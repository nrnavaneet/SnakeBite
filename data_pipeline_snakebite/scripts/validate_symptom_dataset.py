#!/usr/bin/env python3
"""
Validate symptom_dataset.csv and context_features.csv (production schema):
  feature_type, venom_type, symptom, severity, importance_rank, weight_tier, weight,
  possible_snakes, family, onset_min_hours, onset_max_hours,
  local_signs_absent_or_minimal, source

symptom_dataset.csv: feature_type must be "symptom".
context_features.csv: feature_type must be "context".

Prints Step 8 summary: row counts, symptoms per venom type, tier counts.
"""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYMPTOM_CSV = ROOT / "symptom_data" / "processed" / "symptom_dataset.csv"
CONTEXT_CSV = ROOT / "symptom_data" / "processed" / "context_features.csv"

REQUIRED = (
    "feature_type",
    "venom_type",
    "symptom",
    "severity",
    "importance_rank",
    "weight_tier",
    "weight",
    "possible_snakes",
    "family",
    "onset_min_hours",
    "onset_max_hours",
    "local_signs_absent_or_minimal",
    "source",
)
SEVERITY_OK = frozenset({"early", "moderate", "severe", "critical"})
VENOM_OK = frozenset(
    {
        "neurotoxic",
        "hemotoxic",
        "cytotoxic",
        "myotoxic",
        "non_venomous",
        "unknown",
    }
)
LOCAL_OK = frozenset({"yes", "no", "variable", "na"})
TIER_OK = frozenset(
    {
        "trace",
        "minimal",
        "low",
        "moderate",
        "marked",
        "severe",
        "critical",
    }
)
FEATURE_TYPE_OK = frozenset({"symptom", "context"})


def _source_ok(text: str) -> bool:
    t = text.strip()
    return "https://" in t or t.startswith("http://")


def _parse_num(cell: str) -> float | None:
    s = (cell or "").strip()
    if s == "":
        return None
    return float(s)


def _validate_file(path: Path, expected_feature: str) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows, f"empty CSV: {path}"
    header = rows[0].keys() if rows else []
    for col in REQUIRED:
        assert col in header, f"{path}: missing column {col}: got {list(header)}"

    label = path.name
    for i, r in enumerate(rows, start=2):
        assert r.get("feature_type") == expected_feature, (
            f"{label} row {i}: feature_type must be {expected_feature!r}, "
            f"got {r.get('feature_type')!r}"
        )
        for k in REQUIRED:
            if k in ("onset_min_hours", "onset_max_hours"):
                continue
            v = (r.get(k) or "").strip()
            assert v, f"{label} row {i}: empty {k}"
        assert _source_ok(r["source"]), f"{label} row {i}: source must contain http(s) URL(s)"
        assert r["venom_type"] in VENOM_OK, f"{label} row {i}: bad venom_type {r['venom_type']!r}"
        assert r["severity"] in SEVERITY_OK, f"{label} row {i}: bad severity {r['severity']!r}"
        assert r["local_signs_absent_or_minimal"] in LOCAL_OK, (
            f"{label} row {i}: bad local_signs {r['local_signs_absent_or_minimal']!r}"
        )
        assert r["weight_tier"] in TIER_OK, f"{label} row {i}: bad weight_tier {r['weight_tier']!r}"
        assert r["feature_type"] in FEATURE_TYPE_OK, f"{label} row {i}: bad feature_type"
        ir = int(r["importance_rank"])
        assert 1 <= ir <= 7, f"{label} row {i}: bad importance_rank {ir}"
        wf = float(r["weight"])
        assert 0.0 < wf <= 1.0, f"{label} row {i}: weight out of range {wf}"
        exp = round(ir / 7.0, 4)
        assert abs(wf - exp) < 1e-6, f"{label} row {i}: weight {wf} != rank/7 ({exp})"
        omin = _parse_num(r["onset_min_hours"])
        omax = _parse_num(r["onset_max_hours"])
        if omin is not None and omax is not None:
            assert omin <= omax, f"{label} row {i}: onset_min > onset_max"
    return rows


def main() -> None:
    srows = _validate_file(SYMPTOM_CSV, "symptom")
    crows = _validate_file(CONTEXT_CSV, "context")

    by_vt = Counter(r["venom_type"] for r in srows)
    by_tier = Counter(r["weight_tier"] for r in srows)
    families = sorted({r["family"] for r in srows})
    unique_symptoms = len({r["symptom"] for r in srows})

    print("--- Validation OK ---")
    print("Path:", SYMPTOM_CSV)
    print("Total rows (symptom):", len(srows))
    print("Path:", CONTEXT_CSV)
    print("Total rows (context):", len(crows))
    print("Unique symptom strings:", unique_symptoms)
    print("Symptoms per venom_type:")
    for vt in sorted(by_vt.keys()):
        print(f"  {vt}: {by_vt[vt]}")
    print("Rows per weight_tier (symptom file):")
    for t in sorted(by_tier.keys()):
        print(f"  {t}: {by_tier[t]}")
    print("Unique snake families covered:", len(families))
    for fam in families:
        print(f"  - {fam}")


if __name__ == "__main__":
    main()
