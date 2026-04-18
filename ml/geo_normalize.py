"""Collapse duplicate (country, state) spellings in geo CSV rows (e.g. Jammu Kashmir vs Jammu and Kashmir)."""
from __future__ import annotations

import re
from collections import Counter
from typing import Iterable

import pandas as pd


def state_merge_key(country: str, state: str) -> tuple[str, str]:
    """Return (country, normalized_key) for grouping alias spellings of the same region."""
    c = (country or "").strip()
    s = (state or "").strip()
    if not s:
        return c, ""
    k = s.lower()
    k = re.sub(r"\s+", " ", k)
    # Merge "X and Y" with "X Y" (e.g. Jammu and Kashmir vs Jammu Kashmir)
    k = k.replace(" and ", " ")
    if c == "India":
        # Andaman and Nicobar vs Andaman and Nicobar Islands
        k = re.sub(r"\s+islands?$", "", k)
    return c, k


def canonical_state_for_group(states: list[str]) -> str:
    """Pick one display string: prefer longer (more specific), then most frequent."""
    states = [str(x).strip() for x in states if x is not None and str(x).strip()]
    if not states:
        return ""
    cnt = Counter(states)
    return max(states, key=lambda s: (len(s), cnt[s]))


def apply_canonical_state_column(df: pd.DataFrame) -> None:
    """Normalize ``state`` in place; requires ``country`` and ``state`` columns."""
    if df.empty or "country" not in df.columns or "state" not in df.columns:
        return
    df["_mk"] = df.apply(lambda r: state_merge_key(str(r["country"]), str(r["state"]))[1], axis=1)
    df["state"] = df.groupby(["country", "_mk"], sort=False)["state"].transform(
        lambda s: canonical_state_for_group(s.unique().tolist())
    )
    df.drop(columns=["_mk"], inplace=True)


def resolve_canonical_state_from_region_keys(
    country: str,
    state: str,
    region_keys: Iterable[str],
) -> str:
    """Map a raw state string to the key spelling used in ``region_prior`` / ``by_region`` (alias → canonical)."""
    c = (country or "").strip()
    s = (state or "").strip()
    if not c or not s:
        return s
    prefix = f"{c}|"
    mk = state_merge_key(c, s)[1]
    for k in region_keys:
        if not isinstance(k, str) or not k.startswith(prefix):
            continue
        rest = k[len(prefix) :]
        if state_merge_key(c, rest)[1] == mk:
            return rest
    return s
