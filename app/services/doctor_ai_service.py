from __future__ import annotations

import json
import logging
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.openrouter_service import OpenRouterService

logger = logging.getLogger(__name__)


class DoctorAiUnavailable(RuntimeError):
    pass


class DoctorSummary(BaseModel):
    overview: str = Field(min_length=1, max_length=2000)
    insights: list[str] = Field(min_length=1, max_length=8)


DOCTOR_SUMMARY_PROVIDER_SCHEMA = {
    "type": "object",
    "properties": {
        "overview": {"type": "string"},
        "insights": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["overview", "insights"],
}


async def generate_doctor_summary(source: dict[str, Any]) -> DoctorSummary:
    """Generate decision support from authorized data without dummy fallbacks."""
    fallback = OpenRouterService()
    if not settings.gemini_api_key and not fallback.configured:
        raise DoctorAiUnavailable("AI provider is not configured.")
    prompt = (
        "You support a pediatric diabetes doctor. Summarize only the supplied "
        "patient data. Do not diagnose, invent facts, or mention other patients. "
        "Return only JSON with a concise overview and an insights array containing "
        "1-8 actionable items.\n\n"
        f"Authorized patient data:\n{json.dumps(source, ensure_ascii=False, default=str)}"
    )
    if settings.gemini_api_key:
        try:
            client = genai.Client(api_key=settings.gemini_api_key)
            response = await client.aio.models.generate_content(
                model=settings.gemini_doctor_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=DOCTOR_SUMMARY_PROVIDER_SCHEMA,
                    temperature=0.2,
                ),
            )
            return DoctorSummary.model_validate_json(response.text)
        except Exception:
            logger.warning("Gemini doctor summary failed; trying Qwen fallback", exc_info=True)
    try:
        return DoctorSummary.model_validate(
            await fallback.complete_json(prompt, temperature=0.2)
        )
    except Exception as exc:
        logger.exception("All doctor AI providers failed")
        raise DoctorAiUnavailable("AI provider request failed.") from exc
