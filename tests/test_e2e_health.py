def test_db_check(test_client):
    """
    Test E2E untuk endpoint /api/v1/db-check.
    Pastikan aplikasi bisa terkoneksi ke Supabase dan membaca tabel users.
    """
    response = test_client.get("/api/v1/db-check")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["success", "ok"]
    assert "user_count" in data.get("data", data)
