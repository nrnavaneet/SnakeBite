#!/usr/bin/env python3
"""Build stratified train/val split + data/train|val/<label>/ symlinks from snake_wounds_labels.json."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data" / "geo_data" / "snake_wounds_labels.json"
DATA = ROOT / "data"
CLASSES = ["cytotoxic", "hemotoxic", "neurotoxic", "non_venomous", "not_snakebite"]


def main() -> None:
    rows = json.loads(MANIFEST.read_text(encoding="utf-8"))
    records: list[dict[str, str]] = []
    for r in rows:
        lab = r["label"]
        if lab not in CLASSES:
            continue
        p = Path(r["image_path"])
        if not p.is_file():
            print("warning: missing file, skipping:", p, file=sys.stderr)
            continue
        rel = p.resolve().relative_to(ROOT.resolve())
        records.append({"path": str(rel).replace("\\", "/"), "label": lab})

    df = pd.DataFrame(records)
    if df.empty:
        raise SystemExit("No rows for classes " + ", ".join(CLASSES))

    train_df, val_df = train_test_split(
        df,
        test_size=0.20,
        random_state=42,
        stratify=df["label"],
    )
    train_df = train_df.copy()
    val_df = val_df.copy()
    train_df["split"] = "train"
    val_df["split"] = "val"
    final_df = pd.concat([train_df, val_df], ignore_index=True)

    DATA.mkdir(parents=True, exist_ok=True)
    wound_dir = DATA / "wound_data"
    wound_dir.mkdir(parents=True, exist_ok=True)
    out_csv = wound_dir / "training_data.csv"
    final_df.to_csv(out_csv, index=False)

    for sub in ("train", "val"):
        root = DATA / sub
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        for c in CLASSES:
            (root / c).mkdir(parents=True, exist_ok=True)

    for _, row in final_df.iterrows():
        src = (ROOT / row["path"]).resolve()
        dst = DATA / row["split"] / row["label"] / src.name
        if dst.exists() or dst.is_symlink():
            dst.unlink()
        dst.symlink_to(src)

    print(f"Wrote {out_csv}")
    print(f"Total: {len(final_df)}")
    print(f"Train: {len(train_df)}")
    print(f"Val:   {len(val_df)}")
    print("\nTrain distribution:")
    print(train_df["label"].value_counts().sort_index())
    print("\nVal distribution:")
    print(val_df["label"].value_counts().sort_index())


if __name__ == "__main__":
    main()
