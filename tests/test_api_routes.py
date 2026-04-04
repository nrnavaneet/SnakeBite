"""HTTP integration: FastAPI routes used by lab.html (requires repo root on PYTHONPATH)."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def client() -> TestClient:
    from backend.main import app

    with TestClient(app) as c:
        yield c


def test_health_lists_routes(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    j = r.json()
    assert j.get("ok") is True
    assert j.get("classes") and len(j["classes"]) == 5


def test_symptoms_returns_plain_labels(client: TestClient) -> None:
    r = client.get("/symptoms")
    assert r.status_code == 200
    j = r.json()
    assert j.get("symptoms") and len(j["symptoms"]) >= 1
    items = j.get("items") or []
    assert len(items) == len(j["symptoms"])
    sample = next((x for x in items if x.get("value") == "ptosis"), None)
    assert sample is not None
    assert "label" in sample and "Drooping" in sample["label"]
    assert sample.get("category")


def test_post_wound_backbone_paths(client: TestClient) -> None:
    hem = ROOT / "data" / "geo_data" / "categories" / "hemotoxic"
    jpgs = sorted(hem.glob("*.jpg"))
    assert jpgs, "need at least one JPG under hemotoxic/"
    path = jpgs[0]
    data = {
        "backbone": "resnet50",
        "country": "India",
        "state": "Karnataka",
        "symptoms": "[]",
    }
    files = {"file": (path.name, path.read_bytes(), "image/jpeg")}
    for url in ("/test/wound/backbone", "/test/wound_backbone"):
        resp = client.post(url, data=data, files=files)
        assert resp.status_code == 200, f"{url}: {resp.text}"
        body = resp.json()
        assert body.get("mode") == "wound_backbone"
        if body.get("error"):
            pytest.fail(f"{url}: {body}")
        assert body.get("backbone") == "resnet50"
        assert len(body.get("wound_probability", [])) == 5


def test_post_predict_image_quality_and_fusion_fields(client: TestClient) -> None:
    hem = ROOT / "data" / "geo_data" / "categories" / "hemotoxic"
    jp = next(hem.glob("*.jpg"))
    r = client.post(
        "/predict",
        data={
            "symptoms": "[]",
            "country": "India",
            "state": "Karnataka",
            "time_since_bite_hours": "3",
            "bite_circumstance": "unknown",
            "age_years": "35",
            "weight_kg": "60",
        },
        files={"file": (jp.name, jp.read_bytes(), "image/jpeg")},
    )
    assert r.status_code == 200
    j = r.json()
    iq = j.get("image_quality") or {}
    assert "sharpness_score" in iq or iq.get("reason") == "unreadable_image"
    assert "wound_only_top_class" in j
    assert "fusion_explanation" in j
    assert len(j.get("final_probability", [])) == 5
    assert "selected_symptoms_ranked" in j
    assert isinstance(j["selected_symptoms_ranked"], list)
    assert "wound_uncertain" in j
    assert "wound_effective_class" in j
    assert "disclaimer" in j


def test_post_wound_fused(client: TestClient) -> None:
    hem = ROOT / "data" / "geo_data" / "categories" / "hemotoxic"
    jp = next(hem.glob("*.jpg"))
    r = client.post(
        "/test/wound",
        data={
            "country": "India",
            "state": "Karnataka",
            "symptoms": "[]",
        },
        files={"file": (jp.name, jp.read_bytes(), "image/jpeg")},
    )
    assert r.status_code == 200
    j = r.json()
    assert j.get("mode") == "wound_only"
    assert len(j.get("wound_probability", [])) == 5
