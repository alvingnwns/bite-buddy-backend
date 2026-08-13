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

import csv
import json
import logging
import os
import re
import unicodedata
from functools import lru_cache
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_NUTRIENT_ENERGY_KCAL = [1008, 1062, 2047, 2048]
_NUTRIENT_PROTEIN = [1003]
_NUTRIENT_FAT = [1004, 1085]
_NUTRIENT_CARBS = [1005, 1050]
_NUTRIENT_SUGAR = [1063, 2000]
_NUTRIENT_FIBER = [1079, 2033]

# Tipe data untuk satu item nutrisi yang sudah disederhanakan
NutritionEntry = Dict[str, object]

def _get_first_available(nutrient_map: Dict[int, float], ids: List[int]) -> float:
    """Mengambil nilai nutrisi pertama yang tersedia dari daftar ID alternatif. Default ke 0.0 jika tidak ada."""
    for eid in ids:
        if eid in nutrient_map:
            return nutrient_map[eid]
    return 0.0

def _extract_nutrients(food_nutrients: list) -> Dict[str, float]:
    # Buat lookup dict nutrient_id → amount dari list
    nutrient_map: Dict[int, float] = {}
    for fn in food_nutrients:
        nutrient_id = fn.get("nutrient", {}).get("id")
        amount = fn.get("amount")
        if nutrient_id and amount is not None:
            nutrient_map[int(nutrient_id)] = float(amount)

    # Kalori di-treat khusus karena kita skip makanan tanpa kalori
    kcal_val = None
    for eid in _NUTRIENT_ENERGY_KCAL:
        if eid in nutrient_map:
            kcal_val = nutrient_map[eid]
            break

    return {
        "kcal": kcal_val,  # Bisa None, untuk difilter di _load
        "protein_g": _get_first_available(nutrient_map, _NUTRIENT_PROTEIN),
        "fat_g": _get_first_available(nutrient_map, _NUTRIENT_FAT),
        "carbs_g": _get_first_available(nutrient_map, _NUTRIENT_CARBS),
        "sugar_g": _get_first_available(nutrient_map, _NUTRIENT_SUGAR),
        "fiber_g": _get_first_available(nutrient_map, _NUTRIENT_FIBER),
    }


_TKPI_ALIASES = {
    "ice cream": "es krim",
    "fried rice": "nasi goreng",
    "spinach": "bayam",
    "carrot": "wortel",
    "broccoli": "brokoli",
    "cabbage": "kol",
    "lettuce": "selada",
    "tomato": "tomat",
    "cucumber": "ketimun",
    "eggplant": "terong",
    "green bean": "buncis",
    "corn": "jagung",
    "chicken": "ayam",
    "beef": "sapi",
    "fish": "ikan",
    "rice": "nasi",
    "tofu": "tahu",
    "tempeh": "tempe",
}

_SWEET_FOOD_TERMS = {
    "es krim", "ice cream", "gula", "sirup", "permen", "cokelat", "cake",
    "kue", "dodol", "selai", "susu kental manis", "sweetened",
}


def _normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return " ".join(re.findall(r"[a-z0-9]+", normalized))


