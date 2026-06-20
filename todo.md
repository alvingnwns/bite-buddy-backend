# BiteBuddy Backend — TODO (Master Plan)

> Referensi utama: `md/design.md`
> Rules pengerjaan: `rules.md`

---

## Fase 0 — Foundation (Project Setup)

### Fase 0.1 — Project Scaffolding
- [x] Struktur folder modular FastAPI (`app/api`, `app/core`, `app/models`, `app/services`, `app/workers`)
- [x] `app/core/config.py` — settings via `pydantic-settings`
- [x] `app/main.py` — FastAPI app dengan CORS middleware & lifespan hook
- [x] `app/api/v1/router.py` — API v1 router
- [x] `app/api/v1/health.py` — `GET /api/v1/health`
- [x] `app/models/health.py` — Pydantic model untuk health check
- [x] `requirements.txt` — dependencies
- [x] `.env.example` — template environment variables
- [x] `.gitignore`
- [x] 📝 Handout: `md/handout_database_schema.md`

### Fase 0.2 — Database Schema & Migration
- [x] `migrations/001_initial_schema.sql` — DDL untuk 6 tabel (users, clinical_parameters, custom_meal_schedules, virtual_pets, food_logs, medication_logs)
- [x] `migrations/rls_policies.md` — dokumentasi RLS policies
- [x] `app/models/database.py` — Pydantic models (Base/Create/Update/Read) untuk semua tabel
- [x] Enums: `UserRole`, `MealType`, `PetStatus`
- [x] Helper: `compute_pet_status(happiness, hunger)`

### Fase 0.3 — Supabase Client Setup
- [x] `app/core/supabase.py` — Supabase client singletons (anon + service role)
- [x] `app/core/__init__.py` — export `supabase` & `supabase_service`
- [x] `app/api/v1/health.py` — tambah `GET /api/v1/db-check`
- [x] `.env.example` — cleanup format
- [x] 📝 Handout: `md/handout_fitur_supabase_client.md`

### Fase 0.4 — Environment & Tooling
- [x] Virtual environment `bbb-venv` (Python 3.13.9)
- [x] `pyrightconfig.json` — IntelliSense configuration
- [x] `.vscode/settings.json` — IDE interpreter path
- [ ] ⚠️ Apply migration `001_initial_schema.sql` ke Supabase (manual)
- [ ] ⚠️ Isi `.env` dengan credentials Supabase (manual)
- [ ] Verifikasi koneksi via `GET /api/v1/db-check`

---

## Fase 1 — Scan Food Endpoint (Parallel Processing)

> Referensi: design.md § "Detect Food Flow"

### Fase 1.1 — Supabase Storage Service
- [x] `app/services/storage_service.py`
  - [x] Fungsi `upload_image_to_storage(file_bytes, bucket, filename)` → public URL
  - [x] Validasi file type (hanya gambar: jpg, png, webp)
  - [x] Validasi ukuran file (max 10MB)
  - [x] Generate unique filename (UUID-based)
- [x] ⚠️ Buat bucket `food-photos` di Supabase Storage (manual)

### Fase 1.2 — AI Inference Service (SegFormer)
- [x] `app/services/ai_service.py`
  - [x] Fungsi `detect_food(image_bytes)` → kirim ke Hugging Face SegFormer API
  - [x] Parse response segmentation → list food items
  - [x] Error handling: timeout, rate limit, API down
  - [x] Retry logic dengan exponential backoff

### Fase 1.3 — Multimodal Reasoning Service
- [x] `app/services/reasoning_service.py`
  - [x] Fungsi `estimate_nutrition(food_items: list)` → JSON output
  - [x] Output format: `{ "foods": [...], "total_calories": int, "total_carbs": float }`
  - [x] Lookup nutritional database / estimation logic

### Fase 1.4 — Scan Food Endpoint
- [x] `app/api/v1/scan.py`
  - [x] `POST /api/v1/scan/food` — terima foto makanan
  - [x] Implementasi `asyncio.gather` untuk parallel processing:
    - Task A: Upload gambar ke Supabase Storage
    - Task B: Kirim gambar ke SegFormer AI
  - [x] Proses hasil AI lewat reasoning service
  - [x] Simpan ke tabel `food_logs`
  - [ ] Trigger gamification logic (Fase 3 - Menyusul nanti)
  - [x] Return response dengan detail makanan & status pet
- [x] `app/api/v1/router.py` — register scan router
- [x] 📝 Handout: `md/handout_fitur_scan_food.md`

---

## Fase 2 — Scan Medicine/Insulin Endpoint

> Referensi: design.md § "Detect Medicine/Insulin Flow"

