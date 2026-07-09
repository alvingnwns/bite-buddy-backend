# Handout: Supabase Client Setup

## Prasyarat

1. Project Supabase sudah dibuat di [supabase.com/dashboard](https://supabase.com/dashboard)
2. Migration `001_initial_schema.sql` sudah dijalankan di SQL Editor Supabase
3. Environment variables sudah diisi di file `.env`

---

## Langkah 1: Siapkan Supabase Client Module

Buat file `app/core/supabase.py` untuk mengelola koneksi ke Supabase:

```python
from functools import lru_cache

from supabase import Client, create_client

from app.core.config import settings


@lru_cache
def get_supabase_client() -> Client:
    """Membuat dan meng-cache Supabase client instance."""
    return create_client(
        supabase_url=settings.supabase_url,
        supabase_key=settings.supabase_anon_key,
    )


@lru_cache
def get_supabase_service_client() -> Client:
    """Membuat dan meng-cache Supabase service role client.
    
    Hanya digunakan untuk operasi backend-to-backend (bypass RLS).
    Jangan pernah expose service_role_key ke client-side.
    """
    return create_client(
        supabase_url=settings.supabase_url,
        supabase_key=settings.supabase_service_role_key,
    )


supabase: Client = get_supabase_client()
supabase_service: Client = get_supabase_service_client()
```

---

## Langkah 2: Update `app/core/__init__.py`

```python
from app.core.supabase import supabase, supabase_service

__all__ = ["supabase", "supabase_service"]
```

---

## Langkah 3: Tambahkan Environment Variables ke `.env`

Buka file `.env` (copy dari `.env.example`) dan isi:

```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

> **Dapatkan nilai-nilai ini dari:**
> 1. Buka [Supabase Dashboard](https://supabase.com/dashboard)
> 2. Pilih project kamu
> 3. **Project Settings** → **API**
> 4. Copy `Project URL` → `SUPABASE_URL`
> 5. Copy `anon public` → `SUPABASE_ANON_KEY`
> 6. Copy `service_role` → `SUPABASE_SERVICE_ROLE_KEY`

---

## Langkah 4: Update `.env.example`

```env
# App
APP_NAME=BiteBuddy API
APP_VERSION=0.1.0
DEBUG=false
CORS_ORIGINS=http://localhost:3000,http://localhost:8081
# Supabase
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
# Hugging Face
HF_API_TOKEN=
```

---

## Langkah 5: Update `app/core/config.py`

Pastikan `Settings` class sudah mencakup properti Supabase:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "BiteBuddy API"
    app_version: str = "0.1.0"
    debug: bool = False
    cors_origins: str = "http://localhost:3000,http://localhost:8081"

    # ── Supabase ──────────────────────────────
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # ── Hugging Face ──────────────────────────
    hf_api_token: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]
```

---

## Langkah 6: Verifikasi Koneksi

Tambahkan endpoint test di `app/api/v1/health.py` untuk memverifikasi koneksi Supabase:

```python
from fastapi import APIRouter
from supabase import Client

from app.core.supabase import supabase
from app.models.health import HealthResponse, build_health_response

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return build_health_response()


@router.get("/db-check")
async def database_check() -> dict:
    """Cek koneksi ke Supabase database."""
    try:
        result = supabase.table("users").select("count", count="exact").limit(1).execute()
        return {
            "status": "ok",
            "db_connected": True,
            "user_count": result.count,
        }
    except Exception as e:
        return {
            "status": "error",
            "db_connected": False,
            "error": str(e),
        }
```

---

## Langkah 7: Cara Apply Migration ke Supabase

Ada dua cara untuk menjalankan migration:

### Opsi A: Via Supabase SQL Editor (Manual)

1. Buka [Supabase Dashboard](https://supabase.com/dashboard)
2. Pilih project kamu
3. Klik **SQL Editor** di sidebar kiri
4. Klik **New Query**
5. Copy seluruh isi `migrations/001_initial_schema.sql`
6. Paste dan klik **Run**
7. Ulangi untuk `migrations/002_rls_policies.sql` (jika dibuat terpisah)

### Opsi B: Via Supabase CLI (Advanced)

```bash
# Install Supabase CLI
npm install -g supabase

# Login ke Supabase
supabase login

# Link ke project (perlu project reference ID dari dashboard)
supabase link --project-ref your-project-ref

# Apply migration
supabase db push
```

---

## Struktur File Setelah Setup

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
│   │       └── health.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── supabase.py          ← NEW
│   ├── models/
│   │   ├── __init__.py
│   │   ├── health.py
│   │   └── database.py          ← NEW
│   ├── services/
│   │   └── __init__.py
│   └── workers/
│       └── __init__.py
├── migrations/
│   ├── 001_initial_schema.sql    ← NEW
│   └── rls_policies.md           ← NEW
├── md/
│   ├── handout_database_schema.md
│   ├── handout_supabase_client.md ← THIS FILE
│   └── design.md
├── .env.example
├── .gitignore
└── requirements.txt
```

---

## Troubleshooting

| Masalah | Solusi |
|---|---|
| `User` object has no attribute `count` | Gunakan `.execute()` dan akses `.count` dari response |
| Connection refused / timeout | Pastikan `SUPABASE_URL` benar dan project aktif |
| 401 Unauthorized | Periksa `SUPABASE_ANON_KEY` — pastikan bukan `service_role_key` |
| 406 Not Acceptable | Pastikan tabel sudah dibuat via migration |
| RLS policy violation | Pastikan user sudah login/authenticated, atau gunakan service client |

---

## Referensi

- [Supabase Python Client Docs](https://supabase.com/docs/reference/python/introduction)
- [Supabase Row Level Security](https://supabase.com/docs/guides/auth/row-level-security)
- [FastAPI + Supabase Integration Guide](https://supabase.com/docs/guides/with/fastapi)