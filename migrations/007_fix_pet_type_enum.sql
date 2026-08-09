-- =============================================================
-- BiteBuddy — Migration 007: Fix pet_type ENUM conversion
-- =============================================================
-- Hotfix untuk error dari migration 006:
--   ERROR: 22P02: invalid input value for enum pet_type: "Blob"
--
-- Root cause: tabel virtual_pets punya data lama dengan nilai pet_type
-- yang tidak ada di ENUM baru (cat/dog/rabbit/hamster/bird).
-- Contoh: "Blob", "Dragon", atau nilai test lainnya.
--
-- Pelajaran: selalu UPDATE/clean data lama SEBELUM ALTER COLUMN ke ENUM.
-- =============================================================

-- Step 1: Buat ENUM pet_type (jika belum ada dari migration 006)
DO $$ BEGIN
    CREATE TYPE pet_type AS ENUM ('cat', 'dog', 'rabbit', 'hamster', 'bird');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Step 2: Bersihkan data lama — semua nilai yang TIDAK valid di-reset ke 'dog'
-- Ini aman karena data di virtual_pets saat ini hanya data test/demo
UPDATE public.virtual_pets
SET pet_type = 'dog'
WHERE pet_type NOT IN ('cat', 'dog', 'rabbit', 'hamster', 'bird');

-- Step 3: Sekarang aman untuk konversi kolom ke ENUM
ALTER TABLE public.virtual_pets
    ALTER COLUMN pet_type TYPE pet_type USING pet_type::pet_type;

-- Verifikasi: cek semua nilai setelah konversi
-- SELECT id, pet_name, pet_type FROM virtual_pets;