### Fase 2.1 — AI Inference Service (YOLOv8)
- [x] `app/services/ai_service.py` (extend)
  - [x] Fungsi `detect_medicine(image_bytes)` → kirim ke Hugging Face YOLOv8 API
  - [x] Parse response → detected insulin type, pen color/shape
  - [x] Error handling (sama dengan food detection)

### Fase 2.2 — Scan Medicine Endpoint
- [x] `app/api/v1/scan.py` (extend)
  - [x] `POST /api/v1/scan/medicine` — terima foto insulin pen + manual dosage input
  - [x] Upload gambar ke Supabase Storage (bucket: `medicine-photos`)
  - [x] Kirim gambar ke YOLOv8 untuk deteksi tipe insulin
  - [x] Validasi: dosage WAJIB diisi manual oleh parent (medical safety)
  - [x] Simpan ke tabel `medication_logs`
  - [x] Return response dengan detail obat yang terdeteksi
- [x] ⚠️ Buat bucket `medicine-photos` di Supabase Storage (manual)
- [x] 📝 Handout: `md/handout_fitur_scan_medicine.md`

---

## Fase 3 — Gamification & Reasoning Service

> Referensi: design.md § "Gamification Logic" & Task #3

### Fase 3.1 — Gamification Service
- [x] `app/services/gamification_service.py`
  - [x] Fungsi `evaluate_compliance(child_id, food_log_data)`:
    - Ambil `clinical_parameters` anak dari database
    - Bandingkan kalori/karbo makanan vs target medis
    - Hitung EXP reward atau penalty
  - [x] Fungsi `update_pet_status(child_id, exp_delta, happiness_delta, hunger_delta)`:
    - Update tabel `virtual_pets`
    - Hitung level up jika EXP cukup
    - Re-compute `current_status` via `compute_pet_status()`
  - [x] Fungsi `get_pet_evolution_state(level)` → visual state pet berdasarkan level
- [x] 📝 Handout: `md/handout_fitur_gamification.md`

### Fase 3.2 — Integrasi Gamification ke Scan Endpoints
- [x] `POST /api/v1/scan/food` — panggil gamification setelah food log tersimpan
- [x] `POST /api/v1/scan/medicine` — panggil gamification setelah medication log tersimpan

---

## Fase 4 — Compliance Worker (Background Job)

> Referensi: design.md § "Constant Check (Compliance Worker)"

### Fase 4.1 — Scheduler Setup
- [ ] Tambah `apscheduler` ke `requirements.txt`
- [ ] `app/workers/scheduler.py` — setup APScheduler instance
- [ ] Integrasi scheduler ke `app/main.py` lifespan (start/stop)

### Fase 4.2 — Compliance Worker Logic
- [ ] `app/workers/compliance_worker.py`
  - [ ] Fungsi `check_meal_compliance()`:
    - Query `custom_meal_schedules` yang aktif hari ini
    - Untuk setiap meal window yang sudah lewat:
      - Cek apakah ada `food_logs` di window tersebut
      - Jika TIDAK ada → apply health penalty ke `virtual_pets`
      - Flag dashboard (insert alert/notification)
  - [ ] PENTING: jangan gunakan fixed interval (24 jam)
  - [ ] Gunakan meal window schedule (breakfast 07-09, lunch 11-13, dinner 17-19, dll.)
  - [ ] Scheduling: cek setiap 15 menit (configurable)
- [ ] 📝 Handout: `md/handout_fitur_compliance_worker.md`

---

## Fase 5 — Real-time Synchronization

> Referensi: design.md § "Real-time Synchronization"

### Fase 5.1 — Supabase Realtime Configuration
- [ ] Enable Realtime pada tabel-tabel:
  - [ ] `food_logs`
  - [ ] `medication_logs`
  - [ ] `virtual_pets`
- [ ] Dokumentasikan channel subscription patterns untuk frontend

### Fase 5.2 — Backend Broadcast Service
- [ ] `app/services/realtime_service.py`
  - [ ] Fungsi `broadcast_pet_update(child_id, pet_data)` — trigger setelah pet berubah
  - [ ] Fungsi `broadcast_food_log(child_id, log_data)` — trigger setelah food log baru
  - [ ] Fungsi `broadcast_alert(child_id, alert_data)` — trigger compliance violation
- [ ] 📝 Handout: `md/handout_fitur_realtime.md`

---

## Fase 6 — API Endpoints Tambahan (CRUD)

### Fase 6.1 — User Management
- [ ] `app/api/v1/users.py`
  - [ ] `GET /api/v1/users/me` — profil user yang sedang login
  - [ ] `GET /api/v1/users/{user_id}/children` — list anak dari parent
  - [ ] `PATCH /api/v1/users/{user_id}` — update profil

