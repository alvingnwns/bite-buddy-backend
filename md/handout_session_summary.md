# BiteBuddy Backend — Session Handout

> **Dibuat**: 9 Agustus 2026  
> **Tujuan**: Ringkasan lengkap project BiteBuddy backend dari sisi teknis — untuk onboarding ulang, knowledge transfer, atau referensi cepat antar sesi.

---

## 1. Deskripsi Project

**BiteBuddy** adalah aplikasi perawatan berkelanjutan (continuous-care) berbasis gamifikasi untuk **anak penderita Diabetes Mellitus**. Project ini dibuat untuk kompetisi **GEMASTIK** kategori Pengembangan Perangkat Lunak.

### Konsep Inti

Anak-anak dengan T1DM harus disiplin makan dan minum obat/insulin setiap hari. BiteBuddy membuat kewajiban ini terasa menyenangkan dengan konsep **Virtual Pet** (mirip Pou) — kesehatan hewan peliharaan virtual mencerminkan kepatuhan medis anak:
- Anak foto makanan → AI analisis → Pet dapat EXP dan kebahagiaan
- Anak foto obat insulin → Pet dapat bonus besar
- Anak melewatkan makan/obat → Pet jadi sedih atau lapar

### Platform

| Platform | Pengguna | Fungsi |
|----------|----------|--------|
| **Mobile App** (Expo/React Native) | Anak & Orang Tua | Scan foto makanan/obat, lihat Virtual Pet |
| **Web Dashboard** (Next.js) | Dokter & Orang Tua | Monitoring real-time, early warning, data klinis |
| **Backend** (FastAPI/Python) | — | API, AI orchestration, gamifikasi, background jobs |

---

## 2. Tech Stack

| Layer | Teknologi | Keterangan |
|-------|-----------|------------|
| **Backend Framework** | FastAPI (Python 3.13.9) | Async, auto-docs, type-safe |
| **Database** | Supabase (PostgreSQL) | Cloud-hosted, RLS support |
| **Auth** | Supabase Auth (Fase 7 — belum) | JWT-based, role-based |
| **Storage** | Supabase Storage | Bucket `food-photos` & `medicine-photos` |
| **Real-time** | Supabase Postgres Changes | Push via WebSocket ke frontend |
| **AI — Food** | Hugging Face: `nateraw/food` (ViT image-classification) | Detect nama makanan dari foto |
| **AI — Medicine** | Hugging Face: `openai/clip-vit-base-patch32` (zero-shot) | Detect jenis insulin/obat |
| **Local AI Mode** | PyTorch + `transformers` pipeline | Mode offline dengan GPU RTX 4060 |
| **Background Jobs** | APScheduler (AsyncIOScheduler) | Compliance worker setiap 1 menit (demo) |
| **Settings** | pydantic-settings | Baca dari `.env` file |
| **Testing** | pytest + pytest-asyncio | Unit test + E2E test |
| **Virtual Env** | `bbb-venv` (di dalam project folder) | Python 3.13.9 |

---

## 3. Struktur Folder

