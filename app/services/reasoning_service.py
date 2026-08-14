"""Service untuk Multimodal Reasoning (menghitung nutrisi dan mengevaluasi kesehatan makanan)."""

import json
import logging
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types
from fastapi import HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.food_data_service import get_food_data_service
from app.services.openrouter_service import OpenRouterService

logger = logging.getLogger(__name__)
NO_AUTO_FUNCTION_CALLING = types.AutomaticFunctionCallingConfig(disable=True)

class MealEvaluation(BaseModel):
    is_healthy: bool = Field(description="Apakah makanan ini tergolong sehat untuk penderita diabetes/anak-anak secara umum?")
    health_score: int = Field(description="Skor kesehatan makanan dari 0 sampai 100")
    explanation: str = Field(description="Penjelasan singkat berbahasa Indonesia mengapa makanan ini sehat atau tidak")

class ReasoningService:
    def __init__(self) -> None:
        self.food_data_service = get_food_data_service()
        self.api_key = settings.gemini_api_key
        self.nutrition_model_name = getattr(settings, "gemini_nutrition_model", "gemini-3.5-flash")
        self.gemini = genai.Client(api_key=self.api_key) if self.api_key else None
        self.openrouter = OpenRouterService()

    def calculate_totals(self, confirmed_ingredients: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Menghitung total nutrisi berdasarkan list ingredients yang sudah dikonfirmasi.
        Sesuai flow: Hitung berdasarkan data dari FoodData (berat * makro/100g).
        """
        return self.food_data_service.calculate_nutrition_for_meal(confirmed_ingredients)

    async def evaluate_meal_health(
        self, confirmed_ingredients: List[Dict[str, Any]], totals: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Menggunakan Gemini API untuk mengevaluasi apakah total nutrisi meal ini 
        tergolong sehat (khususnya konteks diabetes anak).
        """
        ingredients_text = ", ".join([
            f"{item.get('description', item.get('ingredient', 'Unknown'))} ({item.get('weight_g', 0)}g)"
            for item in confirmed_ingredients
        ])
        prompt = (
            "You are an expert pediatric nutritionist specializing in Type 1 Diabetes. "
            "Analyze only the supplied meal; do not invent ingredients or clinical facts.\n"
            f"Ingredients: {ingredients_text}\n"
            f"Total Calories: {totals.get('kcal', 0)} kcal\n"
            f"Total Carbs: {totals.get('carbs_g', 0)} g\n"
            f"Total Sugar: {totals.get('sugar_g', 0)} g\n"
            f"Total Protein: {totals.get('protein_g', 0)} g\n"
            f"Total Fat: {totals.get('fat_g', 0)} g\n"
            f"Total Fiber: {totals.get('fiber_g', 0)} g\n\n"
            "Return only JSON containing boolean is_healthy, integer health_score (0-100), "
            "and a short Indonesian explanation suitable for a child and parent."
        )

        if self.api_key:
            try:
                if self.gemini is None:
                    raise RuntimeError("Gemini is not configured")
                response = await self.gemini.aio.models.generate_content(
                    model=self.nutrition_model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=MealEvaluation,
                        temperature=0.3,
                        automatic_function_calling=NO_AUTO_FUNCTION_CALLING,
                    ),
                )
                return MealEvaluation.model_validate_json(response.text).model_dump()
            except Exception:
                logger.warning("Gemini meal evaluation failed; trying Qwen fallback", exc_info=True)

        if self.openrouter.configured:
            try:
                raw = await self.openrouter.complete_json(prompt, temperature=0.3)
                return MealEvaluation.model_validate(raw).model_dump()
            except Exception:
                logger.exception("Qwen meal evaluation fallback failed")

        is_healthy = totals.get("sugar_g", 0) < 15 and totals.get("fiber_g", 0) > 2
        return {
            "is_healthy": is_healthy,
            "health_score": 70 if is_healthy else 40,
            "explanation": "Evaluasi AI sedang tidak tersedia; penilaian sementara memakai batas gula dan serat.",
        }

    async def process_confirmed_meal(self, confirmed_ingredients: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Alur utama yang dipanggil oleh endpoint /confirm.
        Menghitung total, mengevaluasi kesehatan, dan mengembalikan hasil lengkap.
        """
        # 1. Hitung total exact dari FoodData in-memory (sangat cepat)
        totals = self.calculate_totals(confirmed_ingredients)
        
        # 2. AI Evaluator (butuh ~1-2 detik)
        evaluation = await self.evaluate_meal_health(confirmed_ingredients, totals)
        
        return {
            "foods_detected": [item.get("description", item.get("ingredient")) for item in confirmed_ingredients],
            "total_calories": totals.get("kcal", 0),
            "total_carbs": totals.get("carbs_g", 0),
            "total_sugar": totals.get("sugar_g", 0),
            "total_protein": totals.get("protein_g", 0),
            "total_fat": totals.get("fat_g", 0),
            "total_fiber": totals.get("fiber_g", 0),
            "is_healthy": evaluation.get("is_healthy", True),
            "health_score": evaluation.get("health_score", 100),
            "explanation": evaluation.get("explanation", ""),
            "ingredients_detail": confirmed_ingredients
        }
