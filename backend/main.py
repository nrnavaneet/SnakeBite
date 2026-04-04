"""
SnakeBiteRx FastAPI server: multimodal venom-type support (not a medical device).

Run from repo root:
  uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ml.config import CLASSES
from ml.fusion import fuse_multimodal, top_prediction
from ml.image_quality import assess_image_quality
from ml.geo_regions import geo_prior_from_region, load_geo_region_payload
from ml.geo_species import load_geo_species_payload, rank_snake_species
from ml.infer import load_wound_predictor, pick_wound_checkpoint, predict_wound_probs
from ml.symptom_engine import load_catalog, rank_selected_symptoms, score_symptoms

from backend.disclaimer import PRODUCT_DISCLAIMER

app = FastAPI(title="SnakeBiteRx API", version="0.1.0")

# Apply before routes so all paths (including /predict multipart) get CORS on success and error responses.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.is_dir():
    app.mount("/ui", StaticFiles(directory=str(STATIC_DIR), html=True), name="ui")


@app.get("/")
def root() -> dict:
    return {
        "service": "SnakeBiteRx API",
        "docs": "/docs",
        "browser_test_ui": "/ui/",
        "lab_test_ui": "/ui/lab.html",
        "health": "/health",
        "geo_regions": "/geo/regions",
        "sample_wound_image": "/test/sample_wound_image",
        "test_wound_backbone": "/test/wound/backbone",
        "test_wound_backbone_alt": "/test/wound_backbone",
        "disclaimer": PRODUCT_DISCLAIMER,
    }


@app.get("/demo")
def demo_page() -> FileResponse:
    """Single-page tester (same as /ui/index.html)."""
    index = STATIC_DIR / "index.html"
    if not index.is_file():
        raise FileNotFoundError("backend/static/index.html missing")
    return FileResponse(index)


_wound_predictor = None
_wound_dev = None
_symptoms: list[str] | None = None
_symptom_mat: np.ndarray | None = None
_symptom_items: list[dict[str, str]] | None = None
_geo_payload: dict | None = None
_species_payload: dict | None = None


def _symptom_label_by_value() -> dict[str, dict[str, str]]:
    assert _symptom_items is not None
    return {x["value"]: x for x in _symptom_items}


@app.on_event("startup")
def _startup() -> None:
    global _wound_predictor, _wound_dev, _symptoms, _symptom_mat, _symptom_items, _geo_payload, _species_payload
    _symptoms, _symptom_mat, _symptom_items = load_catalog()
    _geo_payload = load_geo_region_payload()
    _species_payload = load_geo_species_payload()
    ck = pick_wound_checkpoint(ROOT)
    _wound_predictor, _wound_dev = load_wound_predictor(ck)


@app.get("/symptoms")
def list_symptoms() -> dict:
    """KB symptom values plus plain-language labels for checkboxes (mobile + web)."""
    assert _symptoms is not None and _symptom_items is not None
    return {
        "symptoms": _symptoms,
        "items": _symptom_items,
        "note": "Submit `symptoms` JSON array using each item's `value` (internal key). `label` is for display only.",
    }


@app.get("/geo/regions")
def geo_regions() -> dict:
    """Countries and state lists for dropdowns (from GBIF-derived priors)."""
    assert _geo_payload is not None
    return {
        "countries": _geo_payload.get("countries", []),
        "states_by_country": _geo_payload.get("states_by_country", {}),
    }


@app.get("/health")
def health() -> dict:
    backs: list[str] = []
    if _wound_predictor is not None:
        backs = [n for n, _ in _wound_predictor.models]
    return {
        "ok": True,
        "wound_model_loaded": _wound_predictor is not None,
        "wound_mode": getattr(_wound_predictor, "kind", None),
        "wound_backbones": backs,
        "classes": list(CLASSES),
        "disclaimer_summary": PRODUCT_DISCLAIMER["summary"],
    }


@app.get("/test/sample_wound_image")
def sample_wound_image() -> FileResponse:
    """First JPG under data/geo_data/categories/hemotoxic (for lab / smoke tests)."""
    sample_dir = ROOT / "data" / "geo_data" / "categories" / "hemotoxic"
    jpgs = sorted(sample_dir.glob("*.jpg"))
    if not jpgs:
        raise HTTPException(
            status_code=404,
            detail="No JPGs under data/geo_data/categories/hemotoxic",
        )
    p = jpgs[0]
    return FileResponse(p, media_type="image/jpeg", filename=p.name)


@app.post("/predict")
async def predict(
    file: UploadFile = File(...),
    symptoms: str = Form("[]"),
    country: str = Form(...),
    state: str = Form(""),
    time_since_bite_hours: float = Form(3.0),
    bite_circumstance: str = Form("unknown"),
    age_years: float = Form(35.0),
    weight_kg: float = Form(60.0),
) -> dict:
    """Multipart: wound image + country/state + clinical/context fields."""
    raw = await file.read()
    tmp = ROOT / "models" / "_upload_tmp.jpg"
    tmp.write_bytes(raw)

    try:
        sym_list = json.loads(symptoms)
        if not isinstance(sym_list, list):
            sym_list = []
    except json.JSONDecodeError:
        sym_list = []

    image_quality = assess_image_quality(tmp)

    if _wound_predictor is None:
        wound_p = np.ones(len(CLASSES), dtype=np.float64) / len(CLASSES)
        wound_detail = None
    else:
        wound_p, wound_detail = predict_wound_probs(
            _wound_predictor, _wound_dev, tmp, return_meta=True
        )

    wd = wound_detail or {}
    w_top, w_conf = top_prediction(wound_p)

    assert _symptoms is not None and _symptom_mat is not None
    assert _geo_payload is not None
    sym_p = score_symptoms(sym_list, _symptoms, _symptom_mat)
    g_p = geo_prior_from_region(country, state, _geo_payload)

    final, dbg = fuse_multimodal(
        wound_p,
        sym_p,
        g_p,
        time_since_bite_hours=time_since_bite_hours,
        bite_circumstance=bite_circumstance,
        age_years=age_years,
        weight_kg=weight_kg,
    )
    top, conf = top_prediction(final)

    assert _species_payload is not None
    species_rank, sp_dbg = rank_snake_species(
        final,
        country.strip(),
        (state or "").strip(),
        sym_list,
        _species_payload,
    )

    sym_top, sym_conf = top_prediction(sym_p)
    geo_top, geo_conf = top_prediction(g_p)

    selected_ranked = rank_selected_symptoms(
        sym_list,
        _symptoms,
        _symptom_mat,
        sym_p,
        label_by_value=_symptom_label_by_value(),
    )

    return {
        "classes": list(CLASSES),
        "disclaimer": PRODUCT_DISCLAIMER,
        "image_quality": image_quality,
        "final_probability": final.tolist(),
        "wound_probability": wound_p.tolist(),
        "wound_only_top_class": w_top,
        "wound_only_confidence": w_conf,
        "wound_uncertain": wd.get("wound_uncertain", True),
        "wound_effective_class": wd.get("wound_effective_class", "unknown"),
        "wound_ensemble_max_confidence": wd.get("ensemble_max_confidence"),
        "wound_detail": wound_detail,
        "symptom_probability": sym_p.tolist(),
        "symptom_only_top_class": sym_top,
        "symptom_only_confidence": sym_conf,
        "selected_symptoms_ranked": selected_ranked,
        "geo_probability": g_p.tolist(),
        "geo_only_top_class": geo_top,
        "geo_only_confidence": geo_conf,
        "geo_input": {"country": country.strip(), "state": (state or "").strip()},
        "top_class": top,
        "top_confidence": conf,
        "fusion_explanation": {
            "wound_branch": (
                "Ensemble: weighted average of softmax vectors — EfficientNet-B3 0.5, ResNet50 0.3, "
                "DenseNet121 0.2. If ensemble max confidence < 0.60, wound_effective_class is 'unknown'."
            ),
            "final_multimodal": (
                "final_probability blends wound + symptoms + geo + context in log-space "
                f"(weights: {dbg.get('modality_weights', {})}). "
                "It is not the sum of the three CNN outputs; symptoms/geo/context can change the top class."
            ),
        },
        "snake_species_top": species_rank,
        "snake_species_debug": sp_dbg,
        "debug": dbg,
    }


@app.post("/test/wound/backbone")
@app.post("/test/wound_backbone")
async def test_wound_backbone(
    file: UploadFile = File(...),
    backbone: str = Form(...),
    country: str = Form("India"),
    state: str = Form("Karnataka"),
    symptoms: str = Form("[]"),
) -> dict:
    """Single ensemble member (EfficientNet-B3, ResNet50, or DenseNet121) — atomic softmax.

    Registered at ``/test/wound/backbone`` and ``/test/wound_backbone`` (alias for clients that
    mishandle paths with multiple slashes).
    """
    raw = await file.read()
    tmp = ROOT / "models" / "_upload_tmp.jpg"
    tmp.write_bytes(raw)
    try:
        sym_list = json.loads(symptoms)
        if not isinstance(sym_list, list):
            sym_list = []
    except json.JSONDecodeError:
        sym_list = []

    if _wound_predictor is None:
        return {"error": "no wound checkpoint", "mode": "wound_backbone"}
    try:
        wound_p, bb_detail = _wound_predictor.predict_backbone(backbone, tmp)
    except ValueError as e:
        return {"error": str(e), "mode": "wound_backbone", "available": [n for n, _ in _wound_predictor.models]}

    top, conf = top_prediction(wound_p)
    assert _species_payload is not None
    species_rank, sp_dbg = rank_snake_species(
        wound_p,
        (country or "").strip(),
        (state or "").strip(),
        sym_list,
        _species_payload,
    )
    return {
        "mode": "wound_backbone",
        "backbone": bb_detail.get("backbone"),
        "classes": list(CLASSES),
        "wound_probability": wound_p.tolist(),
        "wound_backbone_detail": bb_detail,
        "top_class": top,
        "top_confidence": conf,
        "snake_species_top": species_rank,
        "snake_species_debug": sp_dbg,
        "geo_input": {"country": (country or "").strip(), "state": (state or "").strip()},
    }


@app.post("/test/wound")
async def test_wound_only(
    file: UploadFile = File(...),
    country: str = Form("India"),
    state: str = Form("Karnataka"),
    symptoms: str = Form("[]"),
) -> dict:
    """Wound CNN only (+ optional species hint using wound probs × region × symptoms)."""
    raw = await file.read()
    tmp = ROOT / "models" / "_upload_tmp.jpg"
    tmp.write_bytes(raw)
    try:
        sym_list = json.loads(symptoms)
        if not isinstance(sym_list, list):
            sym_list = []
    except json.JSONDecodeError:
        sym_list = []

    if _wound_predictor is None:
        wound_p = np.ones(len(CLASSES), dtype=np.float64) / len(CLASSES)
        wound_detail = None
    else:
        wound_p, wound_detail = predict_wound_probs(
            _wound_predictor, _wound_dev, tmp, return_meta=True
        )

    top, conf = top_prediction(wound_p)
    assert _species_payload is not None
    species_rank, sp_dbg = rank_snake_species(
        wound_p,
        (country or "").strip(),
        (state or "").strip(),
        sym_list,
        _species_payload,
    )
    return {
        "mode": "wound_only",
        "classes": list(CLASSES),
        "wound_probability": wound_p.tolist(),
        "wound_detail": wound_detail,
        "top_class": top,
        "top_confidence": conf,
        "snake_species_top": species_rank,
        "snake_species_debug": sp_dbg,
        "geo_input": {"country": (country or "").strip(), "state": (state or "").strip()},
    }


@app.post("/test/geo")
def test_geo_only(
    country: str = Form(...),
    state: str = Form(""),
    symptoms: str = Form("[]"),
) -> dict:
    """Geo venom prior only + species ranks from that prior (GBIF)."""
    try:
        sym_list = json.loads(symptoms)
        if not isinstance(sym_list, list):
            sym_list = []
    except json.JSONDecodeError:
        sym_list = []

    assert _geo_payload is not None and _species_payload is not None
    g_p = geo_prior_from_region(country, state, _geo_payload)
    top, conf = top_prediction(g_p)
    species_rank, sp_dbg = rank_snake_species(
        g_p,
        (country or "").strip(),
        (state or "").strip(),
        sym_list,
        _species_payload,
    )
    return {
        "mode": "geo_only",
        "classes": list(CLASSES),
        "geo_probability": g_p.tolist(),
        "top_class": top,
        "top_confidence": conf,
        "snake_species_top": species_rank,
        "snake_species_debug": sp_dbg,
        "geo_input": {"country": (country or "").strip(), "state": (state or "").strip()},
    }


@app.post("/test/symptoms")
def test_symptoms_only(
    country: str = Form("India"),
    state: str = Form("Karnataka"),
    symptoms: str = Form(...),
) -> dict:
    """Symptom KB only → venom distribution + species ranks."""
    try:
        sym_list = json.loads(symptoms)
        if not isinstance(sym_list, list):
            sym_list = []
    except json.JSONDecodeError:
        return {"error": "symptoms must be a JSON array of strings", "mode": "symptoms_only"}

    assert _symptoms is not None and _symptom_mat is not None and _species_payload is not None
    sym_p = score_symptoms(sym_list, _symptoms, _symptom_mat)
    top, conf = top_prediction(sym_p)
    selected_ranked = rank_selected_symptoms(
        sym_list,
        _symptoms,
        _symptom_mat,
        sym_p,
        label_by_value=_symptom_label_by_value(),
    )
    species_rank, sp_dbg = rank_snake_species(
        sym_p,
        (country or "").strip(),
        (state or "").strip(),
        sym_list,
        _species_payload,
    )
    return {
        "mode": "symptoms_only",
        "classes": list(CLASSES),
        "symptom_probability": sym_p.tolist(),
        "selected_symptoms_ranked": selected_ranked,
        "top_class": top,
        "top_confidence": conf,
        "snake_species_top": species_rank,
        "snake_species_debug": sp_dbg,
        "geo_input": {"country": (country or "").strip(), "state": (state or "").strip()},
    }