```
bite-buddy-backend/
├── app/
│   ├── api/v1/
│   │   ├── router.py        # Registrasi semua sub-router
│   │   ├── health.py        # GET /health, GET /db-check
│   │   ├── scan.py          # POST /scan/food, POST /scan/medicine
│   │   ├── users.py         # CRUD users
│   │   ├── clinical.py      # CRUD clinical parameters
│   │   ├── schedules.py     # CRUD meal schedules
│   │   ├── pets.py          # CRUD virtual pets
│   │   └── logs.py          # GET food/medication logs
│   ├── core/
│   │   ├── config.py        # Settings (pydantic-settings)
│   │   └── supabase.py      # Supabase client singletons (lazy-init)
│   ├── models/
│   │   ├── database.py      # Semua Pydantic models (Base/Create/Update/Read)
│   │   └── health.py        # Health check model
│   ├── services/
│   │   ├── ai_service.py          # HF API calls + retry logic + local AI mode
│   │   ├── storage_service.py     # Upload gambar ke Supabase Storage
│   │   ├── reasoning_service.py   # Estimasi kalori & karbo dari nama makanan
│   │   ├── gamification_service.py # EXP, happiness, hunger, level-up logic
│   │   ├── log_service.py         # INSERT food_logs & medication_logs
│   │   └── alert_service.py       # INSERT alerts → trigger Postgres Changes
│   ├── workers/
│   │   ├── scheduler.py           # APScheduler setup & start/stop
│   │   └── compliance_worker.py   # check_daily_compliance() + clean_old_alerts()
│   └── main.py                    # FastAPI app, CORS, lifespan hook
├── migrations/
│   ├── 001_initial_schema.sql     # DDL: 6 tabel utama
│   ├── 003_spec_fixes.sql         # ALTER: tambah start_time/end_time & target calories
│   ├── 004_food_health_status.sql
│   ├── 005_alerts_table.sql       # Tabel alerts untuk real-time notifications
│   └── rls_policies.md            # Dokumentasi RLS (belum diimplementasi di code)
├── tests/
│   ├── conftest.py                # Session fixture: insert dummy data ke Supabase (no teardown)
│   ├── test_reasoning.py          # Unit: estimasi nutrisi
│   ├── test_gamification.py       # Unit: evaluasi kepatuhan makanan
│   ├── test_api_crud.py           # Unit: CRUD endpoints (mock Supabase)
│   ├── test_e2e_health.py         # E2E: koneksi DB live
│   ├── test_e2e_scan.py           # E2E: upload foto + AI + DB + gamifikasi
│   └── test_e2e_compliance.py     # E2E: penalty system
├── md/
│   ├── design.md                  # System design document (referensi utama)
│   └── handout_*.md               # Handout per fitur
├── .env                           # Credentials (gitignored)
├── requirements.txt               # Dependencies
├── todo.md                        # Master task list + progress tracker
└── errors.md                      # Log semua error yang pernah terjadi
```

---

## 4. Database Schema (7 tabel)

| Tabel | Fungsi | Kolom Penting |
|-------|--------|---------------|
| `users` | Semua pengguna (dokter, orang tua, anak) | `id`, `email`, `role` (enum), `parent_id`, `doctor_id` |
| `clinical_parameters` | Data klinis anak (berat, tinggi, target kalori) | `child_id`, `height_cm`, `weight_kg`, `target_daily_calories`, `target_daily_carbs` |
| `custom_meal_schedules` | Jadwal makan per anak | `child_id`, `meal_type`, `day_of_week`, `start_time`, `end_time`, `is_active` |
| `virtual_pets` | Status hewan peliharaan virtual | `child_id`, `pet_name`, `level`, `experience_points`, `happiness`, `hunger`, `current_status` |
| `food_logs` | Riwayat log makanan dari scan | `child_id`, `meal_type`, `food_name`, `calories`, `photo_url`, `is_healthy`, `consumed_at` |
| `medication_logs` | Riwayat log obat/insulin dari scan | `child_id`, `medication_name`, `dosage`, `dosage_unit`, `route`, `was_taken` |
| `alerts` | Notifikasi real-time ke dashboard | `child_id`, `type`, `message`, `is_read` |

**Supabase Info:**
- URL: `https://anrwnglqqosbkxwiktid.supabase.co`
- Realtime enabled: `food_logs`, `medication_logs`, `virtual_pets`, `alerts`
- Storage buckets: `food-photos`, `medicine-photos` (keduanya public)

---

## 5. Fitur yang Sudah Terimplementasi (Fase 0–6)

### Fase 0 — Foundation ✅
- Project setup FastAPI modular
- Supabase client singletons dengan **lazy initialization**
- `GET /api/v1/health` + `GET /api/v1/db-check`

### Fase 1 — Scan Food ✅
**Endpoint**: `POST /api/v1/scan/food`
- **Parallel processing** via `asyncio.gather`: upload Storage + call AI
- Reasoning Service: estimasi kalori & karbohidrat dari nama makanan
- Simpan ke `food_logs` → lanjut gamifikasi

