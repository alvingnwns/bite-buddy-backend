"""FoodDataService — In-memory loader dan lookup engine untuk USDA FoodData Central.

File JSON (app/data/FoodData_Central_foundation_food_json_2026-04-30.json)
di-load SEKALI saat startup aplikasi dan disimpan di memori (~50MB RAM).
Setiap request lookup hanya perlu query dict in-memory — sangat cepat (O(1)).

Cara penggunaan:
  from app.services.food_data_service import get_food_data_service

  svc = get_food_data_service()
  result = svc.lookup_by_fdc_id(321358)
  # → {"fdcId": 321358, "description": "Hummus, commercial", "kcal": 229, ...}

  matches = svc.search_by_name("tomato")
  # → [{"fdcId": 170457, "description": "Tomatoes, raw", ...}, ...]

Nutrient IDs yang dipakai dari FoodData Central:
  1008 → Energy (kcal)
  1003 → Protein (g)
  1004 → Total lipid / Fat (g)
  1005 → Carbohydrate, by difference (g)
  1063 → Sugars, Total (g)
  1079 → Fiber, total dietary (g)
"""

import json
import logging
import os
from functools import lru_cache
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Nutrient IDs dari standar USDA FoodData Central
_NUTRIENT_ENERGY_KCAL = 1008
_NUTRIENT_PROTEIN = 1003
_NUTRIENT_FAT = 1004
_NUTRIENT_CARBS = 1005
_NUTRIENT_SUGAR = 1063
_NUTRIENT_FIBER = 1079

# Tipe data untuk satu item nutrisi yang sudah disederhanakan
NutritionEntry = Dict[str, object]


def _extract_nutrients(food_nutrients: list) -> Dict[str, Optional[float]]:
    """Ekstrak hanya nutrisi yang kita butuhkan dari daftar foodNutrients.

    FoodData Central menyimpan BANYAK sekali nutrisi (vitamin, asam lemak, dll).
    Kita hanya butuh 6: kalori, protein, lemak, karbohidrat, gula, serat.

    Semua nilai adalah per 100g bahan makanan.

    Args:
        food_nutrients: List objek FoodNutrient dari JSON mentah

    Returns:
        Dict dengan keys: kcal, protein_g, fat_g, carbs_g, sugar_g, fiber_g
        Value None jika nutrisi tidak tersedia di data
    """
    # Buat lookup dict nutrient_id → amount dari list
    nutrient_map: Dict[int, float] = {}
    for fn in food_nutrients:
        nutrient_id = fn.get("nutrient", {}).get("id")
        amount = fn.get("amount")
        if nutrient_id and amount is not None:
            nutrient_map[int(nutrient_id)] = float(amount)

    return {
        "kcal": nutrient_map.get(_NUTRIENT_ENERGY_KCAL),
        "protein_g": nutrient_map.get(_NUTRIENT_PROTEIN),
        "fat_g": nutrient_map.get(_NUTRIENT_FAT),
        "carbs_g": nutrient_map.get(_NUTRIENT_CARBS),
        "sugar_g": nutrient_map.get(_NUTRIENT_SUGAR),
        "fiber_g": nutrient_map.get(_NUTRIENT_FIBER),
    }


