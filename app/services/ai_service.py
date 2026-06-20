import json
import logging
from typing import List

import httpx
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)

# Menggunakan model Hugging Face.
# Catatan: Karena kita sedang mengembangkan purwarupa, kita menggunakan model 
# klasifikasi gambar makanan / objek umum yang ringan.
HF_MODEL_URL = "https://api-inference.huggingface.co/models/nateraw/food"

# Model Zero-Shot Image Classification untuk Obat/Insulin
# Sangat fleksibel, kita bisa mendeteksi tanpa perlu melatih dataset.
HF_MEDICINE_MODEL_URL = "https://api-inference.huggingface.co/models/openai/clip-vit-base-patch32"

class AIService:
    """Service untuk berinteraksi dengan model Kecerdasan Buatan (AI)."""

    def __init__(self) -> None:
        self.api_token = settings.hf_api_token
        self.headers = {"Authorization": f"Bearer {self.api_token}"}

    async def detect_food(self, image_bytes: bytes) -> List[str]:
        """
        Mengirim gambar ke Hugging Face Inference API untuk mendeteksi makanan.

        Args:
            image_bytes: Byte gambar makanan.

        Returns:
            List[str]: Daftar nama makanan yang terdeteksi (label).
        """
        if not self.api_token:
            logger.warning(
                "HF_API_TOKEN kosong di .env. Menggunakan output MOCK/Dummy untuk testing."
            )
            # MOCK OUTPUT (Untuk testing jika token belum ada)
            return ["apple", "sandwich"]

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Implementasi Retry Logic dengan Exponential Backoff
                # Sangat berguna untuk API gratis Hugging Face yang sering 'Cold Start'
                max_retries = 3
                base_delay = 2.0  # detik

                for attempt in range(max_retries):
                    response = await client.post(
                        HF_MODEL_URL,
                        headers=self.headers,
                        content=image_bytes,
                    )

                    # Jika model sedang loading (Cold Start) atau server sibuk
                    if response.status_code == 503:
                        if attempt < max_retries - 1:
                            # Hitung exponential backoff: 2s, 4s, 8s...
                            sleep_time = base_delay * (2 ** attempt)
                            logger.info(f"Model HF sedang dimuat. Menunggu {sleep_time} detik (Percobaan {attempt+1}/{max_retries})...")
                            import asyncio
                            await asyncio.sleep(sleep_time)
                            continue
                        else:
                            raise HTTPException(
                                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                                detail="Model AI sedang dimuat oleh server (Cold Start). Silakan coba lagi nanti.",
                            )
                    
                    # Jika statusnya sukses (2xx) atau error lain (4xx/5xx selain 503), keluar dari loop retry
                    response.raise_for_status()
                    break

                data = response.json()

                # Parse response. Format HF Image Classification biasanya:
                # [{"label": "pizza", "score": 0.95}, {"label": "burger", "score": 0.02}]
                detected_foods = []
                for item in data:
                    # Ambil label yang memiliki confidence (score) di atas 10%
                    if isinstance(item, dict) and item.get("score", 0) > 0.1:
                        detected_foods.append(item.get("label", "unknown"))

                if not detected_foods:
                    # Jika AI tidak yakin, kita return default agar sistem tetap jalan
                    detected_foods = ["unknown_food"]

                return detected_foods

        except httpx.TimeoutException:
            logger.error("AI Service Timeout")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Waktu tunggu (timeout) saat menghubungi server AI.",
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"AI Service HTTP Error: {e.response.text}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Gagal mendapatkan respon yang valid dari server AI.",
            )
        except Exception as e:
            logger.error(f"AI Service Unknown Error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Terjadi kesalahan internal pada layanan AI.",
            )

    async def detect_medicine(self, image_bytes: bytes) -> str:
        """
        Mengirim gambar ke Hugging Face Inference API untuk mendeteksi tipe obat/insulin.

        Args:
            image_bytes: Byte gambar obat.

        Returns:
            str: Tipe obat yang terdeteksi (misal: 'NovoRapid Pen').
        """
        if not self.api_token:
            logger.warning(
                "HF_API_TOKEN kosong di .env. Menggunakan output MOCK untuk obat."
            )
            # MOCK OUTPUT
            return "Insulin Pen (Mock)"

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                max_retries = 3
                base_delay = 2.0

                for attempt in range(max_retries):
                    # Zero-Shot Image Classification butuh payload JSON berisi base64 image dan candidate_labels
                    import base64
                    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
                    payload = {
                        "inputs": image_b64,
                        "parameters": {"candidate_labels": ["insulin pen", "medicine bottle", "syringe", "pill"]}
                    }

                    response = await client.post(
                        HF_MEDICINE_MODEL_URL,
                        headers=self.headers,
                        json=payload,
                    )

                    if response.status_code == 503:
                        if attempt < max_retries - 1:
                            sleep_time = base_delay * (2 ** attempt)
                            logger.info(f"Model HF Obat sedang dimuat. Menunggu {sleep_time}s...")
                            import asyncio
                            await asyncio.sleep(sleep_time)
                            continue
                        else:
                            raise HTTPException(
                                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                                detail="Model AI Obat sedang dimuat. Coba lagi nanti.",
                            )
                    
                    response.raise_for_status()
                    break

                data = response.json()

                # Parse response. Untuk CLIP Zero-Shot, response berupa list of dicts:
                # [{"score": 0.9, "label": "insulin pen"}, {"score": 0.05, "label": "syringe"}, ...]
                if isinstance(data, list) and len(data) > 0:
                    top_result = data[0]
                    if isinstance(top_result, dict) and top_result.get("score", 0) > 0.1:
                        return top_result.get("label", "Unknown Medicine")

                return "Unknown Medicine"

        except httpx.TimeoutException:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Waktu tunggu timeout saat menghubungi server AI Obat.",
            )
        except Exception as e:
            logger.error(f"AI Service Medicine Error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Terjadi kesalahan internal pada deteksi obat.",
            )


