import datetime
from app.workers.compliance_worker import check_daily_compliance
from app.core.supabase import get_supabase_service_client

def test_e2e_compliance_worker(setup_e2e_data):
    """
    Test E2E untuk memicu compliance worker.
    Kita akan menyisipkan custom_meal_schedules dengan waktu mundur (end_time = 00:00:00)
    agar worker menganggap anak ini MELEWATKAN jadwal makannya.
    Lalu kita jalankan worker dan cek Happiness apakah berkurang.
    """
    child_id = setup_e2e_data["child_id"]
    pet_id = setup_e2e_data["pet_id"]
    client = get_supabase_service_client()
    
    # 1. Pastikan pet punya 100 happiness sebelum worker jalan
    client.table("virtual_pets").update({"happiness": 100}).eq("id", pet_id).execute()

    # 2. Sisipkan Custom Meal Schedule "Midnight Snack" yang berakhir jam 00:01 hari ini
    # Hari ini (0-6)
    today_dow = datetime.datetime.now(datetime.timezone.utc).date().weekday()
    client.table("custom_meal_schedules").insert({
        "child_id": child_id,
        "created_by": setup_e2e_data["user_id"],
        "day_of_week": today_dow,
        "meal_type": "snack",
        "meal_name": "Missed E2E Snack",
        "start_time": "00:00:00",
        "end_time": "00:01:00",  # Pasti terlewat karena sekarang sudah lewat dari jam segitu
        "is_active": True
    }).execute()
    
    # 3. Jalankan Worker secara sinkron
    check_daily_compliance()
    
    # 4. Verifikasi bahwa Pet terkena penalti Happiness
    pets = client.table("virtual_pets").select("*").eq("id", pet_id).execute()
    current_happiness = pets.data[0]["happiness"]
    
    # Harus di bawah 100 karena kena penalty missed meal (-15) dan missed meds (-10)
    assert current_happiness < 100
    print(f"Happiness turun menjadi {current_happiness} karena penalti.")
