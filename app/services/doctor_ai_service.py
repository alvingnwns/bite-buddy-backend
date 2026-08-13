from __future__ import annotations

import json
from typing import Any

import google.generativeai as genai
from pydantic import BaseModel, Field

from app.core.config import settings


class DoctorAiUnavailable(RuntimeError):
    pass


class DoctorSummary(BaseModel):
    overview: str = Field(min_length=1, max_length=2000)
    insights: list[str] = Field(min_length=1, max_length=8)


async def generate_doctor_summary(source: dict[str, Any]) -> DoctorSummary:
    """Generate decision support from authorized data without dummy fallbacks."""
    if not settings.gemini_api_key:
        raise DoctorAiUnavailable("AI provider is not configured.")
    try:
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.gemini_doctor_model)
        response = await model.generate_content_async(
            "You support a pediatric diabetes doctor. Summarize only the supplied "
            "patient data. Do not diagnose, invent facts, or mention other patients. "
            "Return a concise overview and 1-8 actionable insights.\n\n"
            f"Authorized patient data:\n{json.dumps(source, ensure_ascii=False, default=str)}",
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
                response_schema=DoctorSummary,
                temperature=0.2,
            ),
        )
        return DoctorSummary.model_validate_json(response.text)
    except Exception as exc:
        raise DoctorAiUnavailable("AI provider request failed.") from exc
