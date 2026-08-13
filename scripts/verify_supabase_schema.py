"""Read-only verification for database objects required by migrations 001-016."""

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.core.supabase import get_supabase_service_client


TABLE_COLUMNS = {
    "users": "id,username,patient_code,doctor_code,address,birth_date,gender",
    "clinical_parameters": "id,target_daily_calories,target_daily_carbs,diabetes_type,max_sugar_intake_g",
    "custom_meal_schedules": "id,start_time,end_time,last_penalty_date,schedule_type",
    "virtual_pets": "id,pet_type,level,experience_points,happiness,hunger",
    "food_logs": "id,analysis_id,portion_grams,nutrition,is_healthy",
    "medication_logs": "id,analysis_id,photo_url,is_medicine,status",
    "nutrition_database": "id,food_name,calories_per_100g",
    "alerts": "id,sender_type,title,recipient_user_id,doctor_notification_id",
    "activity_logs": "id,wib_month,created_at",
    "analysis_drafts": "id,analysis_type,status,confirmed_history_id",
    "schedule_occurrences": "id,schedule_id,occurrence_date,status",
    "patient_invitations": "id,doctor_id,patient_code,status",
    "doctor_patient_profiles": "doctor_id,patient_id",
    "blood_glucose_records": "id,recorded_by,patient_id,value_mg_dl",
    "doctor_appointments": "id,doctor_id,patient_id,starts_at,status",
    "doctor_diagnoses": "id,doctor_id,patient_id",
    "doctor_notifications": "id,doctor_id,patient_id,recipient_user_id,idempotency_key",
}

RPC_NAMES = {
    "claim_patient_invitation",
    "doctor_create_blood_glucose",
    "doctor_create_appointment",
    "doctor_create_diagnosis",
    "doctor_create_notification",
    "confirm_child_analysis",
}


def main() -> int:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        print("FAIL: Supabase credentials are not configured.")
        return 1

    client = get_supabase_service_client()
    failures: list[str] = []
    for table, columns in TABLE_COLUMNS.items():
        try:
            client.table(table).select(columns).limit(1).execute()
        except Exception as exc:
            failures.append(f"table {table}: {type(exc).__name__}")

    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Accept": "application/openapi+json",
    }
    try:
        response = httpx.get(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/",
            headers=headers,
            timeout=20,
        )
        response.raise_for_status()
        paths = response.json().get("paths", {})
        for name in RPC_NAMES:
            if f"/rpc/{name}" not in paths:
                failures.append(f"rpc {name}: missing")
    except Exception as exc:
        failures.append(f"PostgREST OpenAPI: {type(exc).__name__}")

    if failures:
        print("FAIL: migration verification found missing objects:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(
        f"PASS: {len(TABLE_COLUMNS)} tables/column groups and "
        f"{len(RPC_NAMES)} RPCs for migrations 001-016 are available."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
