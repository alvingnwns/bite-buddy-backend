-- =============================================================
-- BiteBuddy — Initial Database Schema (Migration 001)
-- =============================================================
-- Tables:
--   1. users
--   2. clinical_parameters
--   3. custom_meal_schedules
--   4. virtual_pets
--   5. food_logs
--   6. medication_logs
-- =============================================================

-- =============================================================
-- ENUM: user_role
-- =============================================================
DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('doctor', 'parent', 'child');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- =============================================================
-- ENUM: meal_type
-- =============================================================
DO $$ BEGIN
    CREATE TYPE meal_type AS ENUM ('breakfast', 'lunch', 'dinner', 'snack');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- =============================================================
-- 1. USERS
-- =============================================================
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    full_name       TEXT NOT NULL,
    role            user_role NOT NULL DEFAULT 'child',
    parent_id       UUID REFERENCES users(id) ON DELETE SET NULL,
    doctor_id       UUID REFERENCES users(id) ON DELETE SET NULL,
    avatar_url      TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for fast lookups by email
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Index for role-based queries
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- Index for parent-child relationships
CREATE INDEX IF NOT EXISTS idx_users_parent_id ON users(parent_id);

-- Index for doctor-patient relationships
CREATE INDEX IF NOT EXISTS idx_users_doctor_id ON users(doctor_id);

