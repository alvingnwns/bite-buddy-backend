-- =============================================================
-- BiteBuddy — Migration 006: Revised Architecture Schema
-- =============================================================
-- Perubahan berdasarkan revisiHTML.md (2026-08-10):
--   1. users: tambah birth_date, gender
--   2. clinical_parameters: tambah diabetes_type, max_sugar_intake_g
--      (target_daily_calories & target_daily_carbs sudah ada di migration 003)
--   3. virtual_pets: pet_type jadi ENUM (5 jenis)
--   4. custom_meal_schedules: tambah last_penalty_date (fix penalty berulang)
--   5. Buat tabel nutrition_database (placeholder ground truth kalori)
-- =============================================================


-- =============================================================
-- 1. USERS — tambah data profil anak
-- =============================================================

-- ENUM untuk jenis kelamin
DO $$ BEGIN
    CREATE TYPE gender_type AS ENUM ('male', 'female');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- birth_date: dipakai untuk hitung umur → kalori otomatis
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS birth_date DATE,
    ADD COLUMN IF NOT EXISTS gender gender_type;

-- Catatan: full_name sudah ada di tabel users (dari migration 001)
-- Catatan: alergi (allergies) disimpan di clinical_parameters sebagai JSONB


-- =============================================================
-- 2. CLINICAL PARAMETERS — tambah diabetes type & max sugar
-- =============================================================

-- ENUM untuk tipe diabetes
-- Menentukan rekomendasi awal max_sugar_intake_g:
--   type1    → < 25g/hari (American Diabetes Association standard)
--   type2    → < 25g/hari (lebih ketat karena resistensi insulin)
--   prediabetes → < 36g/hari (WHO guideline)
--   gestational → < 25g/hari
DO $$ BEGIN
    CREATE TYPE diabetes_type AS ENUM ('type1', 'type2', 'prediabetes', 'gestational');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

ALTER TABLE public.clinical_parameters
    ADD COLUMN IF NOT EXISTS diabetes_type diabetes_type DEFAULT 'type1',
    ADD COLUMN IF NOT EXISTS max_sugar_intake_g FLOAT;
    -- target_daily_calories dan target_daily_carbs SUDAH ADA dari migration 003
    -- Kedua kolom ini sekarang DIHITUNG OTOMATIS oleh sistem via WHO formula,
    -- tapi dokter tetap bisa override via PATCH /clinical/{child_id}

-- Catatan untuk dokter: max_sugar_intake_g diisi oleh dokter, sistem berikan rekomendasi.
-- Rekomendasi dihitung di app/services/clinical_service.py berdasarkan diabetes_type.


-- =============================================================
-- 3. VIRTUAL PETS — pet_type jadi ENUM (5 jenis)
-- =============================================================

-- ENUM untuk jenis pet
DO $$ BEGIN
    CREATE TYPE pet_type AS ENUM ('cat', 'dog', 'rabbit', 'hamster', 'bird');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Konversi kolom pet_type dari TEXT ke ENUM
-- Perlu set default dulu agar row yang ada tidak rusak
ALTER TABLE public.virtual_pets
    ALTER COLUMN pet_type TYPE pet_type USING pet_type::pet_type;

-- Catatan semantik hunger (PERUBAHAN PENTING):
-- Sebelumnya: hunger tinggi = lapar (semantik salah)
-- SEKARANG  : hunger tinggi = kenyang (++hunger = makin kenyang)
-- Kolom hunger (INT 0-100) tetap, hanya MAKNA yang berubah.
-- Nilai default tetap 100 (lahir dalam keadaan kenyang).
-- compute_pet_status() thresholds TIDAK perlu diubah karena:
--   hunger < 30 masih berarti "sedikit kenyang" = lapar ✅


-- =============================================================
-- 4. CUSTOM MEAL SCHEDULES — fix penalty berulang
-- =============================================================

-- last_penalty_date: mencegah compliance_worker memberikan penalty
-- berulang-ulang untuk jadwal yang sama dalam satu hari.
-- Logika di compliance_worker.py:
--   IF last_penalty_date == today → skip (sudah kena penalty hari ini)
--   ELSE → berikan penalty + update last_penalty_date = today
ALTER TABLE public.custom_meal_schedules
    ADD COLUMN IF NOT EXISTS last_penalty_date DATE;

-- Index untuk query compliance worker yang sering ambil jadwal by day
CREATE INDEX IF NOT EXISTS idx_meal_schedules_penalty_date
    ON public.custom_meal_schedules(child_id, last_penalty_date);


-- =============================================================
-- 5. NUTRITION DATABASE — tabel ground truth kalori (placeholder)
-- =============================================================
-- Ini adalah placeholder. Data akan diisi secara bertahap.
-- Gemini akan gunakan tabel ini sebagai konteks saat mengestimasi kalori.
-- Jika makanan tidak ada di sini, Gemini akan estimate langsung.

