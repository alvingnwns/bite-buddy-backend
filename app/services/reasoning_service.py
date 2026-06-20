from typing import Dict, List


class ReasoningService:
    """Service untuk Multimodal Reasoning (menghitung nutrisi)."""

    def __init__(self) -> None:
        # Mock Database Nutrisi Sederhana (Kalori, Karbohidrat dalam gram)
        # Pada produksi, ini akan merujuk ke database tabel Supabase khusus 
        # atau API eksternal pihak ketiga (seperti FatSecret / USDA).
        self.nutrition_db: Dict[str, Dict[str, float]] = {
            "apple": {"calories": 95, "carbs": 25},
            "sandwich": {"calories": 250, "carbs": 33},
            "pizza": {"calories": 285, "carbs": 36},
            "burger": {"calories": 354, "carbs": 29},
            "salad": {"calories": 150, "carbs": 10},
            "unknown_food": {"calories": 100, "carbs": 15},  # Default fallback
        }

    def estimate_nutrition(self, food_items: List[str]) -> Dict[str, float]:
        """
        Menghitung estimasi total kalori dan karbohidrat dari daftar makanan.

        Args:
            food_items: Daftar nama makanan yang terdeteksi oleh AI.

        Returns:
            Dict: Berisi total_calories dan total_carbs.
        """
        total_calories = 0.0
        total_carbs = 0.0
        processed_foods = []

        for item in food_items:
            # Normalisasi ke lowercase
            key = item.lower().strip()
            
            # Ambil data nutrisi jika ada, jika tidak ada pakai default
            nutrition = self.nutrition_db.get(key, self.nutrition_db["unknown_food"])
            
            total_calories += nutrition["calories"]
            total_carbs += nutrition["carbs"]
            processed_foods.append(key)

        return {
            "foods_detected": processed_foods,
            "total_calories": total_calories,
            "total_carbs": total_carbs,
        }

