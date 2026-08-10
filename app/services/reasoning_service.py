"""Service untuk Multimodal Reasoning (menghitung nutrisi dan mengevaluasi kesehatan makanan)."""

import json
import logging
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from fastapi import HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.food_data_service import get_food_data_service

logger = logging.getLogger(__name__)

if settings.gemini_api_key:
    genai.configure(api_key=settings.gemini_api_key)

class MealEvaluation(BaseModel):
    is_healthy: bool = Field(description="Apakah makanan ini tergolong sehat untuk penderita diabetes/anak-anak secara umum?")
    health_score: int = Field(description="Skor kesehatan makanan dari 0 sampai 100")
    explanation: str = Field(description="Penjelasan singkat berbahasa Indonesia mengapa makanan ini sehat atau tidak")

class ReasoningService:
    def __init__(self) -> None:
        self.food_data_service = get_food_data_service()
        self.api_key = settings.gemini_api_key
        self.nutrition_model_name = getattr(settings, "gemini_nutrition_model", "gemini-3.5-flash")

    def calculate_totals(self, confirmed_ingredients: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Menghitung total nutrisi berdasarkan list ingredients yang sudah dikonfirmasi
        dan diedit beratnya (gram) oleh user.
        """
        return self.food_data_service.calculate_nutrition_for_meal(confirmed_ingredients)

    async def evaluate_meal_health(
        self, confirmed_ingredients: List[Dict[str, Any]], totals: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Menggunakan Gemini API untuk mengevaluasi apakah total nutrisi meal ini 
        tergolong sehat (khususnya konteks diabetes anak).
        """
        if not self.api_key:
            logger.warning("Menggunakan MOCK untuk evaluasi nutrisi.")
            return {
                "is_healthy": totals.get("sugar_g", 0) < 15,
                "health_score": 80,
                "explanation": "Evaluasi Mock: Makanan ini tergolong cukup baik (Mock Data)."
            }

        try:
            model = genai.GenerativeModel(self.nutrition_model_name)
            
            # Format data untuk dianalisis oleh model
            ingredients_text = ", ".join([
                f"{item.get('description', item.get('ingredient', 'Unknown'))} ({item.get('weight_g', 0)}g)" 
                for item in confirmed_ingredients
            ])
            
            prompt = (
                "You are an expert pediatric nutritionist specializing in Type 1 Diabetes. "
                "Analyze the following meal based on its total macronutrients and ingredients.\n"
                f"Ingredients: {ingredients_text}\n"
                f"Total Calories: {totals.get('kcal', 0)} kcal\n"
                f"Total Carbs: {totals.get('carbs_g', 0)} g\n"
                f"Total Sugar: {totals.get('sugar_g', 0)} g\n"
                f"Total Protein: {totals.get('protein_g', 0)} g\n"
                f"Total Fat: {totals.get('fat_g', 0)} g\n"
                f"Total Fiber: {totals.get('fiber_g', 0)} g\n\n"
                "Provide an evaluation in JSON format containing boolean 'is_healthy', an integer 'health_score' (0-100), "
                "and a short 'explanation' in Indonesian on why it is or isn't healthy for a child."
            )
            
            response = await model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=MealEvaluation,
                    temperature=0.3,
                ),
            )
            
            evaluation = json.loads(response.text)
            return evaluation

        except Exception as e:
            logger.error(f"Error pada Gemini Meal Evaluation: {str(e)}")
            # Fallback ke evaluasi algoritmik sederhana jika AI gagal
            is_healthy = totals.get("sugar_g", 0) < 15 and totals.get("fiber_g", 0) > 2
            return {
                "is_healthy": is_healthy,
                "health_score": 70 if is_healthy else 40,
                "explanation": "Evaluasi AI sedang tidak tersedia. (Fallback Algoritma)"
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

