"""Pydantic models that map to the database schema tables.

These models represent the data structures stored in Supabase/PostgreSQL.
They are used for serialization, validation, and API responses.
"""

from datetime import date, datetime, time, timezone
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────

class UserRole(str, Enum):
    """Role pengguna dalam sistem BiteBuddy."""
    doctor = "doctor"
    parent = "parent"
    child = "child"


class Gender(str, Enum):
    """Jenis kelamin — dipakai untuk kalkulasi kalori WHO."""
    male = "male"
    female = "female"


class DiabetesType(str, Enum):
    """Tipe diabetes anak — menentukan rekomendasi awal max sugar intake.

    Rekomendasi max sugar (bisa di-override dokter):
      type1      → < 25g/hari  (ADA standard untuk T1DM)
      type2      → < 25g/hari  (lebih ketat karena resistensi insulin)
      prediabetes → < 36g/hari (WHO guideline)
      gestational → < 25g/hari
    """
    type1 = "type1"
    type2 = "type2"
    prediabetes = "prediabetes"
    gestational = "gestational"


# Peta rekomendasi max sugar per tipe diabetes (dalam gram per hari)
DIABETES_MAX_SUGAR_RECOMMENDATION: dict[DiabetesType, float] = {
    DiabetesType.type1: 25.0,
    DiabetesType.type2: 25.0,
    DiabetesType.prediabetes: 36.0,
    DiabetesType.gestational: 25.0,
}


class MealType(str, Enum):
    """Jenis waktu makan."""
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


class PetType(str, Enum):
    """Jenis virtual pet — 5 pilihan yang tersedia.

    Nilai ini harus sinkron dengan ENUM pet_type di PostgreSQL
    (dibuat di migration 006/007).
    """
    cat = "cat"         # 🐱 Kucing
    dog = "dog"         # 🐶 Anjing
    rabbit = "rabbit"   # 🐰 Kelinci
    hamster = "hamster" # 🐹 Hamster
    bird = "bird"       # 🐦 Burung


class PetStatus(str, Enum):
    """Status kesehatan virtual pet — computed dari happiness + hunger.

    CATATAN SEMANTIK HUNGER (updated 2026-08-10):
      hunger TINGGI = makin KENYANG (++hunger = makin kenyang)
      hunger RENDAH = makin LAPAR

    Status dihitung oleh compute_pet_status() berdasarkan threshold ini.
    """
    happy = "happy"
    neutral = "neutral"
    sad = "sad"
    hungry = "hungry"
    sick = "sick"
    critical = "critical"


class AlertType(str, Enum):
    """Tipe alert real-time — sebelumnya pakai string bebas (rawan typo).

    Sekarang pakai ENUM agar type-safe dan IDE bisa autocomplete.
    """
    food_warning = "food_warning"
    compliance_violation = "compliance_violation"
    level_up = "level_up"
    medication_reminder = "medication_reminder"


# ──────────────────────────────────────────────
# Helper: Compute Pet Status
# ──────────────────────────────────────────────

def compute_pet_status(happiness: int, hunger: int) -> PetStatus:
    """Hitung status pet dari nilai happiness dan hunger.

    SEMANTIK HUNGER (updated 2026-08-10):
      hunger = level kenyang (0 = lapar sekali, 100 = kenyang penuh)
      Jadi hunger < 30 berarti "sedikit kenyang" = pet lapar.

    Priority order (tertinggi dulu):
      1. critical  — happiness < 10 ATAU hunger < 10
      2. sick      — happiness < 20 DAN hunger < 20
      3. hungry    — hunger < 30  (sedikit kenyang = lapar)
      4. sad       — happiness < 40
      5. happy     — happiness >= 70 DAN hunger >= 70
      6. neutral   — default

    Fungsi ini harus selalu sinkron dengan SQL function
    compute_pet_status() di database (migration 001).
    """
    if happiness < 10 or hunger < 10:
        return PetStatus.critical
    if happiness < 20 and hunger < 20:
        return PetStatus.sick
    if hunger < 30:
        return PetStatus.hungry
    if happiness < 40:
        return PetStatus.sad
    if happiness >= 70 and hunger >= 70:
        return PetStatus.happy
    return PetStatus.neutral


# ──────────────────────────────────────────────
# 1. User
# ──────────────────────────────────────────────

