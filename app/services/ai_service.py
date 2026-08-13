"""Multimodal AI with Gemini primary and OpenRouter Qwen fallback."""

import json
import logging
from typing import Any

import google.generativeai as genai
from fastapi import HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.food_data_service import get_food_data_service
from app.services.openrouter_service import OpenRouterService

logger = logging.getLogger(__name__)

if settings.gemini_api_key:
    genai.configure(api_key=settings.gemini_api_key)


class IngredientEstimate(BaseModel):
    name: str = Field(description="Simple English ingredient name")
    weight_g: float = Field(gt=0, description="Estimated ingredient weight in grams")


class FoodDetectionResponse(BaseModel):
    is_food: bool
    food_name: str
    ingredients: list[IngredientEstimate]


FOOD_PROMPT = (
    "You are a cautious pediatric nutrition image analyst. Analyze only visible evidence. "
    "First decide whether the image contains edible food. If not, return is_food=false, "
    "food_name='', and ingredients=[]. If it is food, identify the primary dish in food_name "
    "using a short consumer-facing dish name, never an ingredient list. Examples: a scoop or "
    "cup of frozen dairy dessert is 'Ice cream'; noodles with tomato sauce are 'Spaghetti'; "
    "fried rice is 'Nasi goreng'. Do not invent unusual or hidden ingredients. Never label ice "
    "cream as eggplant unless eggplant is clearly visible. List only visually supported or "
    "standard high-confidence ingredients needed for nutrition estimation. When uncertain, use "
    "the generic dish as one ingredient instead of guessing. Estimate weight_g in grams. Return "
    "only JSON with keys is_food, food_name, and ingredients; every ingredient has name and weight_g."
)

MEDICINE_PROMPT = (
    "Identify whether this image contains medicine, medical equipment, or pills. Return only JSON "
    "with boolean is_medicine and string detected. If there is no medicine, detected must be "
    "'None'. For insulin pens or syringes use 'insulin pen'; pills or medicine bottles use "
    "'medicine'; otherwise use 'Unknown Medicine'. Do not classify food, animals, or people as medicine."
)


class AIService:
    def __init__(self) -> None:
        self.api_key = settings.gemini_api_key
        self.food_model_name = settings.gemini_food_model
        self.medicine_model_name = settings.gemini_medicine_model
        self.food_data_service = get_food_data_service()
        self.openrouter = OpenRouterService()

    async def _gemini_food(self, image_bytes: bytes, mime_type: str) -> dict[str, Any]:
        model = genai.GenerativeModel(self.food_model_name)
        response = await model.generate_content_async(
            contents=[FOOD_PROMPT, {"mime_type": mime_type, "data": image_bytes}],
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
                response_schema=FoodDetectionResponse,
                temperature=0.2,
            ),
        )
        return json.loads(response.text)

    async def _fallback_food(self, image_bytes: bytes, mime_type: str) -> dict[str, Any]:
        return await self.openrouter.complete_json(
            FOOD_PROMPT, image_bytes=image_bytes, mime_type=mime_type, temperature=0.2
        )

    def _map_food(self, raw: dict[str, Any]) -> tuple[bool, str, list[dict[str, Any]]]:
        data = FoodDetectionResponse.model_validate(raw)
        if not data.is_food:
            return False, "", []
        mapped: list[dict[str, Any]] = []
        for item in data.ingredients:
            search_results = self.food_data_service.search_by_name(item.name, max_results=1)
            mapped.append({
                "ingredient": item.name,
                "description": search_results[0]["description"] if search_results else item.name,
                "weight_g": item.weight_g,
                "fdcId": search_results[0]["fdcId"] if search_results else None,
            })
        return True, data.food_name.strip() or "Food", mapped

    async def detect_food_ingredients(
        self, image_bytes: bytes, mime_type: str = "image/jpeg"
    ) -> tuple[bool, str, list[dict[str, Any]]]:
        errors: list[Exception] = []
        if self.api_key:
            try:
                return self._map_food(await self._gemini_food(image_bytes, mime_type))
            except Exception as exc:
                errors.append(exc)
                logger.warning("Gemini food analysis failed; trying Qwen fallback", exc_info=True)
        if self.openrouter.configured:
            try:
                return self._map_food(await self._fallback_food(image_bytes, mime_type))
            except Exception as exc:
                errors.append(exc)
                logger.exception("Qwen food analysis fallback failed")
        detail = "AI providers are temporarily unavailable." if errors else "AI provider is not configured."
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)

    async def _gemini_medicine(self, image_bytes: bytes, mime_type: str) -> dict[str, Any]:
        model = genai.GenerativeModel(self.medicine_model_name)
        response = await model.generate_content_async(
            contents=[MEDICINE_PROMPT, {"mime_type": mime_type, "data": image_bytes}],
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json", temperature=0.1
            ),
        )
        return json.loads(response.text)

    async def detect_medicine(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> dict[str, Any]:
        errors: list[Exception] = []
        if self.api_key:
            try:
                return self._normalize_medicine(await self._gemini_medicine(image_bytes, mime_type))
            except Exception as exc:
                errors.append(exc)
                logger.warning("Gemini medicine analysis failed; trying Qwen fallback", exc_info=True)
        if self.openrouter.configured:
            try:
                raw = await self.openrouter.complete_json(
                    MEDICINE_PROMPT, image_bytes=image_bytes, mime_type=mime_type, temperature=0.1
                )
                return self._normalize_medicine(raw)
            except Exception as exc:
                errors.append(exc)
                logger.exception("Qwen medicine analysis fallback failed")
        detail = "AI providers are temporarily unavailable." if errors else "AI provider is not configured."
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)

    @staticmethod
    def _normalize_medicine(raw: dict[str, Any]) -> dict[str, Any]:
        is_medicine = bool(raw.get("is_medicine", False))
        detected = str(raw.get("detected") or ("Unknown Medicine" if is_medicine else "None"))
        valid = {"insulin pen", "medicine", "Unknown Medicine"}
        if is_medicine and detected not in valid:
            detected = "Unknown Medicine"
        return {"is_medicine": is_medicine, "detected": detected if is_medicine else "None"}
