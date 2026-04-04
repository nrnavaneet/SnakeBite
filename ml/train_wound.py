#!/usr/bin/env python3
"""Train wound classifier(s): single backbone or B3+ResNet50+DenseNet121 ensemble."""
from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

import pandas as pd
import torch
import torch.nn as nn
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms

from ml.config import CLASS_TO_IDX, CLASSES, MODELS, ROOT, WOUND_CSV
from ml.wound_arch import (
    ARCH_CHOICES,
    DEFAULT_ARCH,
    DEFAULT_ENSEMBLE_WEIGHTS,
    ENSEMBLE_ARCHS,
    create_wound_model,
)


class WoundCSVDataset(Dataset):
    def __init__(self, df: pd.DataFrame, train: bool) -> None:
        self.paths = [ROOT / p for p in df["path"].tolist()]
        self.labels = [CLASS_TO_IDX[str(l)] for l in df["label"].tolist()]
        norm = transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        if train:
            self.tf = transforms.Compose(
                [
                    transforms.RandomResizedCrop(224, scale=(0.82, 1.0), ratio=(0.95, 1.05)),
                    transforms.RandomHorizontalFlip(0.5),
                    transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.15, hue=0.02),
                    transforms.RandomRotation(18),
                    transforms.ToTensor(),
                    norm,
                ]
            )
        else:
            self.tf = transforms.Compose(
                [
                    transforms.Resize(256),
                    transforms.CenterCrop(224),
                    transforms.ToTensor(),
                    norm,
                ]
            )

    def __len__(self) -> int:
        return len(self.paths)

    def __getitem__(self, i: int):
        p = self.paths[i]
        img = Image.open(p).convert("RGB")
        return self.tf(img), self.labels[i]


def class_weights_tensor(train_df: pd.DataFrame, dev: torch.device) -> torch.Tensor:
    n = len(train_df)
    w = torch.zeros(len(CLASSES), dtype=torch.float32)
    for i, c in enumerate(CLASSES):
        cnt = int((train_df["label"] == c).sum())
        w[i] = n / (len(CLASSES) * max(cnt, 1))
    w = w / w.mean().clamp(min=1e-6)
    return w.to(dev)


def train_single_arch(
    arch: str,
    train_loader: DataLoader,
    val_loader: DataLoader,
    train_df: pd.DataFrame,
    dev: torch.device,
    epochs: int,
    lr: float,
    label_smoothing: float,
) -> tuple[dict[str, torch.Tensor], float]:
    model = create_wound_model(arch, len(CLASSES), pretrained=True)
    model.to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.02)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max(1, epochs))
    cw = class_weights_tensor(train_df, dev)
    crit = nn.CrossEntropyLoss(weight=cw, label_smoothing=label_smoothing)

    best_acc = 0.0
    best_state: dict[str, torch.Tensor] | None = None

    print(
        f"  [{arch}] model on {dev} — first epoch can take several minutes on CPU; "
        f"{len(train_loader)} train batches…",
        flush=True,
    )

    for epoch in range(epochs):
        model.train()
        total, correct = 0, 0
        for bi, (x, y) in enumerate(train_loader):
            x, y = x.to(dev), y.to(dev)
            opt.zero_grad()
            logits = model(x)
            loss = crit(logits, y)
            loss.backward()
            opt.step()
            pred = logits.argmax(dim=1)
            correct += int((pred == y).sum().item())
            total += len(y)
            if epoch == 0 and bi == 0:
                print(f"  [{arch}] first batch done (training is running)", flush=True)
        train_acc = correct / max(total, 1)

        model.eval()
        vt, vc = 0, 0
        with torch.no_grad():
            for x, y in val_loader:
                x, y = x.to(dev), y.to(dev)
                logits = model(x)
                pred = logits.argmax(dim=1)
                vc += int((pred == y).sum().item())
                vt += len(y)
        val_acc = vc / max(vt, 1)
        lr_now = opt.param_groups[0]["lr"]
        print(
            f"  [{arch}] epoch {epoch+1}/{epochs}  lr={lr_now:.2e}  "
            f"train_acc={train_acc:.3f}  val_acc={val_acc:.3f}",
            flush=True,
        )

        if val_acc >= best_acc:
            best_acc = val_acc
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

        sched.step()

    assert best_state is not None
    return best_state, best_acc


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=25)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--arch", type=str, default=DEFAULT_ARCH, choices=ARCH_CHOICES)
    ap.add_argument("--label-smoothing", type=float, default=0.08)
    ap.add_argument(
        "--ensemble",
        action="store_true",
        help="Train EfficientNet-B3, ResNet50, DenseNet121 and save wound_ensemble.pt",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output path (default: wound_ensemble.pt or wound_mobilenet.pt)",
    )
    args = ap.parse_args()

    df = pd.read_csv(WOUND_CSV)
    train_df = df[df["split"] == "train"].reset_index(drop=True)
    val_df = df[df["split"] == "val"].reset_index(drop=True)

    bs = args.batch_size
    if args.ensemble and bs > 12:
        bs = min(bs, 12)

    train_ds = WoundCSVDataset(train_df, train=True)
    val_ds = WoundCSVDataset(val_df, train=False)
    train_loader = DataLoader(train_ds, batch_size=bs, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=bs, shuffle=False, num_workers=0)

    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    MODELS.mkdir(parents=True, exist_ok=True)

    if args.ensemble:
        out = args.out or (MODELS / "wound_ensemble.pt")
        states: dict[str, dict[str, torch.Tensor]] = {}
        accs: dict[str, float] = {}
        for arch in ENSEMBLE_ARCHS:
            print(f"=== Training {arch} ===", flush=True)
            st, acc = train_single_arch(
                arch,
                train_loader,
                val_loader,
                train_df,
                dev,
                args.epochs,
                args.lr,
                args.label_smoothing,
            )
            states[arch] = st
            accs[arch] = acc
            print(f"  best val_acc for {arch}: {acc:.4f}\n", flush=True)

        torch.save(
            {
                "kind": "ensemble",
                "models": states,
                "model_order": list(ENSEMBLE_ARCHS),
                "ensemble_weights": DEFAULT_ENSEMBLE_WEIGHTS,
                "val_acc": accs,
                "classes": list(CLASSES),
            },
            out,
        )
        print("saved ensemble ->", out, "members:", list(ENSEMBLE_ARCHS), flush=True)
        return

    out = args.out or (MODELS / "wound_mobilenet.pt")
    best_state, best_acc = train_single_arch(
        args.arch,
        train_loader,
        val_loader,
        train_df,
        dev,
        args.epochs,
        args.lr,
        args.label_smoothing,
    )
    torch.save(
        {
            "model_state": best_state,
            "arch": args.arch,
            "classes": list(CLASSES),
            "val_acc": best_acc,
        },
        out,
    )
    print("done. best val_acc=", round(best_acc, 4), "arch=", args.arch, "->", out, flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
