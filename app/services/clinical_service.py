"""ClinicalService — Kalkulasi parameter klinis anak secara otomatis.

Service ini bertanggung jawab untuk:
1. Menghitung kebutuhan kalori harian menggunakan formula WHO Pediatric (1985)
2. Menghitung kebutuhan karbohidrat harian (50% dari total kalori untuk T1DM)
3. Memberikan rekomendasi max sugar berdasarkan tipe diabetes
4. Menyimpan dan mengambil data clinical_parameters dari Supabase
"""

import logging
from datetime import date
from typing import Any, Dict, Optional
from uuid import UUID

from app.core.supabase import get_supabase_service_client
from app.models.database import (
    DIABETES_MAX_SUGAR_RECOMMENDATION,
    ClinicalParameterCreate,
    DiabetesType,
    Gender,
)

logger = logging.getLogger(__name__)


def calculate_age_years(birth_date: date) -> float:
    """Hitung umur dalam tahun dari tanggal lahir.

    Contoh: lahir 2015-01-01, hari ini 2026-08-10 → umur 11.6 tahun
    Menggunakan floating point agar formula WHO lebih akurat.
    """
    today = date.today()
    # Hitung selisih hari kemudian konversi ke tahun
    delta_days = (today - birth_date).days
    return delta_days / 365.25


def calculate_bmr_who(
    weight_kg: float,
    gender: Gender,
    age_years: float
) -> float:
    """Hitung Basal Metabolic Rate (BMR) menggunakan formula WHO/FAO/UNU 1985.

    Formula ini direkomendasikan untuk anak-anak karena lebih akurat
    dibandingkan Mifflin-St Jeor yang dirancang untuk orang dewasa.

    Persamaan berdasarkan kelompok usia (input: berat badan dalam kg):
      Boys (Laki-laki):
        0–3 tahun  : BMR = 60.9 × W – 54
        3–10 tahun : BMR = 22.7 × W + 495
        10–18 tahun: BMR = 17.5 × W + 651
        > 18 tahun : BMR = 15.3 × W + 679  (fallback orang dewasa)

      Girls (Perempuan):
        0–3 tahun  : BMR = 61.0 × W – 51
        3–10 tahun : BMR = 22.5 × W + 499
        10–18 tahun: BMR = 12.2 × W + 746
        > 18 tahun : BMR = 14.7 × W + 496  (fallback orang dewasa)

    Args:
        weight_kg: Berat badan anak dalam kilogram
        gender: Jenis kelamin (Gender.male atau Gender.female)
        age_years: Umur dalam tahun (float, misal 11.6)

    Returns:
        BMR dalam kkal/hari
    """
    if gender == Gender.male:
        if age_years < 3:
            return 60.9 * weight_kg - 54
        elif age_years < 10:
            return 22.7 * weight_kg + 495
        elif age_years < 18:
            return 17.5 * weight_kg + 651
        else:
            return 15.3 * weight_kg + 679
    else:  # female
        if age_years < 3:
            return 61.0 * weight_kg - 51
        elif age_years < 10:
            return 22.5 * weight_kg + 499
        elif age_years < 18:
            return 12.2 * weight_kg + 746
        else:
            return 14.7 * weight_kg + 496


def calculate_daily_targets(
    weight_kg: float,
    height_cm: float,
    birth_date: date,
    gender: Gender,
    diabetes_type: DiabetesType = DiabetesType.type1,
) -> Dict[str, Any]:
    """Hitung target kalori, karbohidrat, dan rekomendasi max sugar harian.

    Kalori = BMR × activity_factor
    - Activity factor untuk anak T1DM: 1.3 (light-moderately active)
      Dipakai untuk semua tipe diabetes karena targetnya adalah anak.

    Karbohidrat:
    - Untuk anak dengan diabetes, rekomendasi ADA: 45–60% dari total kalori
    - Kita gunakan 50% sebagai default (konsisten dan aman untuk T1DM)
    - Karbs grams = (kalori × 50%) / 4 kcal per gram

    Max sugar:
    - Diambil dari DIABETES_MAX_SUGAR_RECOMMENDATION berdasarkan tipe diabetes
    - Dokter bisa override nilai ini via PATCH /clinical/{child_id}

    Args:
        weight_kg: Berat badan dalam kg
        height_cm: Tinggi badan dalam cm (disimpan tapi tidak dipakai formula ini)
        birth_date: Tanggal lahir anak
        gender: Jenis kelamin
        diabetes_type: Tipe diabetes (menentukan rekomendasi max sugar)

    Returns:
        Dict dengan keys: target_daily_calories, target_daily_carbs, recommended_max_sugar_g
    """
    age_years = calculate_age_years(birth_date)
    bmr = calculate_bmr_who(weight_kg, gender, age_years)

    # Activity factor: 1.3 untuk anak dengan aktivitas ringan-sedang
    activity_factor = 1.3
    total_calories = bmr * activity_factor

    # Karbohidrat: 50% dari total kalori, 1 gram karbohidrat = 4 kcal
    carbs_grams = (total_calories * 0.50) / 4.0

    # Max sugar berdasarkan tipe diabetes
    recommended_sugar = DIABETES_MAX_SUGAR_RECOMMENDATION[diabetes_type]

    return {
        "target_daily_calories": round(total_calories),
        "target_daily_carbs": round(carbs_grams, 1),
        "recommended_max_sugar_g": recommended_sugar,
        "age_years_at_calculation": round(age_years, 1),
        "bmr_kcal": round(bmr, 1),
    }


