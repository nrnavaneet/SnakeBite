from __future__ import annotations

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    symptoms: list[str] = Field(default_factory=list)
    latitude: float = Field(..., description="GPS latitude (decimal degrees)")
    longitude: float = Field(..., description="GPS longitude (decimal degrees)")
    time_since_bite_hours: float = Field(3.0, ge=0, le=720)
    bite_circumstance: str = Field(
        "unknown",
        description="e.g. nocturnal_indoor, daytime_outdoor, unknown",
    )
    age_years: float = Field(35.0, ge=0, le=120)
    weight_kg: float = Field(60.0, ge=1, le=250)


class PredictResponse(BaseModel):
    classes: list[str]
    final_probability: list[float]
    wound_probability: list[float]
    symptom_probability: list[float]
    geo_probability: list[float]
    top_class: str
    top_confidence: float
    debug: dict