-- Trigger: auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$ BEGIN
    CREATE TRIGGER trg_users_updated_at
        BEFORE UPDATE ON users
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- =============================================================
-- 2. CLINICAL PARAMETERS
-- =============================================================
CREATE TABLE IF NOT EXISTS clinical_parameters (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    child_id                UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recorded_by             UUID NOT NULL REFERENCES users(id) ON DELETE SET NULL,
    height_cm               NUMERIC(5, 1) NOT NULL,
    weight_kg               NUMERIC(5, 1) NOT NULL,
    bmi                     NUMERIC(4, 1) GENERATED ALWAYS AS (
                                ROUND((weight_kg / ((height_cm / 100) ^ 2))::numeric, 1)
                            ) STORED,
    head_circumference_cm   NUMERIC(4, 1),
    allergies               JSONB DEFAULT '[]'::jsonb,
    medical_conditions       JSONB DEFAULT '[]'::jsonb,
    notes                   TEXT,
    recorded_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for querying clinical data by child
CREATE INDEX IF NOT EXISTS idx_clinical_params_child_id ON clinical_parameters(child_id);

-- Index for querying by recorded date
CREATE INDEX IF NOT EXISTS idx_clinical_params_recorded_at ON clinical_parameters(recorded_at DESC);

-- =============================================================
-- 3. CUSTOM MEAL SCHEDULES
-- =============================================================
CREATE TABLE IF NOT EXISTS custom_meal_schedules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    child_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_by      UUID NOT NULL REFERENCES users(id) ON DELETE SET NULL,
    meal_type       meal_type NOT NULL,
    day_of_week     INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
    meal_name       TEXT NOT NULL,
    description     TEXT,
    calories        INTEGER,
    portion_size    TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    start_date      DATE NOT NULL DEFAULT CURRENT_DATE,
    end_date        DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for retrieving schedules by child
CREATE INDEX IF NOT EXISTS idx_meal_schedules_child_id ON custom_meal_schedules(child_id);

-- Index for active schedules on specific days
CREATE INDEX IF NOT EXISTS idx_meal_schedules_active_day
    ON custom_meal_schedules(child_id, day_of_week)
    WHERE is_active = TRUE;

-- Trigger: auto-update updated_at
DO $$ BEGIN
    CREATE TRIGGER trg_meal_schedules_updated_at
        BEFORE UPDATE ON custom_meal_schedules
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- =============================================================
-- 4. VIRTUAL PETS
-- =============================================================
-- ── Helper function: compute pet status from happiness + hunger ──────
CREATE OR REPLACE FUNCTION compute_pet_status(happiness INT, hunger INT)
RETURNS TEXT AS $$
BEGIN
    IF happiness < 10 OR hunger < 10 THEN
        RETURN 'critical';
    END IF;
    IF happiness < 20 AND hunger < 20 THEN
        RETURN 'sick';
    END IF;
    IF hunger < 30 THEN
        RETURN 'hungry';
    END IF;
    IF happiness < 40 THEN
        RETURN 'sad';
    END IF;
    IF happiness >= 70 AND hunger >= 70 THEN
        RETURN 'happy';
    END IF;
    RETURN 'neutral';
END;
$$ LANGUAGE plpgsql IMMUTABLE;


CREATE TABLE IF NOT EXISTS virtual_pets (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    child_id            UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    pet_name            TEXT NOT NULL,
    pet_type            TEXT NOT NULL,
    level               INTEGER NOT NULL DEFAULT 1 CHECK (level >= 1),
    experience_points   INTEGER NOT NULL DEFAULT 0 CHECK (experience_points >= 0),
    happiness           INTEGER NOT NULL DEFAULT 100 CHECK (happiness BETWEEN 0 AND 100),
    hunger              INTEGER NOT NULL DEFAULT 100 CHECK (hunger BETWEEN 0 AND 100),
    current_status      TEXT GENERATED ALWAYS AS (
                            compute_pet_status(happiness, hunger)
                        ) STORED,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for looking up pet by child
CREATE INDEX IF NOT EXISTS idx_virtual_pets_child_id ON virtual_pets(child_id);

-- Index for filtering by health status
CREATE INDEX IF NOT EXISTS idx_virtual_pets_status ON virtual_pets(current_status);

-- Trigger: auto-update updated_at
DO $$ BEGIN
    CREATE TRIGGER trg_virtual_pets_updated_at
        BEFORE UPDATE ON virtual_pets
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- =============================================================
-- 5. FOOD LOGS
-- =============================================================
CREATE TABLE IF NOT EXISTS food_logs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    child_id            UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    logged_by           UUID NOT NULL REFERENCES users(id) ON DELETE SET NULL,
    meal_schedule_id    UUID REFERENCES custom_meal_schedules(id) ON DELETE SET NULL,
    meal_type           meal_type NOT NULL,
    food_name           TEXT NOT NULL,
    portion_size        TEXT,
    calories            INTEGER,
    photo_url           TEXT,
    notes               TEXT,
    consumed_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for querying logs by child and date
CREATE INDEX IF NOT EXISTS idx_food_logs_child_date
    ON food_logs(child_id, consumed_at DESC);

-- Index for querying logs by meal type
CREATE INDEX IF NOT EXISTS idx_food_logs_meal_type ON food_logs(meal_type);

-- Index for linking to meal schedule
CREATE INDEX IF NOT EXISTS idx_food_logs_meal_schedule_id
    ON food_logs(meal_schedule_id);

-- =============================================================
-- 6. MEDICATION LOGS
-- =============================================================
CREATE TABLE IF NOT EXISTS medication_logs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    child_id            UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    administered_by     UUID NOT NULL REFERENCES users(id) ON DELETE SET NULL,
    medication_name     TEXT NOT NULL,
    dosage              NUMERIC(10, 2) NOT NULL,
    dosage_unit         TEXT NOT NULL,
    route               TEXT NOT NULL DEFAULT 'oral',
    scheduled_time      TIME NOT NULL,
    administered_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    was_taken           BOOLEAN NOT NULL DEFAULT TRUE,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for querying medication logs by child and date
CREATE INDEX IF NOT EXISTS idx_medication_logs_child_date
    ON medication_logs(child_id, administered_at DESC);

-- Index for querying by medication name
CREATE INDEX IF NOT EXISTS idx_medication_logs_name
    ON medication_logs(medication_name);

-- Index for scheduled time queries
CREATE INDEX IF NOT EXISTS idx_medication_logs_scheduled_time
    ON medication_logs(scheduled_time);