class ClinicalService:
    """Service untuk mengelola data clinical_parameters.

    Memisahkan logika bisnis (kalkulasi WHO) dari layer API.
    Endpoint clinical.py hanya memanggil method di sini.
    """

    def create_clinical_record(
        self,
        params: ClinicalParameterCreate,
        birth_date: Optional[date] = None,
        gender: Optional[Gender] = None,
    ) -> Dict[str, Any]:
        """Buat record clinical_parameters baru.

        Jika birth_date dan gender tersedia (dari profil anak),
        kalori dan karbohidrat dihitung otomatis.
        Jika tidak, target_daily_calories yang diinput manual dipakai.

        Args:
            params: Data input dari request body (ClinicalParameterCreate)
            birth_date: Tanggal lahir anak (diambil dari tabel users)
            gender: Jenis kelamin anak (diambil dari tabel users)

        Returns:
            Data record yang baru diinsert dari Supabase
        """
        client = get_supabase_service_client()

        # Konversi model ke dict, abaikan field yang tidak diisi (None)
        data = params.model_dump(exclude_unset=True)
        data["child_id"] = str(params.child_id)
        data["recorded_by"] = str(params.recorded_by)

        # Auto-calculate jika data anak tersedia
        if birth_date and gender and not data.get("target_daily_calories"):
            try:
                targets = calculate_daily_targets(
                    weight_kg=params.weight_kg,
                    height_cm=params.height_cm,
                    birth_date=birth_date,
                    gender=gender,
                    diabetes_type=params.diabetes_type,
                )
                data["target_daily_calories"] = targets["target_daily_calories"]
                data["target_daily_carbs"] = targets["target_daily_carbs"]

                # Isi rekomendasi max_sugar jika dokter tidak input manual
                if not data.get("max_sugar_intake_g"):
                    data["max_sugar_intake_g"] = targets["recommended_max_sugar_g"]

                logger.info(
                    f"Auto-calculated targets for child {params.child_id}: "
                    f"{targets['target_daily_calories']} kcal/day, "
                    f"age={targets['age_years_at_calculation']}y, "
                    f"bmr={targets['bmr_kcal']} kcal"
                )
            except Exception as e:
                logger.warning(
                    f"Gagal auto-calculate kalori untuk {params.child_id}: {e}. "
                    "Menggunakan nilai manual jika ada."
                )

        # Simpan ke database
        # Konversi enum ke value string agar bisa diserialisasi
        if "diabetes_type" in data and hasattr(data["diabetes_type"], "value"):
            data["diabetes_type"] = data["diabetes_type"].value

        response = client.table("clinical_parameters").insert(data).execute()
        if not response.data:
            raise ValueError("Gagal menyimpan parameter klinis ke database")

        return response.data[0]

    def get_child_profile(self, child_id: UUID) -> Optional[Dict[str, Any]]:
        """Ambil profil anak (birth_date, gender) dari tabel users.

        Dipakai untuk mengambil data yang diperlukan auto-calculation.
        Mengembalikan None jika anak tidak ditemukan atau data tidak lengkap.
        """
        client = get_supabase_service_client()
        try:
            response = (
                client.table("users")
                .select("id, birth_date, gender, full_name")
                .eq("id", str(child_id))
                .single()
                .execute()
            )
            return response.data
        except Exception as e:
            logger.warning(f"Gagal mengambil profil anak {child_id}: {e}")
            return None

    def preview_calculation(
        self,
        weight_kg: float,
        height_cm: float,
        birth_date: date,
        gender: Gender,
        diabetes_type: DiabetesType = DiabetesType.type1,
    ) -> Dict[str, Any]:
        """Preview kalkulasi WHO tanpa menyimpan ke database.

        Berguna untuk dokter melihat estimasi sebelum menyimpan data.
        Endpoint: GET /clinical/preview
        """
        return calculate_daily_targets(
            weight_kg=weight_kg,
            height_cm=height_cm,
            birth_date=birth_date,
            gender=gender,
            diabetes_type=diabetes_type,
        )