### Fase 2 — Scan Medicine ✅
**Endpoint**: `POST /api/v1/scan/medicine`
- CLIP zero-shot: detect jenis obat (insulin pen / syringe / pill)
- Dosis wajib diisi manual (medical safety — AI tidak tebak dosis)
- Simpan ke `medication_logs` → lanjut gamifikasi

### Fase 3 — Gamification Service ✅
`evaluate_food_compliance()` — 3 jalur penilaian:
- ✅ Sehat + kalori wajar → +15 EXP, +15 Happiness, +30 Hunger
- ⚠️ Sehat tapi berlebih → +5 EXP, -5 Happiness, +20 Hunger
- ❌ Junk food → +0 EXP, -20 Happiness + create alert

`PetStatus` logic (`compute_pet_status(happiness, hunger)`):

| Status | Kondisi |
|--------|---------|
| `critical` | happiness < 10 ATAU hunger < 10 |
| `sick` | happiness < 20 DAN hunger < 20 |
| `hungry` | hunger < 30 |
| `sad` | happiness < 40 |
| `happy` | happiness ≥ 70 DAN hunger ≥ 70 |
| `neutral` | default |

### Fase 4 — Compliance Worker ✅
`check_daily_compliance()` (setiap 1 menit, mode demo):
1. Tidak ada `medication_logs` hari ini → −10 happiness + alert
2. Jadwal makan lewat tanpa `food_logs` → −15 happiness, +30 hunger + alert
`clean_old_alerts()` (tiap 1 jam): hapus alerts > 7 hari

### Fase 5 — Real-time Alerts ✅
- Backend hanya `INSERT INTO alerts` → Supabase Postgres Changes broadcast otomatis
- Tidak ada WebSocket custom di backend
- Frontend subscribe: `supabase.channel("alerts").on("postgres_changes", ...)`

### Fase 6 — CRUD Endpoints ✅
| Group | Endpoints |
|-------|-----------|
| Users | `GET /me`, `GET /{id}/children`, `PATCH /{id}` |
| Clinical | `POST /`, `GET /{child_id}`, `GET /{child_id}/latest` |
| Schedules | `POST /`, `GET /{child_id}`, `PATCH /{id}`, `DELETE /{id}` |
| Pets | `POST /`, `GET /{child_id}`, `PATCH /{id}` |
| Logs | `GET /food/{child_id}`, `GET /medication/{child_id}` |

---

## 6. Fitur yang Belum Terimplementasi

### Fase 7 — Auth & Security ❌ (NEXT)
- `app/core/auth.py` — verify JWT dari Supabase Auth
- Replace mock `get_current_user()` di `app/api/deps.py`
- Role-based access: child / parent / doctor
- `migrations/002_rls_policies.sql` — apply RLS

### Fase 8 — Testing & Documentation ❌
- Unit test lebih lengkap (pets, auth)
- API documentation polish

### Known Gaps dari Code Review
- Filter query params di `/logs/*`: `?date_from=`, `?date_to=`, `?meal_type=` belum ada
- `datetime.utcnow()` di `database.py:252` masih deprecated
- `StorageService.__init__` eager client init (inkonsisten dengan lazy pattern)
- Duplicated error handling block di 12+ endpoint functions

---

## 7. Riwayat Error Lengkap

| Tanggal | Error | Status | Penyebab | Fix |
|---------|-------|--------|----------|-----|
| 2026-06-20 | `InterpreterHandleError` (venv di OneDrive) | ✅ | OneDrive lock binary files saat sync | Pindahkan venv ke `bbb-venv` di project folder |
| 2026-06-20 | `InterpreterHandleError` (Anaconda conflict) | ✅ | Sistem pakai Anaconda Python | Venv jalan normal di terminal (bukan issue code) |
| 2026-07-13 | `NullByteCorruption` di `requirements.txt` | ✅ | File tersimpan UTF-16 + UTF-8 mix | Tulis ulang dengan encoding UTF-8 murni |
| 2026-07-13 | `DeprecationWarning` (starlette → httpx2) | ⚠️ | Library terbaru minta migrasi | Tunggu upgrade dependency |
| 2026-07-13 | `DeprecationWarning` (supabase-py) | ⚠️ | Warning internal library | Akan hilang saat upgrade |
| 2026-07-13 | `DeprecationWarning` (`datetime.utcnow`) | ⚠️ | Python 3.12+ deprecated | Ganti ke `datetime.now(timezone.utc)` — belum difix |
| 2026-07-20 | `getaddrinfo failed` (E2E DNS error) | ✅ Identified | Supabase auto-pause setelah 7 hari | Resume project di Supabase Dashboard |