class FoodDataService:
    def __init__(self, json_path: str, tkpi_path: str | None = None) -> None:
        self._by_id: Dict[int, NutritionEntry] = {}
        self._tkpi_by_code: Dict[str, NutritionEntry] = {}
        self._total_loaded = 0

        logger.info(f"Memuat FoodData Central dari: {json_path}")
        self._load(json_path)
        if tkpi_path and os.path.exists(tkpi_path):
            self._load_tkpi(tkpi_path)
        logger.info(
            f"FoodData dimuat: {self._total_loaded} makanan terindex. "
            f"Ukuran index: {len(self._by_id)} entries."
        )

    def _load_tkpi(self, csv_path: str) -> None:
        """Load only app-relevant TKPI columns; source CSV remains untouched."""
        relevant = {
            "energi_kkal": "kcal", "protein_g": "protein_g", "lemak_g": "fat_g",
            "karbohidrat_g": "carbs_g", "serat_g": "fiber_g",
        }
        with open(csv_path, encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                code = str(row.get("kode") or "").strip()
                name = str(row.get("nama_bahan") or "").strip()
                if not code or not name:
                    continue
                entry: NutritionEntry = {
                    "tkpiCode": code,
                    "description": name,
                    "dataSource": "TKPI 2020",
                    "sourceReference": str(row.get("sumber") or "").strip(),
                    "category": str(row.get("kategori") or "").strip(),
                    "bdd_percent": float(row.get("bdd_persen") or 100),
                    # TKPI 2020 does not contain total sugar. It is completed
                    # conservatively below only for clearly sweet foods.
                    "sugar_g": 0.0,
                }
                valid = True
                for source_key, target_key in relevant.items():
                    try:
                        entry[target_key] = float(row.get(source_key) or 0)
                    except (TypeError, ValueError):
                        valid = False
                        break
                if valid:
                    self._tkpi_by_code[code] = self._complete_missing_nutrients(entry)

    @staticmethod
    def _complete_missing_nutrients(entry: NutritionEntry) -> NutritionEntry:
        """Avoid false zero sugar when the source has no sugar column."""
        name = _normalize_name(str(entry.get("description") or ""))
        carbs = float(entry.get("carbs_g") or 0)
        sugar = float(entry.get("sugar_g") or 0)
        if sugar <= 0 and any(term in name for term in _SWEET_FOOD_TERMS):
            entry["sugar_g"] = round(min(carbs, carbs * 0.85), 2)
            entry["sugarEstimated"] = True
        return entry

    def _load(self, json_path: str) -> None:
        with open(json_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        foods = raw.get("FoundationFoods", [])

        for food in foods:
            if not food or not isinstance(food, dict):
                continue

            fdc_id = food.get("fdcId")
            description = food.get("description", "")
            food_nutrients = food.get("foodNutrients", [])

            if not fdc_id or not description:
                continue

            nutrients = _extract_nutrients(food_nutrients)

            if nutrients["kcal"] is None:
                continue

            entry: NutritionEntry = {
                "fdcId": fdc_id,
                "description": description,
                **nutrients,
            }

            self._by_id[int(fdc_id)] = entry
            self._total_loaded += 1

    def lookup_by_fdc_id(self, fdc_id: int) -> Optional[NutritionEntry]:
        """Cari data nutrisi berdasarkan fdcId USDA."""
        return self._by_id.get(fdc_id)

    def search_by_name(self, query: str, max_results: int = 10) -> List[NutritionEntry]:
        """Cari makanan berdasarkan nama (partial match)."""
        words = [w.lower() for w in query.replace(",", " ").split() if len(w) >= 3]

        if not words:
            return []

        # Cari yang mengandung semua kata, lalu skor berdasarkan pendeknya deskripsi
        matches = []
        for entry in self._by_id.values():
            desc_lower = str(entry["description"]).lower()
            if all(word in desc_lower for word in words):
                matches.append(entry)

        # Sort matches by length of description (ascending) so exact matches appear first
        sorted_matches = sorted(matches, key=lambda x: len(str(x["description"])))

        return sorted_matches[:max_results]

    def search_tkpi_by_name(self, query: str, max_results: int = 10) -> List[NutritionEntry]:
        normalized = _normalize_name(query)
        translated = _TKPI_ALIASES.get(normalized, normalized)
        words = [word for word in translated.split() if len(word) >= 2]
        if not words:
            return []
        matches: list[tuple[int, int, NutritionEntry]] = []
        for entry in self._tkpi_by_code.values():
            description = _normalize_name(str(entry["description"]))
            if all(word in description for word in words):
                exact_rank = 0 if description == translated else 1 if description.startswith(translated) else 2
                matches.append((exact_rank, len(description), entry))
        return [entry for _, _, entry in sorted(matches, key=lambda item: (item[0], item[1]))[:max_results]]

    def resolve_by_name(self, query: str) -> Optional[NutritionEntry]:
        """Prefer an exact/local TKPI match, otherwise use USDA Foundation."""
        tkpi = self.search_tkpi_by_name(query, max_results=1)
        usda = self.search_by_name(query, max_results=1)
        normalized = _normalize_name(query)
        if tkpi and (_TKPI_ALIASES.get(normalized) or _normalize_name(str(tkpi[0]["description"])) == normalized):
            return tkpi[0]
        return usda[0] if usda else (tkpi[0] if tkpi else None)

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
            tkpi_code = item.get("tkpiCode")
            weight_g = float(item.get("weight_g", 0))

            if weight_g <= 0:
                continue

            entry = self._tkpi_by_code.get(str(tkpi_code)) if tkpi_code else None
            if entry is None and fdc_id:
                entry = self.lookup_by_fdc_id(int(fdc_id))
            if entry is None and item.get("nutrition_per_100g"):
                entry = dict(item["nutrition_per_100g"])
            if not entry:
                logger.warning("Ground truth nutrisi tidak ditemukan untuk %s", item.get("ingredient"))
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
    tkpi_path = os.path.join(base_dir, "app", "data", "TKPI_2020_food_composition.csv")

    if not os.path.exists(json_path):
        logger.error(
            f"File FoodData tidak ditemukan di: {json_path}. "
            "Lookup nutrisi tidak akan berfungsi. "
            "Pastikan file ada di app/data/"
        )
        # Buat instance kosong agar tidak crash
        _instance = _EmptyFoodDataService()  # type: ignore
        return _instance

    _instance = FoodDataService(json_path, tkpi_path)
    return _instance


class _EmptyFoodDataService(FoodDataService):
    """Fallback service kosong jika file JSON tidak ada.

    Mengembalikan None/empty untuk semua lookup, tapi tidak crash.
    Log warning setiap kali dipanggil.
    """

    def __init__(self) -> None:
        # Tidak memanggil super().__init__ agar tidak crash saat file tidak ada
        self._by_id = {}
        self._tkpi_by_code = {}
        self._by_name = {}
        self._total_loaded = 0
        logger.warning("FoodDataService berjalan dalam mode KOSONG — file JSON tidak ditemukan")

    def _load(self, json_path: str) -> None:
        pass