class UserBase(BaseModel):
    email: str = Field(..., max_length=255)
    full_name: str = Field(..., max_length=255)
    role: UserRole = UserRole.child
    parent_id: Optional[UUID] = None
    doctor_id: Optional[UUID] = None
    avatar_url: Optional[str] = None
    is_active: bool = True
    # Field baru (migration 006): profil anak
    birth_date: Optional[date] = None
    gender: Optional[Gender] = None


class UserCreate(UserBase):
    password_hash: str


class UserUpdate(BaseModel):
    """Model untuk update data user.

    Hanya field yang boleh diubah setelah registrasi.
    Catatan: full_name (bukan name) sesuai kolom di database.
    """
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = None
    birth_date: Optional[date] = None
    gender: Optional[Gender] = None


class User(UserBase):
    id: UUID
    password_hash: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserPublic(BaseModel):
    """Public-facing user model — password hash tidak di-expose."""
    id: UUID
    email: str
    full_name: str
    role: UserRole
    parent_id: Optional[UUID] = None
    doctor_id: Optional[UUID] = None
    avatar_url: Optional[str] = None
    is_active: bool
    birth_date: Optional[date] = None
    gender: Optional[Gender] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# 2. Clinical Parameters
# ──────────────────────────────────────────────

class ClinicalParameterBase(BaseModel):
    child_id: UUID
    recorded_by: UUID
    height_cm: float = Field(..., ge=20, le=250)
    weight_kg: float = Field(..., ge=1, le=300)
    head_circumference_cm: Optional[float] = Field(None, ge=20, le=80)
    allergies: list[str] = Field(default_factory=list)
    medical_conditions: list[str] = Field(default_factory=list)
    notes: Optional[str] = None
    # Field baru (migration 006): tipe diabetes + max sugar
    diabetes_type: DiabetesType = DiabetesType.type1
    max_sugar_intake_g: Optional[float] = None
    # target_daily_calories & target_daily_carbs DIHITUNG OTOMATIS
    # oleh ClinicalService menggunakan WHO Pediatric formula.
    # Dokter tetap bisa override via PATCH /clinical/{child_id}.
    target_daily_calories: Optional[int] = None
    target_daily_carbs: Optional[float] = None


class ClinicalParameterCreate(ClinicalParameterBase):
    """Saat create, target_daily_calories & carbs boleh dikosongkan.
    ClinicalService akan menghitung otomatis dari BB, TB, usia, gender.
    max_sugar_intake_g jika tidak diisi, sistem berikan rekomendasi
    berdasarkan diabetes_type.
    """
    pass


class ClinicalParameterUpdate(BaseModel):
    """Dokter bisa update semua field, termasuk override kalori target."""
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    head_circumference_cm: Optional[float] = None
    allergies: Optional[list[str]] = None
    medical_conditions: Optional[list[str]] = None
    notes: Optional[str] = None
    diabetes_type: Optional[DiabetesType] = None
    max_sugar_intake_g: Optional[float] = None
    target_daily_calories: Optional[int] = None
    target_daily_carbs: Optional[float] = None


class ClinicalParameter(ClinicalParameterBase):
    id: UUID
    bmi: Optional[float] = None
    recorded_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# 3. Custom Meal Schedule
# ──────────────────────────────────────────────

class CustomMealScheduleBase(BaseModel):
    child_id: UUID
    created_by: UUID
    meal_type: MealType
    day_of_week: int = Field(..., ge=0, le=6,
                             description="0=Senin, 6=Minggu (ISO weekday)")
    meal_name: str = Field(..., max_length=255)
    description: Optional[str] = None
    calories: Optional[int] = None
    portion_size: Optional[str] = None
    is_active: bool = True
    start_date: date = Field(default_factory=date.today)
    end_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None


class CustomMealScheduleCreate(CustomMealScheduleBase):
    pass


class CustomMealScheduleUpdate(BaseModel):
    meal_type: Optional[MealType] = None
    day_of_week: Optional[int] = None
    meal_name: Optional[str] = None
    description: Optional[str] = None
    calories: Optional[int] = None
    portion_size: Optional[str] = None
    is_active: Optional[bool] = None
    end_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None


