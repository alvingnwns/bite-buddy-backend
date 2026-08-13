import asyncio
import os
import sys
import json
from pathlib import Path

# Setup sys.path so we can import from app
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from app.services.ai_service import AIService
from app.services.reasoning_service import ReasoningService

async def main():
    if len(sys.argv) < 2:
        print("Penggunaan: python test_gemini_accuracy.py <path_ke_gambar_makanan>")
        sys.exit(1)

    image_path = sys.argv[1]
    
    if not os.path.exists(image_path):
        print(f"Error: Gambar tidak ditemukan di {image_path}")
        sys.exit(1)
        
    print(f"Memulai pengujian akurasi Gemini untuk gambar: {image_path}\n")

    # Inisialisasi Services
    ai_service = AIService()
    reasoning_service = ReasoningService()

    # 1. Mendeteksi Makanan dan Estimasi Berat (Vision AI)
    print("Tahap 1: Mendeteksi makanan dan estimasi berat (Gemini Vision)...")
    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
            
        detected_ingredients = await ai_service.detect_food_ingredients(image_bytes=image_bytes)
        print("Deteksi Berhasil!")
        print(json.dumps(detected_ingredients, indent=2))
        print("-" * 50)
    except Exception as e:
        print(f"Gagal mendeteksi makanan: {str(e)}")
        sys.exit(1)

    if not detected_ingredients:
        print("Tidak ada bahan makanan yang terdeteksi.")
        sys.exit(0)

    # 2. Menghitung Makronutrien dan Mengevaluasi Kesehatan Makanan
    print("Tahap 2: Menghitung Makronutrien & Evaluasi Kesehatan (Gemini Reasoning)...")
    try:
        # Kita lewati tahap konfirmasi user (langsung anggap deteksi AI benar 100% untuk uji coba)
        result = await reasoning_service.process_confirmed_meal(detected_ingredients)
        print("Kalkulasi & Evaluasi Berhasil!\n")
        
        print("=== HASIL PERHITUNGAN NUTRISI ===")
        print(f"Makanan Terdeteksi : {', '.join(result.get('foods_detected', []))}")
        print(f"Total Kalori      : {result.get('total_calories')} kcal")
        print(f"Total Karbohidrat : {result.get('total_carbs')} g")
        print(f"Total Gula        : {result.get('total_sugar')} g")
        print(f"Total Protein     : {result.get('total_protein')} g")
        print(f"Total Lemak       : {result.get('total_fat')} g")
        print(f"Total Serat       : {result.get('total_fiber')} g")
        print("-" * 50)
        
        print("=== EVALUASI KESEHATAN ===")
        print(f"Apakah Sehat? : {'YA (Sehat)' if result.get('is_healthy') else 'TIDAK (Kurang Sehat)'}")
        print(f"Health Score  : {result.get('health_score')}/100")
        print(f"Penjelasan AI : {result.get('explanation')}")
        print("=" * 50)

    except Exception as e:
        print(f"❌ Gagal melakukan evaluasi: {str(e)}")

if __name__ == "__main__":
    # Karena FastAPI berjalan di thread utama, kita jalankan asyncio sendiri untuk script independen
    asyncio.run(main())
