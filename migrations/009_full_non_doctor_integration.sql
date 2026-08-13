-- BiteBuddy non-doctor API contract persistence (Asia/Jakarta MVP).

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS username TEXT,
    ADD COLUMN IF NOT EXISTS patient_code TEXT,
    ADD COLUMN IF NOT EXISTS doctor_code TEXT;

UPDATE public.users
SET username = split_part(email, '@', 1)
WHERE username IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_ci
    ON public.users (lower(username));
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_patient_code
    ON public.users (patient_code) WHERE patient_code IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_doctor_code
    ON public.users (doctor_code) WHERE doctor_code IS NOT NULL;

CREATE TABLE IF NOT EXISTS public.analysis_drafts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    child_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    analysis_type TEXT NOT NULL CHECK (analysis_type IN ('food', 'medicine')),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    image_url TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'awaiting_confirmation', 'failed', 'confirmed')),
    confirmed_history_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    confirmed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_analysis_drafts_child_created
    ON public.analysis_drafts(child_id, created_at DESC);

ALTER TABLE public.custom_meal_schedules
    ADD COLUMN IF NOT EXISTS schedule_type TEXT NOT NULL DEFAULT 'meal'
        CHECK (schedule_type IN ('meal', 'medicine'));

CREATE TABLE IF NOT EXISTS public.schedule_occurrences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_id UUID NOT NULL REFERENCES public.custom_meal_schedules(id) ON DELETE CASCADE,
    child_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    occurrence_date DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'not_yet'
        CHECK (status IN ('done', 'skipped', 'late', 'not_yet')),
    completed_at TIMESTAMPTZ,
    UNIQUE(schedule_id, occurrence_date)
);
CREATE INDEX IF NOT EXISTS idx_schedule_occurrences_child_date
    ON public.schedule_occurrences(child_id, occurrence_date);

ALTER TABLE public.food_logs
    ADD COLUMN IF NOT EXISTS analysis_id UUID,
    ADD COLUMN IF NOT EXISTS portion_grams NUMERIC(10,2),
    ADD COLUMN IF NOT EXISTS nutrition JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS is_healthy BOOLEAN;
CREATE UNIQUE INDEX IF NOT EXISTS idx_food_logs_analysis_id
    ON public.food_logs(analysis_id) WHERE analysis_id IS NOT NULL;

ALTER TABLE public.medication_logs
    ADD COLUMN IF NOT EXISTS analysis_id UUID,
    ADD COLUMN IF NOT EXISTS photo_url TEXT,
    ADD COLUMN IF NOT EXISTS is_medicine BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'done';
CREATE UNIQUE INDEX IF NOT EXISTS idx_medication_logs_analysis_id
    ON public.medication_logs(analysis_id) WHERE analysis_id IS NOT NULL;

ALTER TABLE public.alerts
    ADD COLUMN IF NOT EXISTS sender_type TEXT NOT NULL DEFAULT 'pet'
        CHECK (sender_type IN ('doctor', 'parent', 'pet')),
    ADD COLUMN IF NOT EXISTS title TEXT NOT NULL DEFAULT 'BiteBuddy';

-- A default partition prevents audit writes from failing when a new month starts.
CREATE TABLE IF NOT EXISTS public.activity_logs_default
    PARTITION OF public.activity_logs DEFAULT;