class CustomMealSchedule(CustomMealScheduleBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    # last_penalty_date dikelola internal oleh compliance_worker,
    # tidak perlu diekspose ke API response.

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# 4. Virtual Pet
# ──────────────────────────────────────────────

class VirtualPetBase(BaseModel):
    child_id: UUID
    pet_name: str = Field(..., max_length=100)
    # pet_type sekarang pakai PetType enum (sebelumnya str bebas)
    pet_type: PetType = PetType.dog
    level: int = Field(default=1, ge=1)
    experience_points: int = Field(default=0, ge=0)
    happiness: int = Field(default=100, ge=0, le=100)
    # hunger semantik: TINGGI = KENYANG, RENDAH = LAPAR
    # Default 100 = pet lahir dalam keadaan kenyang penuh.
    hunger: int = Field(default=100, ge=0, le=100)
    is_active: bool = True


class VirtualPetCreate(BaseModel):
    """Saat membuat pet baru, hanya perlu nama dan tipe.
    Nilai happiness & hunger diset default 100/100 oleh sistem.
    Dokter bisa adjust via PATCH /pets/{pet_id} kapan saja.
    """
    child_id: UUID
    pet_name: str = Field(..., max_length=100)
    pet_type: PetType = PetType.dog


class VirtualPetUpdate(BaseModel):
    """Update nama, tipe, atau stats pet.
    Dokter bisa gunakan ini untuk adjust happiness/hunger awal.
    """
    pet_name: Optional[str] = None
    pet_type: Optional[PetType] = None
    level: Optional[int] = None
    experience_points: Optional[int] = None
    happiness: Optional[int] = Field(None, ge=0, le=100)
    hunger: Optional[int] = Field(None, ge=0, le=100)
    is_active: Optional[bool] = None


class VirtualPet(VirtualPetBase):
    id: UUID
    current_status: PetStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# 5. Food Log
# ──────────────────────────────────────────────

class FoodLogBase(BaseModel):
    child_id: UUID
    logged_by: UUID
    meal_schedule_id: Optional[UUID] = None
    meal_type: MealType
    food_name: str = Field(..., max_length=255)
    portion_size: Optional[str] = None
    calories: Optional[int] = None
    photo_url: Optional[str] = None
    is_healthy: bool = True
    notes: Optional[str] = None
    # Fix: datetime.utcnow() deprecated sejak Python 3.12
    # Ganti ke datetime.now(timezone.utc)
    consumed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class FoodLogCreate(FoodLogBase):
    pass


class FoodLogUpdate(BaseModel):
    meal_type: Optional[MealType] = None
    food_name: Optional[str] = None
    portion_size: Optional[str] = None
    calories: Optional[int] = None
    photo_url: Optional[str] = None
    notes: Optional[str] = None
    consumed_at: Optional[datetime] = None


class FoodLog(FoodLogBase):
    id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# 6. Medication Log
# ──────────────────────────────────────────────

class MedicationLogBase(BaseModel):
    child_id: UUID
    administered_by: UUID
    medication_name: str = Field(..., max_length=255)
    dosage: float = Field(..., gt=0)
    dosage_unit: str = Field(..., max_length=50)
    route: str = Field(default="oral", max_length=100)
    scheduled_time: time
    was_taken: bool = True
    notes: Optional[str] = None
    # photo_url disimpan sebagai field tersendiri (bukan di notes)
    photo_url: Optional[str] = None


class MedicationLogCreate(MedicationLogBase):
    pass


class MedicationLogUpdate(BaseModel):
    medication_name: Optional[str] = None
    dosage: Optional[float] = None
    dosage_unit: Optional[str] = None
    route: Optional[str] = None
    scheduled_time: Optional[time] = None
    was_taken: Optional[bool] = None
    notes: Optional[str] = None
    photo_url: Optional[str] = None


class MedicationLog(MedicationLogBase):
    id: UUID
    administered_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# 7. Alerts (Real-time Sync)
# ──────────────────────────────────────────────

class AlertBase(BaseModel):
    child_id: UUID
    # type sekarang pakai AlertType enum (sebelumnya str bebas = rawan typo)
    type: AlertType
    message: str
    is_read: bool = False


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    is_read: Optional[bool] = None


class AlertRead(AlertBase):
    id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# 8. Nutrition Database (Placeholder)
# ──────────────────────────────────────────────

class NutritionItem(BaseModel):
    """Model untuk tabel nutrition_database.

    Data ini digunakan oleh Gemini sebagai ground truth saat
    mengestimasi kalori dan makronutrien dari nama makanan.
    Data diisi secara bertahap dari sumber data asli.
    """
    id: Optional[UUID] = None
    food_name: str
    food_name_en: Optional[str] = None
    calories_per_100g: float
    carbs_per_100g: Optional[float] = None
    sugar_per_100g: Optional[float] = None
    protein_per_100g: Optional[float] = None
    fat_per_100g: Optional[float] = None
    fiber_per_100g: Optional[float] = None
    is_healthy: bool = True
    category: Optional[str] = None

    model_config = {"from_attributes": True}