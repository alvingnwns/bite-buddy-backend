from typing import Any, Dict, List

class ReasoningService:
    """Service untuk Multimodal Reasoning (menghitung nutrisi)."""

    def __init__(self) -> None:
        # Mock Database Nutrisi Sederhana (Kalori, Karbohidrat dalam gram)
        # Pada produksi, ini akan merujuk ke database tabel Supabase khusus 
        # atau API eksternal pihak ketiga (seperti FatSecret / USDA).
        self.nutrition_db: Dict[str, Dict[str, Any]] = {
            "apple": {"calories": 95, "carbs": 25, "is_healthy": True},
            "sandwich": {"calories": 250, "carbs": 33, "is_healthy": True},
            "pizza": {"calories": 285, "carbs": 36, "is_healthy": False},
            "burger": {"calories": 354, "carbs": 29, "is_healthy": False},
            "salad": {"calories": 150, "carbs": 10, "is_healthy": True},
            "ice cream": {"calories": 207, "carbs": 24, "is_healthy": False},
            "unknown_food": {"calories": 100, "carbs": 15, "is_healthy": True},  # Default fallback
        }

    def estimate_nutrition(self, food_items: List[str]) -> Dict[str, Any]:
        """
        Menghitung estimasi total kalori dan karbohidrat dari daftar makanan,
        serta menentukan apakah keseluruhan makanan sehat.

        Args:
            food_items: Daftar nama makanan yang terdeteksi oleh AI.

        Returns:
            Dict: Berisi total_calories, total_carbs, dan is_healthy.
        """
        total_calories = 0.0
        total_carbs = 0.0
        is_healthy = True
        processed_foods = []

        for item in food_items:
            # Normalisasi ke lowercase
            key = item.lower().strip()
            
            # Ambil data nutrisi jika ada, jika tidak ada pakai default
            nutrition = self.nutrition_db.get(key, self.nutrition_db["unknown_food"])
            
            total_calories += nutrition["calories"]
            total_carbs += nutrition["carbs"]
            
            if not nutrition.get("is_healthy", True):
                is_healthy = False
                
            processed_foods.append(key)

        return {
            "foods_detected": processed_foods,
            "total_calories": total_calories,
            "total_carbs": total_carbs,
            "is_healthy": is_healthy,
        }
