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
    logger.warning("GEMINI_API_KEY tidak ditemukan di .env! Mode Mock/Dummy akan digunakan.")

class IngredientEstimate(BaseModel):
    name: str = Field(description="Nama bahan makanan dalam bahasa Inggris")
    weight_g: float = Field(description="Estimasi berat bahan makanan dalam gram")

class FoodDetectionResponse(BaseModel):
    is_food: bool = Field(description="False jika gambar BUKAN makanan (contoh: hewan, manusia, benda mati, obat). True jika gambar berisi makanan yang bisa dimakan.")
    ingredients: List[IngredientEstimate] = Field(description="Daftar bahan makanan yang terdeteksi. Kosongkan jika is_food adalah false.")

class AIService:
    def __init__(self) -> None:
        self.api_key = settings.gemini_api_key
        # Menggunakan model Gemini Pro Vision (gemini-1.5-pro atau flash tergantung ketersediaan)
        # Kita menggunakan gemini-3.5-flash karena lebih cepat dan sangat baik untuk vision
        self.food_model_name = getattr(settings, "gemini_food_model", "gemini-3.5-flash")
        self.medicine_model_name = getattr(settings, "gemini_medicine_model", "gemini-3.5-flash")
        
        self.food_data_service = get_food_data_service()

    async def detect_food_ingredients(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> List[Dict[str, Any]]:
        """
        Mengirim gambar ke Gemini API untuk mendeteksi bahan makanan dan estimasi berat.
        Kemudian mencocokkan bahan tersebut dengan FDC ID dari FoodData Central.
        """
        if not self.api_key:
            logger.warning("Menggunakan MOCK untuk deteksi makanan.")
            return [
                {"description": "Tomatoes, raw", "weight_g": 50, "fdcId": 170457},
                {"description": "Lettuce, raw", "weight_g": 30, "fdcId": 169247}
            ]

        try:
            model = genai.GenerativeModel(self.food_model_name)
            
            prompt = (
                "You are an expert nutritionist. First, determine if the image actually contains edible food. "
                "If it does NOT contain food (e.g. it's a cat, a car, a person, or medicine), set 'is_food' to false and leave 'ingredients' empty. "
                "If it IS food, set 'is_food' to true and list all fundamental ingredients present in the food. "
                "For each ingredient, estimate its weight in grams. Provide the name in simple English (e.g. 'tomato')."
            )
            
            # Mempersiapkan gambar
            image_part = {
                "mime_type": mime_type,
                "data": image_bytes
            }
            
            # Panggil Gemini dengan Structured Output via JSON schema (Hanya tersedia di versi 1.5+)
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
            
            if not data.get("is_food", True):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Gambar tidak terdeteksi sebagai makanan. Mohon unggah foto makanan yang jelas."
                )
                
            ingredients = data.get("ingredients", [])
            
            # Mapping ke fdcId
            mapped_ingredients = []
            for item in ingredients:
                name = item.get("name", "")
                weight_g = item.get("weight_g", 0)
                
                # Cari fdcId terbaik
                search_results = self.food_data_service.search_by_name(name, max_results=1)
                
                fdc_id = None
                desc = name
                if search_results:
                    fdc_id = search_results[0]["fdcId"]
                    desc = search_results[0]["description"]
                
                mapped_ingredients.append({
                    "ingredient": name,
                    "description": desc,
                    "weight_g": weight_g,
                    "fdcId": fdc_id
                })
                
            return mapped_ingredients

        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Error pada Gemini Food Detection: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Gagal memproses gambar makanan menggunakan AI."
            )

    async def detect_medicine(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
        """
        Mengirim gambar ke Gemini API untuk mendeteksi tipe obat atau insulin.
        """
        if not self.api_key:
            logger.warning("Menggunakan MOCK untuk obat.")
            return "Insulin Pen (Mock)"

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
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Gambar tidak terdeteksi sebagai obat atau alat medis. Mohon unggah foto obat yang jelas."
                )
            
            valid_labels = ["insulin pen", "medicine", "Unknown Medicine"]
            for valid in valid_labels:
                if valid.lower() in label.lower():
                    return valid
                    
            return "Unknown Medicine"
            
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Error pada Gemini Medicine Detection: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Gagal mendeteksi obat dari gambar."
            )
