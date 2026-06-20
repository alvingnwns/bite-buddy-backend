"""Supabase client singletons.

Menyediakan dua client instance:
- ``get_supabase_client()``         : menggunakan anon key (tunduk pada RLS).
- ``get_supabase_service_client()`` : menggunakan service-role key (bypass RLS,
                                      hanya untuk operasi backend-to-backend).

Kedua instance di-cache lewat ``@lru_cache`` sehingga hanya dibuat
satu kali selama lifetime proses.

CATATAN ARSITEKTUR — Lazy Initialization:
  Client TIDAK dibuat saat module di-import, melainkan saat pertama kali
  dipanggil. Ini mencegah server crash saat startup jika .env belum terisi.
  Gunakan fungsi get_supabase_client() / get_supabase_service_client() sebagai
  FastAPI dependency, atau impor langsung untuk akses singleton.
"""

from functools import lru_cache

from supabase import Client, create_client

from app.core.config import settings


@lru_cache
def get_supabase_client() -> Client:
    """Membuat dan meng-cache Supabase client instance (anon key).

    Raises:
        ValueError: Jika SUPABASE_URL atau SUPABASE_ANON_KEY belum diisi di .env
    """
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise ValueError(
            "SUPABASE_URL dan SUPABASE_ANON_KEY harus diisi di file .env"
        )
    return create_client(
        supabase_url=settings.supabase_url,
        supabase_key=settings.supabase_anon_key,
    )


@lru_cache
def get_supabase_service_client() -> Client:
    """Membuat dan meng-cache Supabase service role client.

    Hanya digunakan untuk operasi backend-to-backend (bypass RLS).
    Jangan pernah expose service_role_key ke client-side.

    Raises:
        ValueError: Jika SUPABASE_URL atau SUPABASE_SERVICE_ROLE_KEY belum diisi di .env
    """
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise ValueError(
            "SUPABASE_URL dan SUPABASE_SERVICE_ROLE_KEY harus diisi di file .env"
        )
    return create_client(
        supabase_url=settings.supabase_url,
        supabase_key=settings.supabase_service_role_key,
    )

