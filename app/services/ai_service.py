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
    weight_g: float = Field(gt=0, le=5000, description="Estimated ingredient weight in grams")
    kcal_per_100g: float = Field(ge=0, le=900)
    protein_g_per_100g: float = Field(ge=0, le=100)
    fat_g_per_100g: float = Field(ge=0, le=100)
    carbs_g_per_100g: float = Field(ge=0, le=100)
    sugar_g_per_100g: float = Field(ge=0, le=100)
    fiber_g_per_100g: float = Field(ge=0, le=100)


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
    "standard high-confidence ingredients needed for nutrition estimation. For a uniform composite "
    "food such as ice cream, bread, cake, soup, or fried rice, return the recognized dish itself as "
    "one ingredient instead of inventing hidden components. For a visibly mixed vegetable dish, list "
    "each visible vegetable so fiber is not lost. Estimate weight_g in grams. Also provide conservative "
    "per-100g estimates for kcal, protein, fat, carbs, total sugar, and dietary fiber for fallback use; "
    "total sugar must not be zero for clearly sweet food such as ice cream. Fiber must not be zero when "
    "a meaningful amount of vegetables, legumes, fruit, or whole grain is visible. Return only JSON with "
    "keys is_food, food_name, and ingredients. Each ingredient uses keys name, weight_g, kcal_per_100g, "
    "protein_g_per_100g, fat_g_per_100g, carbs_g_per_100g, sugar_g_per_100g, fiber_g_per_100g."
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
            match = self.food_data_service.resolve_by_name(item.name)
            mapped_item: dict[str, Any] = {
                "ingredient": item.name,
                "description": match["description"] if match else item.name,
                "weight_g": item.weight_g,
                "fdcId": match.get("fdcId") if match else None,
                "tkpiCode": match.get("tkpiCode") if match else None,
                "dataSource": match.get("dataSource", "USDA FoodData Central") if match else "AI estimate",
                "sugarEstimated": bool(match.get("sugarEstimated", False)) if match else True,
            }
            if not match:
                estimates = {
                    "kcal": item.kcal_per_100g,
                    "protein_g": item.protein_g_per_100g,
                    "fat_g": item.fat_g_per_100g,
                    "carbs_g": item.carbs_g_per_100g,
                    "sugar_g": item.sugar_g_per_100g,
                    "fiber_g": item.fiber_g_per_100g,
                }
                estimates["sugar_g"] = min(float(estimates["sugar_g"]), float(estimates["carbs_g"]))
                estimates["fiber_g"] = min(float(estimates["fiber_g"]), float(estimates["carbs_g"]))
                mapped_item["nutrition_per_100g"] = estimates
            mapped.append(mapped_item)
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