### Fase 6.2 — Clinical Parameters CRUD
- [ ] `app/api/v1/clinical.py`
  - [ ] `POST /api/v1/clinical` — tambah parameter klinis baru
  - [ ] `GET /api/v1/clinical/{child_id}` — riwayat parameter klinis anak
  - [ ] `GET /api/v1/clinical/{child_id}/latest` — parameter terbaru

### Fase 6.3 — Meal Schedule CRUD
- [ ] `app/api/v1/schedules.py`
  - [ ] `POST /api/v1/schedules` — buat jadwal makan
  - [ ] `GET /api/v1/schedules/{child_id}` — jadwal makan anak
  - [ ] `PATCH /api/v1/schedules/{schedule_id}` — update jadwal
  - [ ] `DELETE /api/v1/schedules/{schedule_id}` — hapus jadwal

### Fase 6.4 — Virtual Pet Endpoints
- [ ] `app/api/v1/pets.py`
  - [ ] `POST /api/v1/pets` — buat pet baru untuk anak
  - [ ] `GET /api/v1/pets/{child_id}` — status pet anak
  - [ ] `PATCH /api/v1/pets/{pet_id}` — update pet (nama, tipe)

### Fase 6.5 — Logs & History
- [ ] `app/api/v1/logs.py`
  - [ ] `GET /api/v1/logs/food/{child_id}` — riwayat food logs
  - [ ] `GET /api/v1/logs/medication/{child_id}` — riwayat medication logs
  - [ ] Query params: `?date_from=`, `?date_to=`, `?meal_type=`, `?limit=`
- [ ] 📝 Handout: `md/handout_fitur_crud_endpoints.md`

---

## Fase 7 — Auth & Security

### Fase 7.1 — Supabase Auth Integration
- [ ] `app/core/auth.py` — dependency untuk extract & verify JWT dari Supabase Auth
- [ ] `app/api/deps.py` — `get_current_user()` dependency
- [ ] Protect semua endpoint dengan auth dependency
- [ ] Role-based access:
  - Child: hanya lihat data sendiri
  - Parent: lihat & manage data anak
  - Doctor: lihat data semua pasien yang di-assign

### Fase 7.2 — RLS Enforcement
- [ ] `migrations/002_rls_policies.sql` — apply RLS policies dari `rls_policies.md`
- [ ] Test RLS policies berjalan benar
- [ ] 📝 Handout: `md/handout_fitur_auth.md`

---

## Fase 8 — Testing & Documentation

### Fase 8.1 — Unit Tests
- [ ] Tambah `pytest`, `pytest-asyncio`, `httpx` ke requirements (dev)
- [ ] `tests/test_health.py` — test health & db-check endpoints
- [ ] `tests/test_scan.py` — test scan endpoints (mock AI)
- [ ] `tests/test_gamification.py` — test gamification logic
- [ ] `tests/test_compliance.py` — test compliance worker

### Fase 8.2 — API Documentation
- [ ] Review & polish Swagger docs (FastAPI auto-generated)
- [ ] Tambahkan deskripsi dan contoh di setiap endpoint
- [ ] 📝 Handout: `md/handout_fitur_testing.md`

---

## Rules Pengerjaan (dari `rules.md`)

1. ✅ Setiap 1 fitur selesai → buat `handout_fitur_namafitur.md`
2. ✅ Setiap mulai fitur baru → baca ulang `design.md`
3. ✅ Setiap ada error → catat di `errors.md`
4. ✅ Jelaskan code secara detail (untuk pembelajaran)
5. ✅ Belajar dari `errors.md` dan cegah terulang
6. ✅ Push ke GitHub setiap selesai 1 fitur (commit message detail, boleh dibagi beberapa commit)

---

## Progress Summary

| Fase | Nama | Status |
|------|------|--------|
| 0.1 | Project Scaffolding | ✅ Selesai |
| 0.2 | Database Schema | ✅ Selesai |
| 0.3 | Supabase Client | ✅ Selesai |
| 0.4 | Environment & Tooling | ✅ Selesai |
| 1 | Scan Food Endpoint | ✅ Selesai |
| 2 | Scan Medicine Endpoint | ✅ Selesai |
| 3 | Gamification Service | ✅ Selesai |
| 4 | Compliance Worker | ❌ Belum dimulai |
| 5 | Real-time Sync | ❌ Belum dimulai |
| 6 | CRUD Endpoints | ❌ Belum dimulai |
| 7 | Auth & Security | ❌ Belum dimulai |
| 8 | Testing & Docs | ❌ Belum dimulai |