---

## 8. Hasil Testing Terakhir (20 Juli 2026)

| Suite | Hasil | Waktu | Catatan |
|-------|-------|-------|---------|
| Unit tests (10 test) | ✅ 10/10 PASSED | 0.40s | Tidak butuh koneksi internet |
| E2E tests (4 test) | ❌ 0/4 FAILED | 1.70s | Supabase paused (bukan error code) |

**Strategi E2E**: No-teardown — data dummy dibiarkan di database setelah test selesai.

---

## 9. Keputusan Desain Penting (ADR)

| Keputusan | Pilihan | Alasan |
|-----------|---------|--------|
| Direct sync vs Event-driven | **Direct sync** | Untuk kompetisi GEMASTIK, simplicity > scalability. UX lebih baik (response instan). |
| WebSocket backend vs DB-driven realtime | **DB-driven (Supabase Postgres Changes)** | Backend tidak maintain WebSocket, Supabase handle scaling & reconnection |
| Eager init vs Lazy init Supabase client | **Lazy init** | Mencegah crash saat startup jika `.env` belum diisi |
| Online AI vs Local AI | **Keduanya** (toggle via `USE_LOCAL_AI`) | Offline tetap bisa demo dengan GPU lokal |

---

## 10. Git History Ringkasan

| Commit | Pesan |
|--------|-------|
| `37e4452` | Created python file for CRUD test |
| `584fe19` | feat(fase-5): implement database-driven realtime alerts |
| `81fa32f` | feat(fase-4): evaluate healthy food and E2E testing |
| `69727a5` | refactor(fase-1-to-4): fix spec issues and refactor code smells |
| `e6ea2ac` | fix(supabase): use service role key for backend operations |
| `de24b7c` | feat(fase-4): implement apscheduler compliance worker |
| `a71b495` | feat(fase-3): implement gamification service |
| `9a87d42` | feat(fase-2): implement scan medicine endpoint |
| `99cd70f` | feat(fase-1): implement scan food endpoint with parallel AI |

**Uncommitted** (perlu segera di-commit): `errors.md`, `requirements.txt`, `todo.md`

---

## 11. Aksi Manual yang Perlu Dilakukan

> [!IMPORTANT]
> Hal-hal di luar IDE yang perlu kamu tangani:

| # | Aksi | Di Mana |
|---|------|---------|
| 1 | **Resume Supabase project** (jika sudah pause) | [supabase.com/dashboard](https://supabase.com/dashboard) → Settings → Resume |
| 2 | **Jalankan migration** `003_spec_fixes.sql` (jika belum) | Supabase → SQL Editor |
| 3 | **Jalankan migration** `004_food_health_status.sql` | Supabase → SQL Editor |
| 4 | **Jalankan migration** `005_alerts_table.sql` | Supabase → SQL Editor |
| 5 | **Enable Realtime** di tabel: `food_logs`, `medication_logs`, `virtual_pets`, `alerts` | Supabase → Table Editor → Enable Realtime |
| 6 | **Buat Storage Buckets**: `food-photos` & `medicine-photos` (public) | Supabase → Storage |

---

## 12. Next Steps (Prioritas)

1. **Resume Supabase** → jalankan ulang E2E tests → confirm 14/14 green
2. **Commit 3 file uncommitted** ke GitHub
3. **Mulai Fase 7 — Auth & Security** (buat `app/core/auth.py`, replace mock deps)
4. Fase 8 — Testing & Docs (setelah Fase 7 selesai)
