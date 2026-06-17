# Handout: Database Schema

## Apa yang Telah Selesai (Fase 0.1 — Project Setup)

- Struktur folder FastAPI modular:
  - `app/api/v1/` — routing API versi 1
  - `app/core/` — konfigurasi aplikasi
  - `app/models/` — Pydantic schemas
  - `app/services/` — siap untuk business logic
  - `app/workers/` — siap untuk background worker
- `app/core/config.py` — settings via `pydantic-settings` (Supabase, Hugging Face, CORS)
- `app/main.py` — FastAPI app dengan CORS middleware dan lifespan hook
- Endpoint health check:
  - `GET /health` — health check root
  - `GET /api/v1/health` — health check dengan info app name & version
- `requirements.txt` — FastAPI, Uvicorn, Supabase client, httpx, dll.
- `.env.example` — template environment variables
- `.gitignore` — Python artifacts + `.env`

### Cara Menjalankan

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Swagger docs: http://127.0.0.1:8000/docs

---

## Apa yang Harus Dilakukan di Sesi Berikutnya (Fase 0.2 — Database Schema)

1. Buat `migrations/001_initial_schema.sql` dengan tabel:
   - `users` (role: doctor, parent, child)
   - `clinical_parameters`
   - `custom_meal_schedules`
   - `virtual_pets`
   - `food_logs`
   - `medication_logs`
2. Dokumentasikan Row Level Security (RLS) policies untuk setiap tabel
3. Apply migration ke project Supabase (buat project di dashboard jika belum ada)
4. Setelah selesai, buat `handout_supabase_client.md`