class FoodDataService:
    """In-memory index untuk FoodData Central.

    Diinisialisasi sekali saat startup via get_food_data_service().
    Menyimpan dua index:
      1. _by_id   : {fdcId → NutritionEntry}   → lookup O(1) by ID
      2. _by_name : {lowercased_word → [fdcId]} → search by keyword

    Data yang disimpan per entry:
      fdcId, description, kcal, protein_g, fat_g, carbs_g, sugar_g, fiber_g
    """

    def __init__(self, json_path: str) -> None:
        """Load dan index FoodData JSON dari path yang diberikan.

        Args:
            json_path: Path absolut ke file JSON FoodData Central

        Raises:
            FileNotFoundError: Jika file tidak ditemukan
            json.JSONDecodeError: Jika file bukan JSON yang valid
        """
        self._by_id: Dict[int, NutritionEntry] = {}
        self._by_name: Dict[str, List[int]] = {}  # keyword → list fdcId
        self._total_loaded = 0

        logger.info(f"Memuat FoodData Central dari: {json_path}")
        self._load(json_path)
        logger.info(
            f"FoodData dimuat: {self._total_loaded} makanan terindex. "
            f"Ukuran index: {len(self._by_id)} entries."
        )

    def _load(self, json_path: str) -> None:
        """Parse JSON dan bangun kedua index."""
        with open(json_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        # FoundationFoods adalah key utama di file FoodData Central
        foods = raw.get("FoundationFoods", [])

        for food in foods:
            # Skip item None yang kadang muncul di JSON (malformed data)
            if not food or not isinstance(food, dict):
                continue

            fdc_id = food.get("fdcId")
            description = food.get("description", "")
            food_nutrients = food.get("foodNutrients", [])

            if not fdc_id or not description:
                continue

            # Ekstrak hanya nutrisi yang kita butuhkan
            nutrients = _extract_nutrients(food_nutrients)

            # Skip makanan yang tidak punya data kalori
            if nutrients["kcal"] is None:
                continue

            entry: NutritionEntry = {
                "fdcId": fdc_id,
                "description": description,
                **nutrients,
            }

            # Index 1: lookup by fdcId
            self._by_id[int(fdc_id)] = entry

            # Index 2: inverted index by kata (untuk search by name)
            # Contoh: "Tomatoes, grape, raw" → ["tomatoes", "grape", "raw"]
            for word in description.lower().replace(",", " ").split():
                if len(word) >= 3:  # Abaikan kata pendek (a, of, the, dll)
                    if word not in self._by_name:
                        self._by_name[word] = []
                    self._by_name[word].append(int(fdc_id))

            self._total_loaded += 1

    def lookup_by_fdc_id(self, fdc_id: int) -> Optional[NutritionEntry]:
        """Cari data nutrisi berdasarkan fdcId USDA.

        Args:
            fdc_id: ID unik makanan di USDA FoodData Central

        Returns:
            NutritionEntry atau None jika tidak ditemukan
        """
        return self._by_id.get(fdc_id)

    def search_by_name(self, query: str, max_results: int = 10) -> List[NutritionEntry]:
        """Cari makanan berdasarkan nama (partial match).

        Cara kerja:
          1. Pecah query menjadi kata-kata
          2. Setiap kata di-lookup di inverted index
          3. fdcId yang muncul di SEMUA kata mendapat skor tertinggi
          4. Kembalikan top N hasil

        Contoh:
          search_by_name("raw tomato") → cari makanan yang namanya
          mengandung kata "raw" DAN/ATAU "tomato"

        Args:
            query: Nama makanan dalam bahasa Inggris
            max_results: Maksimal hasil yang dikembalikan

        Returns:
            List NutritionEntry, diurutkan dari paling relevan
        """
        words = [w.lower() for w in query.replace(",", " ").split() if len(w) >= 3]

        if not words:
            return []

        # Hitung skor: berapa banyak kata dari query yang cocok per fdcId
        scores: Dict[int, int] = {}
        for word in words:
            for fdc_id in self._by_name.get(word, []):
                scores[fdc_id] = scores.get(fdc_id, 0) + 1

        # Sort by skor (descending), ambil top N
        sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)[:max_results]

        return [self._by_id[fdc_id] for fdc_id in sorted_ids if fdc_id in self._by_id]

    def calculate_nutrition_for_meal(
        self, ingredients: List[Dict]
    ) -> Dict[str, float]:
        """Hitung total nutrisi untuk satu meal dari daftar bahan + berat.

        Rumus: nutrisi_total = Σ (nutrisi_per_100g × berat_g / 100)

        Args:
            ingredients: List dict dengan format:
                [{"fdcId": 321358, "weight_g": 150}, ...]

        Returns:
            Dict total nutrisi: {"kcal": ..., "carbs_g": ..., "sugar_g": ...,
                                  "protein_g": ..., "fat_g": ..., "fiber_g": ...}
        """
        totals = {
            "kcal": 0.0,
            "carbs_g": 0.0,
            "sugar_g": 0.0,
            "protein_g": 0.0,
            "fat_g": 0.0,
            "fiber_g": 0.0,
        }

        for item in ingredients:
            fdc_id = item.get("fdcId")
            weight_g = float(item.get("weight_g", 0))

            if not fdc_id or weight_g <= 0:
                continue

            entry = self.lookup_by_fdc_id(int(fdc_id))
            if not entry:
                logger.warning(f"fdcId {fdc_id} tidak ditemukan di FoodData index")
                continue

            # Faktor konversi: data per 100g → per weight_g
            factor = weight_g / 100.0

            for key in totals:
                val = entry.get(key)
                if val is not None:
                    totals[key] += float(val) * factor

        # Bulatkan ke 1 desimal
        return {k: round(v, 1) for k, v in totals.items()}

    @property
    def total_foods(self) -> int:
        """Jumlah makanan yang berhasil di-load."""
        return self._total_loaded


# ──────────────────────────────────────────────
# Singleton — load sekali saja saat pertama kali dipanggil
# ──────────────────────────────────────────────

_instance: Optional[FoodDataService] = None

def get_food_data_service() -> FoodDataService:
    """Kembalikan singleton FoodDataService.

    Instance dibuat sekali saat pertama kali dipanggil,
    kemudian di-cache untuk request berikutnya.

    Jika file JSON tidak ditemukan, mengembalikan service kosong
    agar aplikasi tetap bisa jalan (graceful degradation).
    """
    global _instance
    if _instance is not None:
        return _instance

    # Tentukan path file JSON relatif ke root project
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    json_path = os.path.join(base_dir, "app", "data", "FoodData_Central_foundation_food_json_2026-04-30.json")

    if not os.path.exists(json_path):
        logger.error(
            f"File FoodData tidak ditemukan di: {json_path}. "
            "Lookup nutrisi tidak akan berfungsi. "
            "Pastikan file ada di app/data/"
        )
        # Buat instance kosong agar tidak crash
        _instance = _EmptyFoodDataService()  # type: ignore
        return _instance

    _instance = FoodDataService(json_path)
    return _instance


class _EmptyFoodDataService(FoodDataService):
    """Fallback service kosong jika file JSON tidak ada.

    Mengembalikan None/empty untuk semua lookup, tapi tidak crash.
    Log warning setiap kali dipanggil.
    """

    def __init__(self) -> None:
        # Tidak memanggil super().__init__ agar tidak crash saat file tidak ada
        self._by_id = {}
        self._by_name = {}
        self._total_loaded = 0
        logger.warning("FoodDataService berjalan dalam mode KOSONG — file JSON tidak ditemukan")

    def _load(self, json_path: str) -> None:
        pass
