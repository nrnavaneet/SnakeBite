"""Wound CNN backbones + single-checkpoint load (ensemble loading lives in infer.py)."""
from __future__ import annotations

from pathlib import Path

import torch
import torch.nn as nn
from torchvision.models import (
    DenseNet121_Weights,
    MobileNet_V3_Small_Weights,
    ResNet18_Weights,
    ResNet50_Weights,
    densenet121,
    efficientnet_b0,
    efficientnet_b3,
    EfficientNet_B0_Weights,
    EfficientNet_B3_Weights,
    mobilenet_v3_small,
    resnet18,
    resnet50,
)

from ml.config import CLASSES

DEFAULT_ARCH = "efficientnet_b0"
ARCH_CHOICES = (
    "efficientnet_b0",
    "efficientnet_b3",
    "resnet18",
    "resnet50",
    "densenet121",
    "mobilenet_v3_small",
)

# Default wound ensemble (training + inference): EfficientNet-B3 favored over ResNet50 / DenseNet121
ENSEMBLE_ARCHS: tuple[str, ...] = ("efficientnet_b3", "resnet50", "densenet121")
DEFAULT_ENSEMBLE_WEIGHTS = [0.5, 0.3, 0.2]


def create_wound_model(arch: str, num_classes: int, *, pretrained: bool) -> nn.Module:
    arch = arch.lower()
    if arch == "efficientnet_b0":
        w = EfficientNet_B0_Weights.IMAGENET1K_V1 if pretrained else None
        m = efficientnet_b0(weights=w)
        in_f = m.classifier[1].in_features
        m.classifier[1] = nn.Linear(in_f, num_classes)
        return m
    if arch == "efficientnet_b3":
        w = EfficientNet_B3_Weights.IMAGENET1K_V1 if pretrained else None
        m = efficientnet_b3(weights=w)
        in_f = m.classifier[1].in_features
        m.classifier[1] = nn.Linear(in_f, num_classes)
        return m
    if arch == "resnet18":
        w = ResNet18_Weights.IMAGENET1K_V1 if pretrained else None
        m = resnet18(weights=w)
        in_f = m.fc.in_features
        m.fc = nn.Linear(in_f, num_classes)
        return m
    if arch == "resnet50":
        w = ResNet50_Weights.IMAGENET1K_V1 if pretrained else None
        m = resnet50(weights=w)
        in_f = m.fc.in_features
        m.fc = nn.Linear(in_f, num_classes)
        return m
    if arch == "densenet121":
        w = DenseNet121_Weights.IMAGENET1K_V1 if pretrained else None
        m = densenet121(weights=w)
        in_f = m.classifier.in_features
        m.classifier = nn.Linear(in_f, num_classes)
        return m
    if arch == "mobilenet_v3_small":
        w = MobileNet_V3_Small_Weights.IMAGENET1K_V1 if pretrained else None
        m = mobilenet_v3_small(weights=w)
        in_f = m.classifier[3].in_features
        m.classifier[3] = nn.Linear(in_f, num_classes)
        return m
    raise ValueError(f"unknown arch {arch!r}, expected one of {ARCH_CHOICES}")


def load_wound_model_from_checkpoint(
    path: Path | None,
    device: torch.device | None = None,
) -> tuple[nn.Module, torch.device, dict]:
    """Load a single backbone from disk. Checkpoint may omit `arch` → mobilenet_v3_small (legacy)."""
    path = path or Path(__file__).resolve().parents[1] / "models" / "wound_mobilenet.pt"
    dev = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
    try:
        ckpt = torch.load(path, map_location=dev, weights_only=False)
    except TypeError:
        ckpt = torch.load(path, map_location=dev)
    if ckpt.get("kind") == "ensemble":
        raise ValueError("use load_wound_predictor() for wound_ensemble.pt")
    arch = str(ckpt.get("arch") or "mobilenet_v3_small").lower()
    model = create_wound_model(arch, len(CLASSES), pretrained=False)
    model.load_state_dict(ckpt["model_state"])
    model.to(dev)
    model.eval()
    return model, dev, ckpt
