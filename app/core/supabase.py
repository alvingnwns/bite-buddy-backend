"""Supabase client singletons.

Menyediakan dua client instance:
- ``supabase``         : menggunakan anon key (tunduk pada RLS).
- ``supabase_service`` : menggunakan service-role key (bypass RLS,
                         hanya untuk operasi backend-to-backend).

Kedua instance di-cache lewat ``@lru_cache`` sehingga hanya dibuat
satu kali selama lifetime proses.
"""

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
