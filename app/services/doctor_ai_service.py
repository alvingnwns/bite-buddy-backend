from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.ai_service import _clean_json_loads, _race_tasks
from app.services.openrouter_service import OpenRouterService

logger = logging.getLogger(__name__)
NO_AUTO_FUNCTION_CALLING = types.AutomaticFunctionCallingConfig(disable=True)


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


def _normalize_doctor_summary(raw: dict[str, Any]) -> DoctorSummary:
    overview = raw.get("overview", "")
    if isinstance(overview, dict):
        overview = str(overview.get("summary") or overview.get("text") or json.dumps(overview))
    elif not isinstance(overview, str):
        overview = str(overview)
    if not overview.strip():
        overview = "Patient profile and vital parameters are currently recorded and monitored."

    insights = raw.get("insights", [])
    if isinstance(insights, str):
        insights = [insights]
    elif isinstance(insights, list):
        insights = [str(item).strip() for item in insights if str(item).strip()]
    else:
        insights = []

    if not insights:
        insights = [
            "Monitor blood glucose trends regularly.",
            "Ensure adherence to prescribed medication and nutrition schedules.",
        ]

    return DoctorSummary(overview=overview[:2000].strip(), insights=insights[:8])


def _deterministic_doctor_summary(source: dict[str, Any]) -> DoctorSummary:
    patient = source.get("patient") or {}
    name = str(patient.get("fullName") or "Patient").strip()
    clinical = source.get("latestClinicalParameters") or {}
    conditions = clinical.get("medical_conditions") or []
    cond_str = f"diagnosed with {', '.join(str(c) for c in conditions)}" if conditions else "under pediatric metabolic monitoring"

    height = clinical.get("height_cm")
    weight = clinical.get("weight_kg")
    vitals_part = f" Vitals: {height} cm, {weight} kg." if height and weight else ""

    glucose_records = source.get("recentBloodGlucose") or []
    if glucose_records:
        avg_val = round(sum(float(r.get("value_mg_dl", 0)) for r in glucose_records) / len(glucose_records), 1)
        glucose_part = f" Recent blood glucose averages {avg_val} mg/dL across {len(glucose_records)} logged readings."
    else:
        glucose_part = " No recent blood glucose logs recorded."

    overview = f"{name} is {cond_str}.{vitals_part}{glucose_part}"

    insights = [
        "Continue tracking blood glucose levels in relation to meal times.",
        "Maintain balanced carbohydrate and dietary fiber distribution across daily meals.",
        "Review medication adherence during upcoming routine consultation.",
    ]
    return DoctorSummary(overview=overview[:2000], insights=insights[:8])


async def generate_doctor_summary(source: dict[str, Any]) -> DoctorSummary:
    """Generate decision support from authorized data with concurrent AI racing and deterministic fallback."""
    fallback = OpenRouterService()
    prompt = (
        "You are a pediatric clinical AI assistant supporting a doctor. "
        "Analyze the patient data below and generate a concise clinical summary for the doctor. "
        "Do not invent facts or mention other patients. "
        "You MUST return ONLY a valid JSON object with EXACTLY two fields:\n"
        '- "overview": a concise string narrative summarizing patient condition, vital parameters, and health status.\n'
        '- "insights": a list of 1 to 8 actionable string recommendations for clinical follow-up.\n\n'
        f"Patient Data:\n{json.dumps(source, ensure_ascii=False, default=str)}"
    )

    tasks: list[asyncio.Task[DoctorSummary]] = []

    async def _gemini_call() -> DoctorSummary:
        if not settings.gemini_api_key:
            raise RuntimeError("Gemini is not configured")
        client = genai.Client(api_key=settings.gemini_api_key)
        response = await client.aio.models.generate_content(
            model=settings.gemini_doctor_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=DOCTOR_SUMMARY_PROVIDER_SCHEMA,
                temperature=0.2,
                automatic_function_calling=NO_AUTO_FUNCTION_CALLING,
            ),
        )
        return _normalize_doctor_summary(_clean_json_loads(response.text))

    async def _openrouter_call() -> DoctorSummary:
        if not fallback.configured:
            raise RuntimeError("OpenRouter is not configured")
        raw = await fallback.complete_json(prompt, temperature=0.2)
        return _normalize_doctor_summary(raw)

    if settings.gemini_api_key:
        tasks.append(asyncio.create_task(_gemini_call()))
    if fallback.configured:
        tasks.append(asyncio.create_task(_openrouter_call()))

    if tasks:
        try:
            return await _race_tasks(tasks)
        except Exception:
            logger.warning("All doctor AI providers failed or quota exceeded; using deterministic clinical summary", exc_info=True)

    return _deterministic_doctor_summary(source)
