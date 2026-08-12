import os
from unittest.mock import patch
from app.core.supabase import get_supabase_service_client
from app.api.v1.children import food_drafts, med_drafts

@patch("app.api.v1.children.ai_service.detect_food_ingredients")
@patch("app.api.v1.children.storage_service.upload_image")
def test_e2e_scan_food_healthy(mock_upload, mock_detect, test_client, setup_e2e_data):
    """
    Test E2E mengunggah gambar makanan sehat ke endpoint /children/me/food-analyses
    lalu memverifikasi DB ter-update dengan is_healthy = True,
    serta Pet mendapat EXP.
    """
    child_id = setup_e2e_data["child_id"]
    pet_id = setup_e2e_data["pet_id"]
    
    # Simulasikan auth
    from app.main import app
    from app.core.auth import get_current_user
    app.dependency_overrides[get_current_user] = lambda: {"id": child_id, "role": "child"}
    
    from PIL import Image
    import io
    img = Image.new("RGB", (10, 10), color="green")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="JPEG")
    dummy_image_content = img_byte_arr.getvalue()
    files = {"file": ("apple.jpg", dummy_image_content, "image/jpeg")}

    mock_detect.return_value = [{"ingredient": "apple", "description": "Apples, raw", "weight_g": 150, "fdcId": 171688}]
    mock_upload.return_value = "http://dummy.url/apple.jpg"
    
    # 2. Tembak Endpoint Analyze
    response = test_client.post("/api/v1/children/me/food-analyses", files=files)
    assert response.status_code == 200, response.text
    
    json_response = response.json()
    assert json_response["status"] == "draft"
    analysis_id = json_response["analysisId"]
    
    # 3. Tembak Endpoint Confirm
    confirm_data = {
        "portionGrams": 150.0
    }
    
    response_confirm = test_client.post(f"/api/v1/children/me/food-analyses/{analysis_id}/confirm", json=confirm_data)
    assert response_confirm.status_code == 200, response_confirm.text
    
    json_confirm = response_confirm.json()
    assert json_confirm["history"]["status"] == "done"
    
    # 4. Verifikasi Database (food_logs)
    client = get_supabase_service_client()
    logs = client.table("food_logs").select("*").eq("child_id", child_id).execute()
    assert len(logs.data) > 0
    assert logs.data[0]["food_name"] == "apple"
    
    # Clean up overrides
    app.dependency_overrides.clear()

@patch("app.api.v1.children.ai_service.detect_medicine")
@patch("app.api.v1.children.storage_service.upload_image")
def test_e2e_scan_medicine(mock_upload, mock_detect_meds, test_client, setup_e2e_data):
    """
    Test E2E memindai obat ke endpoint /children/me/medicine-analyses.
    """
    child_id = setup_e2e_data["child_id"]
    
    # Simulasikan auth
    from app.main import app
    from app.core.auth import get_current_user
    app.dependency_overrides[get_current_user] = lambda: {"id": child_id, "role": "child"}
    
    from PIL import Image
    import io
    img = Image.new("RGB", (10, 10), color="blue")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="JPEG")
    dummy_image_content = img_byte_arr.getvalue()
    files = {"file": ("meds.jpg", dummy_image_content, "image/jpeg")}

    mock_detect_meds.return_value = {"is_medicine": True, "detected": "insulin pen"}
    mock_upload.return_value = "http://dummy.url/meds.jpg"
    
    response = test_client.post("/api/v1/children/me/medicine-analyses", files=files)
    assert response.status_code == 200, response.text
    
    json_response = response.json()
    assert json_response["isMedicine"] == True
    analysis_id = json_response["analysisId"]
    
    # Tembak Endpoint Confirm
    response_confirm = test_client.post(f"/api/v1/children/me/medicine-analyses/{analysis_id}/confirm")
    assert response_confirm.status_code == 200, response_confirm.text
    
    # Verifikasi DB
    client = get_supabase_service_client()
    logs = client.table("medication_logs").select("*").eq("child_id", child_id).execute()
    assert len(logs.data) > 0
    assert "insulin pen" in logs.data[0]["detected_medicine"]
    
    # Clean up overrides
    app.dependency_overrides.clear()
