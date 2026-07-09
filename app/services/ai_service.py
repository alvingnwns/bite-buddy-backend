import json
import logging
from typing import List, Union

import httpx
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)

HF_MODEL_URL = "https://api-inference.huggingface.co/models/nateraw/food"
HF_MEDICINE_MODEL_URL = "https://api-inference.huggingface.co/models/openai/clip-vit-base-patch32"

class AIService:
    """Service untuk berinteraksi dengan model Kecerdasan Buatan (AI)."""

    def __init__(self) -> None:
        self.use_local_ai = settings.use_local_ai
        self.api_token = settings.hf_api_token
        self.headers = {"Authorization": f"Bearer {self.api_token}"}
        
        self.local_food_model = None
        self.local_medicine_model = None

        if self.use_local_ai:
            logger.info("Memuat model AI ke GPU Lokal (RTX 4060). Ini mungkin memakan waktu beberapa detik...")
            from transformers import pipeline
            import torch
            
            device = 0 if torch.cuda.is_available() else -1
            if device == 0:
                logger.info(f"GPU terdeteksi: {torch.cuda.get_device_name(0)}")
            else:
                logger.warning("GPU tidak terdeteksi, menggunakan CPU.")

            self.local_food_model = pipeline("image-classification", model="nateraw/food", device=device)
            self.local_medicine_model = pipeline("zero-shot-image-classification", model="openai/clip-vit-base-patch32", device=device)
            logger.info("Semua model AI Lokal berhasil dimuat!")

    async def _call_hf_api(self, url: str, payload: Union[dict, bytes], model_name: str) -> Union[dict, list]:
        """Internal helper untuk memanggil Hugging Face API dengan implementasi retry logic dan error handling."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                max_retries = 3
                base_delay = 2.0

                for attempt in range(max_retries):
                    if isinstance(payload, dict):
                        response = await client.post(url, headers=self.headers, json=payload)
                    else:
                        response = await client.post(url, headers=self.headers, content=payload)

                    if response.status_code == 503:
                        if attempt < max_retries - 1:
                            sleep_time = base_delay * (2 ** attempt)
                            logger.info(f"Model HF {model_name} sedang dimuat. Menunggu {sleep_time}s...")
                            import asyncio
                            await asyncio.sleep(sleep_time)
                            continue
                        else:
                            raise HTTPException(
                                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                                detail=f"Model AI {model_name} sedang dimuat oleh server (Cold Start). Silakan coba lagi nanti.",
                            )
                    
                    response.raise_for_status()
                    return response.json()
                    
        except httpx.TimeoutException:
            logger.error(f"AI Service Timeout ({model_name})")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Waktu tunggu (timeout) saat menghubungi server AI {model_name}.",
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"AI Service HTTP Error ({model_name}): {e.response.text}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Gagal mendapatkan respon yang valid dari server AI {model_name}.",
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"AI Service Unknown Error ({model_name}): {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Terjadi kesalahan internal pada layanan AI {model_name}.",
            )

    async def detect_food(self, image_bytes: bytes) -> List[str]:
        """Mengirim gambar ke Hugging Face Inference API untuk mendeteksi makanan."""
        if self.use_local_ai and self.local_food_model:
            import io
            from PIL import Image
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            
            results = self.local_food_model(image)
            
            detected_foods = []
            for item in results:
                if item.get("score", 0) > 0.1:
                    detected_foods.append(item.get("label", "unknown"))
                    
            if not detected_foods:
                detected_foods = ["unknown_food"]
            return detected_foods

        if not self.api_token:
            logger.warning("HF_API_TOKEN kosong di .env. Menggunakan output MOCK/Dummy untuk testing.")
            return ["apple", "sandwich"]

        data = await self._call_hf_api(
            url=HF_MODEL_URL, 
            payload=image_bytes, 
            model_name="Makanan"
        )

        detected_foods = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("score", 0) > 0.1:
                    detected_foods.append(item.get("label", "unknown"))

        if not detected_foods:
            detected_foods = ["unknown_food"]

        return detected_foods

    async def detect_medicine(self, image_bytes: bytes) -> str:
        """Mengirim gambar ke Hugging Face Inference API untuk mendeteksi tipe obat/insulin."""
        if self.use_local_ai and self.local_medicine_model:
            import io
            from PIL import Image
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            
            candidate_labels = ["insulin pen", "medicine bottle", "syringe", "pill"]
            results = self.local_medicine_model(image, candidate_labels=candidate_labels)
            
            if isinstance(results, list) and len(results) > 0:
                top_result = results[0]
                if top_result.get("score", 0) > 0.1:
                    return top_result.get("label", "Unknown Medicine")
            
            return "Unknown Medicine"

        if not self.api_token:
            logger.warning("HF_API_TOKEN kosong di .env. Menggunakan output MOCK untuk obat.")
            return "Insulin Pen (Mock)"

        import base64
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        payload = {
            "inputs": image_b64,
            "parameters": {"candidate_labels": ["insulin pen", "medicine bottle", "syringe", "pill"]}
        }

        data = await self._call_hf_api(
            url=HF_MEDICINE_MODEL_URL, 
            payload=payload, 
            model_name="Obat"
        )

        if isinstance(data, list) and len(data) > 0:
            top_result = data[0]
            if isinstance(top_result, dict) and top_result.get("score", 0) > 0.1:
                return top_result.get("label", "Unknown Medicine")

        return "Unknown Medicine"
