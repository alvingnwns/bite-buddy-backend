"""Service untuk berinteraksi dengan model Kecerdasan Buatan (AI) Gemini."""

import json
import logging
from typing import List, Dict, Any, Optional

import google.generativeai as genai
from fastapi import HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.food_data_service import get_food_data_service

logger = logging.getLogger(__name__)

# Mengkonfigurasi Gemini API key
if settings.gemini_api_key:
    genai.configure(api_key=settings.gemini_api_key)
else:
    logger.warning("GEMINI_API_KEY tidak ditemukan; AI scan dinonaktifkan sampai provider dikonfigurasi.")

class IngredientEstimate(BaseModel):
    name: str = Field(description="Nama bahan makanan mentah (fundamental raw ingredient) dalam bahasa Inggris. Contoh: 'wheat flour', 'egg', 'tomato', 'chicken breast'")
    weight_g: float = Field(description="Estimasi berat bahan makanan dalam gram")

class FoodDetectionResponse(BaseModel):
    is_food: bool = Field(description="False jika gambar BUKAN makanan (contoh: hewan, manusia, benda mati, obat). True jika gambar berisi makanan yang bisa dimakan.")
    food_name: str = Field(description="Nama hidangan utama yang terlihat, bukan daftar bahan. Contoh: 'Ice cream', 'Nasi goreng', atau 'Spaghetti'. Kosong jika bukan makanan.")
    ingredients: List[IngredientEstimate] = Field(description="Daftar bahan makanan mentah penyusun makanan yang terdeteksi. Kosongkan jika is_food adalah false.")

class AIService:
    def __init__(self) -> None:
        self.api_key = settings.gemini_api_key
        self.food_model_name = getattr(settings, "gemini_food_model", "gemini-3.5-flash")
        self.medicine_model_name = getattr(settings, "gemini_medicine_model", "gemini-3.5-flash")
        
        self.food_data_service = get_food_data_service()

    async def detect_food_ingredients(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> tuple[bool, str, List[Dict[str, Any]]]:
        """
        Mengirim gambar ke Gemini API untuk mendeteksi bahan makanan mentah penyusun (raw ingredients) dan estimasi beratnya.
        Kemudian mencocokkan bahan mentah tersebut dengan FDC ID dari FoodData Central.
        Returns:
            Tuple[bool, List[Dict]]: (is_food, list_of_ingredients)
        """
        if not self.api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI provider is not configured.",
            )

        try:
            model = genai.GenerativeModel(self.food_model_name)
            
            prompt = (
                "You are a cautious pediatric nutrition image analyst. Analyze only visible evidence. "
                "First decide whether the image contains edible food. If not, set is_food=false, food_name='', and ingredients=[]. "
                "If it is food, identify the primary dish in food_name using a short consumer-facing name, not a comma-separated ingredient list. "
                "Examples: a scoop or cup of frozen dairy dessert is 'Ice cream'; noodles with tomato sauce are 'Spaghetti'; fried rice is 'Nasi goreng'. "
                "Do not invent unusual hidden ingredients. Never label ice cream as eggplant unless eggplant is clearly visible. "
                "Then list only visually supported or standard high-confidence ingredients needed for nutrition estimation. "
                "Use simple English ingredient names and estimate grams. When uncertain, prefer a generic ingredient such as 'ice cream' over a specific unsupported ingredient."
            )
            
            image_part = {
                "mime_type": mime_type,
                "data": image_bytes
            }
            
            response = await model.generate_content_async(
                contents=[prompt, image_part],
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=FoodDetectionResponse,
                    temperature=0.2,
                ),
            )
            
            result_text = response.text
            data = json.loads(result_text)
            
            is_food = data.get("is_food", True)
            food_name = str(data.get("food_name") or "Food").strip()
                
            ingredients = data.get("ingredients", [])
            
            mapped_ingredients = []
            for item in ingredients:
                name = item.get("name", "")
                weight_g = float(item.get("weight_g", 0))
                
                # Cari fdcId terbaik dari FoodData
                search_results = self.food_data_service.search_by_name(name, max_results=1)
                fdc_id = search_results[0]["fdcId"] if search_results else None
                desc = search_results[0]["description"] if search_results else name
                
                mapped_ingredients.append({
                    "ingredient": name,
                    "description": desc,
                    "weight_g": weight_g,
                    "fdcId": fdc_id
                })
                
            return is_food, food_name, mapped_ingredients
            
        except Exception as e:
            logger.error(f"Error AI detect_food_ingredients: {e}")
            if "429" in str(e) or "quota" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="AI provider is temporarily unavailable.",
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Gagal menganalisis gambar dengan AI."
            )

    async def detect_medicine(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> Dict[str, Any]:
        """
        Mengirim gambar ke Gemini API untuk mendeteksi tipe obat atau insulin.
        """
        if not self.api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI provider is not configured.",
            )

        try:
            model = genai.GenerativeModel(self.medicine_model_name)
            
            prompt = (
                "Identify if this image contains any medicine, medical equipment, or pills. "
                "If it does NOT contain any medicine (e.g. it is a cat, food, animal, or person), reply EXACTLY with 'Not Medicine'. "
                "If it's an insulin pen or syringe, reply with 'insulin pen'. "
                "If it's a pill or medicine bottle, reply with 'medicine'. "
                "Otherwise, if it's medical but unknown, reply with 'Unknown Medicine'. "
                "Only output the exact category name."
            )
            
            image_part = {
                "mime_type": mime_type,
                "data": image_bytes
            }
            
            response = await model.generate_content_async(
                contents=[prompt, image_part],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                ),
            )
            
            label = response.text.strip()
            
            if "Not Medicine" in label:
                return {"is_medicine": False, "detected": "None"}
            
            valid_labels = ["insulin pen", "medicine", "Unknown Medicine"]
            for valid in valid_labels:
                if valid.lower() in label.lower():
                    return {"is_medicine": True, "detected": valid}
                    
            return {"is_medicine": True, "detected": "Unknown Medicine"}
            
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Error pada Gemini Medicine Detection: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Gagal mendeteksi obat dari gambar."
            )
