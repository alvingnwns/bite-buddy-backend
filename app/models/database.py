"""Pydantic models that map to the database schema tables.

These models represent the data structures stored in Supabase/PostgreSQL.
They are used for serialization, validation, and API responses.
"""

from datetime import date, datetime, time
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────

class UserRole(str, Enum):
    doctor = "doctor"
    parent = "parent"
    child = "child"


class MealType(str, Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


class PetStatus(str, Enum):
    """Status kesehatan virtual pet — computed dari happiness + hunger."""
    happy = "happy"
    neutral = "neutral"
    sad = "sad"
    hungry = "hungry"
    sick = "sick"
    critical = "critical"


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


class UserCreate(UserBase):
    password_hash: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = None


class User(UserBase):
    id: UUID
    password_hash: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserPublic(BaseModel):
    """Public-facing user model — no password hash exposed."""
    id: UUID
    email: str
    full_name: str
    role: UserRole
    parent_id: Optional[UUID] = None
    doctor_id: Optional[UUID] = None
    avatar_url: Optional[str] = None
    is_active: bool
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
    target_daily_calories: Optional[int] = None
    target_daily_carbs: Optional[float] = None
    notes: Optional[str] = None


class ClinicalParameterCreate(ClinicalParameterBase):
    pass


class ClinicalParameterUpdate(BaseModel):
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    head_circumference_cm: Optional[float] = None
    allergies: Optional[list[str]] = None
    medical_conditions: Optional[list[str]] = None
    target_daily_calories: Optional[int] = None
    target_daily_carbs: Optional[float] = None
    notes: Optional[str] = None


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
    day_of_week: int = Field(..., ge=0, le=6)
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

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# 4. Virtual Pet
# ──────────────────────────────────────────────

def compute_pet_status(happiness: int, hunger: int) -> PetStatus:
    """Compute pet health status from happiness and hunger values.

    Priority order (highest first):
      1. critical  — happiness < 10 OR hunger < 10
      2. sick      — happiness < 20 AND hunger < 20
      3. hungry    — hunger < 30
      4. sad       — happiness < 40
      5. happy     — happiness >= 70 AND hunger >= 70
      6. neutral   — default
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


class VirtualPetBase(BaseModel):
    child_id: UUID
    pet_name: str = Field(..., max_length=100)
    pet_type: str = Field(..., max_length=50)
    level: int = Field(default=1, ge=1)
    experience_points: int = Field(default=0, ge=0)
    happiness: int = Field(default=100, ge=0, le=100)
    hunger: int = Field(default=100, ge=0, le=100)
    is_active: bool = True


class VirtualPetCreate(VirtualPetBase):
    pass


class VirtualPetUpdate(BaseModel):
    pet_name: Optional[str] = None
    level: Optional[int] = None
    experience_points: Optional[int] = None
    happiness: Optional[int] = None
    hunger: Optional[int] = None
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
    consumed_at: datetime = Field(default_factory=datetime.utcnow)


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
    type: str = Field(..., max_length=50)
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