CREATE TABLE IF NOT EXISTS public.nutrition_database (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    food_name       TEXT NOT NULL UNIQUE,      -- nama makanan (lowercase, bahasa Indonesia)
    food_name_en    TEXT,                       -- nama dalam bahasa Inggris (opsional)
    calories_per_100g   FLOAT NOT NULL,
    carbs_per_100g      FLOAT,
    sugar_per_100g      FLOAT,
    protein_per_100g    FLOAT,
    fat_per_100g        FLOAT,
    fiber_per_100g      FLOAT,
    is_healthy          BOOLEAN DEFAULT TRUE,
    category        TEXT,                       -- e.g. 'sayur', 'buah', 'protein', 'karbohidrat'
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index untuk pencarian cepat berdasarkan nama makanan
CREATE INDEX IF NOT EXISTS idx_nutrition_food_name
    ON public.nutrition_database(food_name);

-- Trigger auto-update updated_at
DO $$ BEGIN
    CREATE TRIGGER trg_nutrition_db_updated_at
        BEFORE UPDATE ON public.nutrition_database
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- =============================================================
-- SEED DATA: Beberapa makanan umum Indonesia sebagai placeholder
-- =============================================================
INSERT INTO public.nutrition_database
    (food_name, food_name_en, calories_per_100g, carbs_per_100g, sugar_per_100g,
     protein_per_100g, fat_per_100g, fiber_per_100g, is_healthy, category)
VALUES
    ('nasi putih',      'white rice',       130, 28.0, 0.1, 2.7, 0.3, 0.4, true,  'karbohidrat'),
    ('nasi merah',      'brown rice',       111, 23.0, 0.4, 2.6, 0.9, 1.8, true,  'karbohidrat'),
    ('ayam goreng',     'fried chicken',    250, 0.0,  0.0, 27.0, 15.0, 0.0, false, 'protein'),
    ('ayam rebus',      'boiled chicken',   165, 0.0,  0.0, 31.0,  3.6, 0.0, true,  'protein'),
    ('tempe goreng',    'fried tempeh',     195, 9.4,  0.0, 19.0, 11.0, 1.4, false, 'protein'),
    ('tempe kukus',     'steamed tempeh',   160, 9.4,  0.0, 19.0,  9.0, 1.4, true,  'protein'),
    ('tahu goreng',     'fried tofu',       115, 2.3,  0.3, 10.0,  7.0, 0.3, false, 'protein'),
    ('tahu kukus',      'steamed tofu',      76, 2.3,  0.3, 10.0,  4.0, 0.3, true,  'protein'),
    ('bayam',           'spinach',           23, 3.6,  0.4,  2.9,  0.4, 2.2, true,  'sayur'),
    ('kangkung',        'water spinach',     19, 3.1,  0.0,  2.6,  0.2, 2.1, true,  'sayur'),
    ('wortel',          'carrot',            41, 9.6,  4.7,  0.9,  0.2, 2.8, true,  'sayur'),
    ('brokoli',         'broccoli',          34, 7.0,  1.7,  2.8,  0.4, 2.6, true,  'sayur'),
    ('pisang',          'banana',            89, 23.0, 12.2,  1.1,  0.3, 2.6, true,  'buah'),
    ('apel',            'apple',             52, 14.0,  10.4, 0.3,  0.2, 2.4, true,  'buah'),
    ('jeruk',           'orange',            47, 12.0,  9.4,  0.9,  0.1, 2.4, true,  'buah'),
    ('roti tawar',      'white bread',      265, 49.0,  5.0,  9.0,  3.3, 2.7, false, 'karbohidrat'),
    ('roti gandum',     'whole wheat bread',247, 41.0,  6.0, 13.0,  4.2, 7.0, true,  'karbohidrat'),
    ('mie instan',      'instant noodles',  436, 63.0,  1.0,  9.0, 15.0, 2.5, false, 'karbohidrat'),
    ('kentang rebus',   'boiled potato',     87, 20.0,  0.9,  1.9,  0.1, 1.8, true,  'karbohidrat'),
    ('kentang goreng',  'french fries',     312, 41.0,  0.3,  3.4, 15.0, 3.8, false, 'karbohidrat'),
    ('telur rebus',     'boiled egg',       155, 1.1,   1.1, 13.0, 11.0, 0.0, true,  'protein'),
    ('susu full cream', 'full cream milk',   61, 4.7,   5.1,  3.2,  3.3, 0.0, true,  'minuman'),
    ('jus jeruk segar', 'fresh orange juice',45, 10.4,  8.4, 0.7,  0.2, 0.2, true,  'minuman'),
    ('burger',          'burger',           295, 24.0,  5.0, 17.0, 14.0, 1.5, false, 'junk food'),
    ('pizza',           'pizza',            266, 33.0,  3.6, 11.0, 10.0, 2.3, false, 'junk food'),
    ('es krim',         'ice cream',        207, 24.0, 21.0,  3.5, 11.0, 0.7, false, 'junk food')
ON CONFLICT (food_name) DO NOTHING;
