"""Wound inference: single backbone or EfficientNet-B3 + ResNet50 + DenseNet121 ensemble."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms

from ml.config import CLASSES, WOUND_UNCERTAIN_CONFIDENCE_THRESHOLD
from ml.wound_arch import (
    DEFAULT_ENSEMBLE_WEIGHTS,
    ENSEMBLE_ARCHS,
    create_wound_model,
)

_norm = transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])

_tf_center = transforms.Compose(
    [
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        _norm,
    ]
)


def _tf_hflip(x: torch.Tensor) -> torch.Tensor:
    return torch.flip(x, dims=(3,))


def _forward_one_model(
    model: nn.Module,
    dev: torch.device,
    image_path: Path,
    *,
    tta: bool = True,
) -> np.ndarray:
    img = Image.open(image_path).convert("RGB")
    x0 = _tf_center(img).unsqueeze(0).to(dev)
    model.eval()
    with torch.no_grad():
        if not tta:
            logits = model(x0)
            p = torch.softmax(logits, dim=1)
        else:
            x1 = _tf_hflip(x0)
            log0 = model(x0)
            log1 = model(x1)
            p = (torch.softmax(log0, dim=1) + torch.softmax(log1, dim=1)) * 0.5
    return p.cpu().numpy().ravel().astype(np.float64)


@dataclass
class WoundPredictor:
    """Single model or fixed-order ensemble; fusion = weighted average of softmax vectors."""

    dev: torch.device
    models: list[tuple[str, nn.Module]]
    fusion_weights: list[float]
    kind: str = "single"  # "single" | "ensemble"

    def predict(self, image_path: Path, *, tta: bool = True) -> tuple[np.ndarray, dict[str, Any]]:
        stacked: list[np.ndarray] = []
        per: dict[str, Any] = {}
        for (name, m), w in zip(self.models, self.fusion_weights, strict=True):
            p = _forward_one_model(m, self.dev, image_path, tta=tta)
            stacked.append(p * float(w))
            ti = int(np.argmax(p))
            per[name] = {
                "probability": p.tolist(),
                "top_class": CLASSES[ti],
                "top_confidence": float(p[ti]),
            }
        final = np.sum(np.stack(stacked, axis=0), axis=0)
        final = np.maximum(final, 1e-12)
        final = final / final.sum()
        max_conf = float(np.max(final))
        uncertain = max_conf < WOUND_UNCERTAIN_CONFIDENCE_THRESHOLD
        ti = int(np.argmax(final))
        meta = {
            "kind": self.kind,
            "fusion": "weighted_average_softmax",
            "ensemble_weights": self.fusion_weights,
            "models": per,
            "ensemble_max_confidence": max_conf,
            "wound_uncertain": uncertain,
            "wound_effective_class": "unknown" if uncertain else CLASSES[ti],
            "wound_uncertain_threshold": WOUND_UNCERTAIN_CONFIDENCE_THRESHOLD,
        }
        return final.astype(np.float64), meta

    def predict_backbone(
        self,
        backbone: str,
        image_path: Path,
        *,
        tta: bool = True,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """Single backbone softmax (unnormalized vs other models)."""
        backbone = backbone.strip().lower()
        for name, m in self.models:
            if name.lower() == backbone:
                p = _forward_one_model(m, self.dev, image_path, tta=tta)
                ti = int(np.argmax(p))
                return p.astype(np.float64), {
                    "backbone": name,
                    "probability": p.tolist(),
                    "top_class": CLASSES[ti],
                    "top_confidence": float(p[ti]),
                }
        avail = [n for n, _ in self.models]
        raise ValueError(f"unknown backbone {backbone!r}; available: {avail}")


def pick_wound_checkpoint(root: Path | None = None) -> Path | None:
    root = root or Path(__file__).resolve().parents[1]
    ens = root / "models" / "wound_ensemble.pt"
    leg = root / "models" / "wound_mobilenet.pt"
    if ens.is_file():
        return ens
    if leg.is_file():
        return leg
    return None


def load_wound_predictor(
    path: Path | None = None,
    device: str | None = None,
) -> tuple[WoundPredictor | None, torch.device]:
    """Load ensemble (preferred) or legacy single checkpoint."""
    path = path or pick_wound_checkpoint()
    dev = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
    if path is None or not path.is_file():
        return None, dev
    try:
        ckpt = torch.load(path, map_location=dev, weights_only=False)
    except TypeError:
        ckpt = torch.load(path, map_location=dev)

    if ckpt.get("kind") == "ensemble":
        order = list(ckpt.get("model_order") or ENSEMBLE_ARCHS)
        # Standard B3+ResNet50+DenseNet: always use EfficientNet-heavy weights at inference.
        if tuple(order) == ENSEMBLE_ARCHS:
            weights = list(DEFAULT_ENSEMBLE_WEIGHTS)
        else:
            weights = list(ckpt.get("ensemble_weights") or DEFAULT_ENSEMBLE_WEIGHTS)
        raw = ckpt["models"]
        models: list[tuple[str, nn.Module]] = []
        for name in order:
            m = create_wound_model(name, len(CLASSES), pretrained=False)
            m.load_state_dict(raw[name])
            m.to(dev)
            m.eval()
            models.append((name, m))
        if len(weights) != len(models):
            weights = DEFAULT_ENSEMBLE_WEIGHTS[: len(models)]
        s = sum(weights)
        weights = [w / s for w in weights]
        return WoundPredictor(dev, models, weights, kind="ensemble"), dev

    arch = str(ckpt.get("arch") or "mobilenet_v3_small").lower()
    m = create_wound_model(arch, len(CLASSES), pretrained=False)
    m.load_state_dict(ckpt["model_state"])
    m.to(dev)
    m.eval()
    pred = WoundPredictor(dev, [(arch, m)], [1.0], kind="single")
    return pred, dev


def predict_wound_probs(
    predictor: WoundPredictor | None,
    dev: torch.device,
    image_path: Path,
    *,
    tta: bool = True,
    return_meta: bool = False,
) -> np.ndarray | tuple[np.ndarray, dict[str, Any]]:
    """
    Fused probability vector over CLASSES (ensemble = weighted softmax average).
    """
    if predictor is None:
        u = np.ones(len(CLASSES), dtype=np.float64) / len(CLASSES)
        meta = {
            "kind": "none",
            "models": {},
            "fusion": "uniform",
            "ensemble_max_confidence": float(np.max(u)),
            "wound_uncertain": True,
            "wound_effective_class": "unknown",
            "wound_uncertain_threshold": WOUND_UNCERTAIN_CONFIDENCE_THRESHOLD,
        }
        if return_meta:
            return u, meta
        return u
    final, meta = predictor.predict(image_path, tta=tta)
    if return_meta:
        return final, meta
    return final


def load_wound_model(path: Path | None = None, device: str | None = None) -> tuple[WoundPredictor | None, torch.device]:
    """API/tests: same as load_wound_predictor (name kept for compatibility)."""
    p = path if path is not None else pick_wound_checkpoint()
    return load_wound_predictor(p, device)
