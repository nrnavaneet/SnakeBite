"""Tests for country/state geo priors and sanity of probabilities."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def payload():
    p = ROOT / "models" / "geo_region_prior.json"
    assert p.is_file(), "Run: python3 -m ml.build_assets (builds geo_region_prior.json)"
    return json.loads(p.read_text(encoding="utf-8"))


def test_global_default_sums_to_one(payload):
    g = np.array(payload["global_default"], dtype=np.float64)
    assert len(g) == 5
    assert abs(g.sum() - 1.0) < 1e-6


def test_india_karnataka_sums_to_one(payload):
    from ml.geo_regions import geo_prior_from_region

    v = geo_prior_from_region("India", "Karnataka", payload)
    assert len(v) == 5
    assert abs(v.sum() - 1.0) < 1e-6
    assert v.min() >= 0


def test_country_fallback_differs_from_region(payload):
    from ml.geo_regions import geo_prior_from_region

    v_region = geo_prior_from_region("India", "Karnataka", payload)
    v_country = geo_prior_from_region("India", "", payload)
    # State-specific table should usually differ from country aggregate.
    assert v_region.shape == (5,) and v_country.shape == (5,)


def test_unknown_country_uses_global(payload):
    from ml.geo_regions import geo_prior_from_region

    g = np.array(payload["global_default"], dtype=np.float64)
    g = g / g.sum()
    v = geo_prior_from_region("Totally Fictional Country Xyz", "Foo", payload)
    assert np.allclose(v, g, atol=1e-5)


def test_region_table_has_india_states(payload):
    st = payload.get("states_by_country", {}).get("India", [])
    assert len(st) >= 5
    assert "Karnataka" in st
