-- Stage 3: authoritative Doctor dashboard clinical data.

CREATE TABLE IF NOT EXISTS public.blood_glucose_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    recorded_by UUID NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
    value_mg_dl NUMERIC(8,2) NOT NULL CHECK (value_mg_dl >= 0),
    recorded_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_blood_glucose_patient_recorded
    ON public.blood_glucose_records(patient_id, recorded_at DESC);

CREATE TABLE IF NOT EXISTS public.doctor_appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    doctor_id UUID NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
    title TEXT NOT NULL CHECK (length(btrim(title)) BETWEEN 1 AND 200),
    starts_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL DEFAULT 'scheduled'
        CHECK (status IN ('scheduled', 'completed')),
    note TEXT,
    price_amount NUMERIC(14,2) CHECK (price_amount >= 0),
    currency TEXT CHECK (currency IS NULL OR currency = 'IDR'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_doctor_appointments_patient_starts
    ON public.doctor_appointments(patient_id, starts_at DESC);

ALTER TABLE public.blood_glucose_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.doctor_appointments ENABLE ROW LEVEL SECURITY;

-- Doctor endpoints use the service-role client after canonical role and
-- assignment checks. Child/Parent clients must not access these tables directly.
