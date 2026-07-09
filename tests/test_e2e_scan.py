import os
from app.core.supabase import get_supabase_service_client

def test_e2e_scan_food_healthy(test_client, setup_e2e_data):
    """
    Test E2E mengunggah gambar makanan sehat ke endpoint /scan/food
    lalu memverifikasi DB ter-update dengan is_healthy = True,
    serta Pet mendapat EXP.
    """
    child_id = setup_e2e_data["child_id"]
    user_id = setup_e2e_data["user_id"]
    pet_id = setup_e2e_data["pet_id"]
    
    # 1. Siapkan file dummy untuk simulasi upload
    # Karena kita menggunakan USE_LOCAL_AI=true (dummy AI return apple/salad), 
    # file apa saja bisa dipakai asalkan berwujud bytes image yang valid.
    from PIL import Image
    import io
    img = Image.new("RGB", (10, 10), color="green")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="JPEG")
    dummy_image_content = img_byte_arr.getvalue()
    files = {"file": ("apple.jpg", dummy_image_content, "image/jpeg")}
    data = {
        "child_id": child_id,
        "logged_by": user_id,
        "meal_type": "breakfast",
        "notes": "E2E Test Food"
    }

    # 2. Tembak Endpoint
    response = test_client.post("/api/v1/scan/food", data=data, files=files)
    assert response.status_code == 200, response.text
    
    json_response = response.json()
    assert json_response["status"] == "success"
    assert json_response["data"]["is_healthy"] == True
    
    # 3. Verifikasi Database (food_logs)
    client = get_supabase_service_client()
    logs = client.table("food_logs").select("*").eq("child_id", child_id).execute()
    assert len(logs.data) > 0
    assert logs.data[0]["is_healthy"] == True
    assert "E2E Test Food" in logs.data[0]["notes"]
    
    # 4. Verifikasi Database (virtual_pets) mendapat EXP
    pets = client.table("virtual_pets").select("*").eq("id", pet_id).execute()
    assert pets.data[0]["experience_points"] > 50  # 50 adalah nilai awal di conftest

def test_e2e_scan_medicine(test_client, setup_e2e_data):
    """
    Test E2E memindai obat ke endpoint /scan/medicine.
    """
    child_id = setup_e2e_data["child_id"]
    user_id = setup_e2e_data["user_id"]
    
    from PIL import Image
    import io
    img = Image.new("RGB", (10, 10), color="blue")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="JPEG")
    dummy_image_content = img_byte_arr.getvalue()
    files = {"file": ("meds.jpg", dummy_image_content, "image/jpeg")}
    data = {
        "child_id": child_id,
        "administered_by": user_id,
        "dosage": 5.0,
        "dosage_unit": "IU",
        "route": "subcutaneous",
        "notes": "E2E Test Meds"
    }

    response = test_client.post("/api/v1/scan/medicine", data=data, files=files)
    assert response.status_code == 200, response.text
    
    # Verifikasi DB
    client = get_supabase_service_client()
    logs = client.table("medication_logs").select("*").eq("child_id", child_id).execute()
    assert len(logs.data) > 0
    assert logs.data[0]["dosage"] == 5.0
    assert "E2E Test Meds" in logs.data[0]["notes"]
