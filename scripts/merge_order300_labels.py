#!/usr/bin/env python3
"""Merge compact label chunks into snake_wounds_labels.json, move files, rebalance CNN splits.

Examples:
  python3 merge_order300_labels.py --order-file ../snake_wounds/order_batch.txt \\
    --chunks ../snake_wounds/compact_labels_part1.json ...
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WOUNDS = ROOT / "data" / "geo_data"
SRC = WOUNDS / "snake_images"
CAT = WOUNDS / "categories"
MANIFEST = WOUNDS / "snake_wounds_labels.json"

ALL_CLASSES = [
    "cytotoxic",
    "hemotoxic",
    "neurotoxic",
    "myotoxic",
    "non_venomous",
    "not_snakebite",
    "unknown",
]

def ruled_list(pairs: list[tuple[str, str]]) -> list[dict]:
    return [{"class": c, "reason": r} for c, r in pairs]


def normalize_flags(raw: object) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw]
    s = str(raw).strip()
    if not s or s.lower() == "none":
        return []
    return [s]


def expand_minimal(obj: dict) -> dict:
    """Chunk2/3 minimal rubric export -> full compact dict."""
    path = obj.get("image_path") or ""
    fname = Path(path).name
    reason = obj.get("reason", "").strip()
    flags = normalize_flags(obj.get("flags"))
    conf = float(obj["confidence"])
    lab = obj["label"]
    return {
        "filename": fname,
        "label": lab,
        "confidence": conf,
        "confidence_before_adjustments": conf,
        "final_summary": reason or f"Compact import: {lab}.",
        "visual_features_observed": [],
        "visual_features_absent": [],
        "classes_ruled_out": [],
        "flags": flags,
        "context_factors_detected": [],
        "tie_break_applied": "compact_minimal_import",
        "pre_check_triggered": None,
        "confidence_adjustments_applied": ["imported_from_minimal_compact"],
        "step1_pre_check": "PC cleared per compact batch.",
        "step2_snakebite_pattern": reason[:280] if reason else "See compact label.",
        "step3_context_factors": "Imported row; limited step detail.",
        "step4_classification": f"Label {lab} from compact batch.",
        "step5_confidence_check": "Floors enforced in merge script.",
        "step6_tie_break": "compact_minimal_import",
        "step7_mistake_check": "Reconcile with rubric floors post-import.",
    }


def coerce_full(obj: dict) -> dict:
    if "filename" in obj and obj["filename"]:
        return obj
    return expand_minimal(obj)


def enforce_rubric_floors(c: dict) -> None:
    label = c["label"]
    cb = float(c.get("confidence_before_adjustments", c["confidence"]))
    conf = float(c["confidence"])
    adj = list(c.get("confidence_adjustments_applied") or [])

    if label == "neurotoxic":
        if conf > 0.70:
            conf = 0.70
            adj.append("cap_neurotoxic_0.70")
        if conf < 0.60:
            c["label"] = "unknown"
            c["confidence"] = min(conf, 0.55)
            c["confidence_before_adjustments"] = cb
            c["final_summary"] = (
                c.get("final_summary", "")
                + " Demoted: neurotoxic below minimum 0.60 or invalid after cap."
            ).strip()
            c["confidence_adjustments_applied"] = adj + ["demote_neuro_floor"]
            return
    if label == "myotoxic":
        if conf > 0.65:
            conf = 0.65
            adj.append("cap_myotoxic_0.65")

    floors = {
        "not_snakebite": 0.85,
        "non_venomous": 0.75,
        "cytotoxic": 0.75,
        "hemotoxic": 0.75,
    }
    if label in floors and conf < floors[label]:
        c["label"] = "unknown"
        c["confidence"] = min(conf, 0.58)
        c["confidence_before_adjustments"] = cb
        c["final_summary"] = (
            c.get("final_summary", "")
            + f" Demoted: {label} below rubric floor {floors[label]}."
        ).strip()
        c["confidence_adjustments_applied"] = adj + [f"demote_floor_{label}"]
        return

    c["confidence"] = conf
    c["confidence_before_adjustments"] = cb
    c["confidence_adjustments_applied"] = adj


def make_record(
    c: dict,
    fname: str,
    label: str,
    cnn_elig: bool,
    cnn_lab: str | None,
    cnn_split: str | None,
) -> dict:
    ruled = c.get("classes_ruled_out") or []
    if ruled and isinstance(ruled[0], dict):
        ruled_out = ruled
    else:
        ruled_out = []

    return {
        "image_path": str((CAT / label / fname).resolve()),
        "label": label,
        "confidence": c["confidence"],
        "confidence_before_adjustments": float(c.get("confidence_before_adjustments", c["confidence"])),
        "reasoning": {
            "step1_pre_check": c.get("step1_pre_check", ""),
            "step2_snakebite_pattern": c.get("step2_snakebite_pattern", ""),
            "step3_context_factors": c.get("step3_context_factors", ""),
            "step4_classification": c.get("step4_classification", ""),
            "step5_confidence_check": c.get("step5_confidence_check", ""),
            "step6_tie_break": c.get("step6_tie_break", ""),
            "step7_mistake_check": c.get("step7_mistake_check", ""),
            "final_summary": c.get("final_summary", ""),
        },
        "visual_features_observed": c.get("visual_features_observed") or [],
        "visual_features_absent": c.get("visual_features_absent") or [],
        "classes_considered": ALL_CLASSES.copy(),
        "classes_ruled_out": ruled_out,
        "flags": c.get("flags") or [],
        "pre_check_triggered": c.get("pre_check_triggered"),
        "context_factors_detected": c.get("context_factors_detected") or [],
        "confidence_adjustments_applied": c.get("confidence_adjustments_applied") or [],
        "tie_break_applied": c.get("tie_break_applied"),
        "cnn_training_eligible": cnn_elig,
        "cnn_label": cnn_lab,
        "cnn_split": cnn_split,
    }


def cnn_base_eligible(label: str, conf: float, flags: list[str]) -> bool:
    bad = {"human_review_recommended", "tourniquet_present", "post_treatment"}
    if conf < 0.80:
        return False
    if label not in ("cytotoxic", "hemotoxic", "neurotoxic", "non_venomous", "not_snakebite"):
        return False
    if any(f in bad for f in flags):
        return False
    return True


def finalize_cnn_splits(rows: list[dict]) -> None:
    """Every 5th eligible row per class (manifest order) -> val; rest train."""
    from collections import defaultdict

    eligible_indices: dict[str, list[int]] = defaultdict(list)
    for i, r in enumerate(rows):
        lab = r["label"]
        conf = float(r["confidence"])
        flags = r.get("flags") or []
        if cnn_base_eligible(lab, conf, flags):
            eligible_indices[lab].append(i)

    for r in rows:
        r["cnn_training_eligible"] = False
        r["cnn_label"] = None
        r["cnn_split"] = None

    for lab, indices in eligible_indices.items():
        for k, idx in enumerate(indices, start=1):
            r = rows[idx]
            r["cnn_training_eligible"] = True
            r["cnn_label"] = lab
            r["cnn_split"] = "val" if k % 5 == 0 else "train"


def main() -> None:
    ap = argparse.ArgumentParser(description="Merge compact label JSON chunks into manifest.")
    ap.add_argument(
        "--order-file",
        type=Path,
        required=True,
        help="Text file: one image basename per line, matching compact chunk order",
    )
    ap.add_argument(
        "--chunks",
        nargs="+",
        type=Path,
        required=True,
        help="Compact JSON chunk files in merge order (lists of label objects)",
    )
    args = ap.parse_args()

    order_path = args.order_file
    chunk_files = list(args.chunks)
    if not order_path.is_file():
        raise SystemExit(f"order file not found: {order_path}")

    expected = [ln.strip() for ln in order_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    compact: list[dict] = []
    for cf in chunk_files:
        if not cf.exists():
            raise SystemExit(f"missing chunk file: {cf}")
        chunk = json.loads(cf.read_text(encoding="utf-8"))
        if not isinstance(chunk, list):
            raise SystemExit(f"bad json list: {cf}")
        for obj in chunk:
            compact.append(coerce_full(obj))

    if len(compact) != len(expected):
        raise SystemExit(f"expected {len(expected)} compact rows (from order file), got {len(compact)}")

    got_names = [c["filename"] for c in compact]
    if got_names != expected:
        for i, (a, b) in enumerate(zip(got_names, expected)):
            if a != b:
                raise SystemExit(f"order mismatch at {i}: {a!r} vs {b!r}")
        raise SystemExit("order mismatch (lengths already checked)")

    existing = json.loads(MANIFEST.read_text(encoding="utf-8"))
    have = {Path(r["image_path"]).name for r in existing}
    overlap = have.intersection(set(expected))
    if overlap:
        raise SystemExit(f"images already in manifest: {sorted(overlap)[:10]}...")

    new_rows: list[dict] = []
    for c in compact:
        enforce_rubric_floors(c)
        label = c["label"]
        fname = c["filename"]
        rec = make_record(c, fname, label, False, None, None)
        new_rows.append(rec)

    merged = existing + new_rows
    finalize_cnn_splits(merged)

    MANIFEST.write_text(json.dumps(merged, indent=2), encoding="utf-8")

    for c in compact:
        fname = c["filename"]
        label = c["label"]
        s = SRC / fname
        dst_dir = CAT / label
        dst_dir.mkdir(parents=True, exist_ok=True)
        d = dst_dir / fname
        if not s.exists():
            print("missing source (skip move):", s, file=__import__("sys").stderr)
            continue
        shutil.move(str(s), str(d))

    print("Wrote", MANIFEST, "total", len(merged))
    print("Appended", len(new_rows), "rows; moved from snake_images where present.")


if __name__ == "__main__":
    main()
