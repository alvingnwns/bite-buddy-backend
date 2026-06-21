import uuid
from typing import Optional

from fastapi import HTTPException, status
from supabase import Client

from app.core.supabase import get_supabase_service_client

# Konstanta Validasi
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


class StorageService:
    """Service untuk menangani unggahan file ke Supabase Storage."""

    def __init__(self) -> None:
        # Menggunakan lazy client dari Fase 0
        self.supabase: Client = get_supabase_service_client()

    def _validate_file(self, filename: str, file_size: int) -> None:
        """Validasi ekstensi dan ukuran file."""
        if not filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename tidak boleh kosong",
            )

        # Cek ekstensi
        ext = filename.split(".")[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ekstensi file tidak diizinkan. Gunakan: {', '.join(ALLOWED_EXTENSIONS)}",
            )

        # Cek ukuran
        if file_size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Ukuran file terlalu besar. Maksimal {MAX_FILE_SIZE_MB}MB",
            )

    async def upload_image(
        self, file_bytes: bytes, filename: str, bucket_name: str
    ) -> str:
        """
        Mengunggah gambar ke Supabase Storage dan mengembalikan URL publiknya.

        Args:
            file_bytes: Byte file yang diunggah.
            filename: Nama file asli dari client.
            bucket_name: Nama bucket di Supabase (misal: 'food-photos').

        Returns:
            str: URL publik gambar.
        """
        # 1. Validasi
        self._validate_file(filename, len(file_bytes))

        # 2. Generate nama file unik agar tidak tertimpa
        ext = filename.split(".")[-1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{ext}"

        # 3. Upload ke Supabase
        try:
            # Karena supabase-py saat ini masih synchronous, eksekusinya tetap blocking
            # Namun kita membungkusnya di fungsi async untuk kompatibilitas dengan gather
            # (Jika ingin benar-benar non-blocking, bisa dibungkus asyncio.to_thread)
            res = self.supabase.storage.from_(bucket_name).upload(
                path=unique_filename,
                file=file_bytes,
                file_options={"content-type": f"image/{ext}"},
            )
            
            # Jika berhasil, dapatkan public URL
            public_url = self.supabase.storage.from_(bucket_name).get_public_url(
                unique_filename
            )
            return public_url

        except Exception as e:
            # Supabase biasanya melempar StorageException jika bucket tidak ada atau RLS gagal
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gagal mengunggah gambar ke cloud storage: {str(e)}",
            )

