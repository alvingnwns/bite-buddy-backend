# Handout: Supabase Client Setup

## Apa yang Telah Dikerjakan (Fase 0.3 — Supabase Client)

### 1. `app/core/supabase.py` — **[NEW]**

Module baru yang menyediakan dua Supabase client singleton:

- `supabase` — menggunakan `SUPABASE_ANON_KEY`, tunduk pada Row Level Security (RLS).
- `supabase_service` — menggunakan `SUPABASE_SERVICE_ROLE_KEY`, bypass RLS untuk operasi backend-to-backend.

Kedua instance di-cache dengan `@lru_cache` sehingga hanya dibuat satu kali selama lifetime proses.

```python
from app.core.supabase import supabase, supabase_service
```

### 2. `app/core/__init__.py` — **[MODIFIED]**

Menambahkan export `supabase` dan `supabase_service` ke package `app.core`, sehingga module lain bisa import langsung:

```python
from app.core import supabase, supabase_service
```

### 3. `app/core/config.py` — **[MODIFIED]**

Menambahkan section comment headers (`── Supabase ──` dan `── Hugging Face ──`) untuk mengelompokkan konfigurasi secara visual. Semua field sudah ada sebelumnya — tidak ada perubahan fungsional.

### 4. `app/api/v1/health.py` — **[MODIFIED]**

Menambahkan endpoint baru:

- `GET /api/v1/db-check` — memverifikasi koneksi ke Supabase database dengan mengquery tabel `users`.

Response sukses:
```json
{
    "status": "ok",
    "db_connected": true,
    "user_count": 0
}
```

Response error:
```json
{
    "status": "error",
    "db_connected": false,
    "error": "detail pesan error"
}
```

Juga memindahkan tag `["health"]` ke level router (bukan per-endpoint) agar konsisten.

### 5. `.env.example` — **[MODIFIED]**

Membersihkan template: menghapus placeholder value (`your-anon-key`, dll.) dan menggantinya dengan value kosong agar user tahu field ini WAJIB diisi sendiri.

---

## Struktur File Setelah Fase Ini

```
bite-buddy-backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py
│   │       └── health.py          ← MODIFIED (+/db-check)
│   ├── core/
│   │   ├── __init__.py            ← MODIFIED (+supabase exports)
│   │   ├── config.py              ← MODIFIED (+section comments)
│   │   └── supabase.py            ← NEW
│   ├── models/
│   │   ├── __init__.py
│   │   ├── health.py
│   │   └── database.py
│   ├── services/
│   │   └── __init__.py
│   └── workers/
│       └── __init__.py
├── migrations/
│   ├── 001_initial_schema.sql
│   └── rls_policies.md
├── md/
│   ├── design.md
│   ├── handout_database_schema.md
│   ├── handout_supabase_client.md
│   └── handout_fitur_supabase_client.md  ← THIS FILE
├── .env.example                   ← MODIFIED
├── .gitignore
└── requirements.txt
```

---

## Prasyarat Sebelum Lanjut (Aksi Manual User)

> ⚠️ Langkah-langkah ini HARUS dilakukan secara manual sebelum melanjutkan ke fase berikutnya:

1. **Buat project Supabase** di [supabase.com/dashboard](https://supabase.com/dashboard)
2. **Jalankan migration** `001_initial_schema.sql` di SQL Editor Supabase
3. **Isi file `.env`** dengan credentials dari Supabase Dashboard:
   - `SUPABASE_URL` → Project Settings → API → Project URL
   - `SUPABASE_ANON_KEY` → Project Settings → API → anon public
   - `SUPABASE_SERVICE_ROLE_KEY` → Project Settings → API → service_role
4. **Verifikasi koneksi** dengan menjalankan server dan mengakses `GET /api/v1/db-check`

---

## Apa yang Harus Dikerjakan di Sesi Berikutnya

Berdasarkan `design.md`, fase-fase selanjutnya yang perlu dikerjakan:

### Fase 1 — Scan Food Endpoint
- Buat `app/api/v1/scan.py` dengan endpoint `POST /api/v1/scan/food`
- Implementasikan parallel processing menggunakan `asyncio.gather`:
  - Task A: Upload gambar ke Supabase Storage
  - Task B: Kirim gambar ke SegFormer AI (Hugging Face API)
- Buat service untuk multimodal reasoning (estimasi kalori & karbohidrat)

### Fase 2 — Scan Medicine Endpoint
- Tambahkan endpoint `POST /api/v1/scan/medicine` di `scan.py`
- Integrasi dengan YOLOv8 untuk deteksi insulin pen
- Input manual dosage dari parent

### Fase 3 — Gamification Service
- Buat `app/services/gamification_service.py`
- Logic: bandingkan output AI JSON dengan `clinical_parameters`
- Update `virtual_pets` (EXP, happiness, hunger)
- Trigger Supabase real-time broadcast

### Fase 4 — Compliance Worker
- Buat `app/workers/compliance_worker.py`
- Query `custom_meal_schedules` untuk cek meal window yang terlewat
- Apply health penalty ke virtual pet jika tidak ada food log
- Flag dashboard untuk early warning

### Fase 5 — Real-time Synchronization
- Konfigurasi Supabase Real-time pada semua tabel yang relevan
- Pastikan semua mutasi database trigger update ke Web Dashboard

---

## Cara Menjalankan & Verifikasi

```bash
# Aktifkan virtual environment
.venv\Scripts\activate

# Jalankan server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Test health check
# GET http://127.0.0.1:8000/api/v1/health

# Test koneksi database (setelah .env diisi)
# GET http://127.0.0.1:8000/api/v1/db-check
```

Swagger docs: http://127.0.0.1:8000/docs

---

## Troubleshooting

| Masalah | Solusi |
|---|---|
| `ImportError: cannot import name 'supabase'` | Pastikan `supabase>=2.10.0` terinstall: `pip install supabase` |
| Connection refused / timeout | Pastikan `SUPABASE_URL` benar dan project aktif |
| 401 Unauthorized | Periksa `SUPABASE_ANON_KEY` — pastikan bukan `service_role_key` |
| `ValidationError` saat startup | Pastikan file `.env` ada dan semua field terisi |
| `/db-check` return error 406 | Pastikan migration `001_initial_schema.sql` sudah dijalankan |
