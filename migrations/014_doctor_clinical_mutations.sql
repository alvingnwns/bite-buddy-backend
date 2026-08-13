-- Stage 4: Doctor clinical mutations and atomic success activity logs.

CREATE TABLE IF NOT EXISTS public.doctor_diagnoses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    doctor_id UUID NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
    chief_complaint TEXT NOT NULL CHECK (length(btrim(chief_complaint)) BETWEEN 1 AND 5000),
    medical_diagnosis TEXT NOT NULL CHECK (length(btrim(medical_diagnosis)) BETWEEN 1 AND 5000),
    therapy TEXT NOT NULL CHECK (length(btrim(therapy)) BETWEEN 1 AND 5000),
    price_amount NUMERIC(14,2) NOT NULL CHECK (price_amount >= 0),
    currency TEXT NOT NULL DEFAULT 'IDR' CHECK (currency = 'IDR'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_doctor_diagnoses_patient_created
    ON public.doctor_diagnoses(patient_id, created_at DESC);

ALTER TABLE public.doctor_diagnoses ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION public.doctor_create_blood_glucose(
    p_doctor_id UUID, p_patient_id UUID, p_value_mg_dl NUMERIC,
    p_recorded_at TIMESTAMPTZ, p_request_id TEXT
) RETURNS JSONB
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE v_row public.blood_glucose_records; v_now TIMESTAMPTZ := now();
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM public.users
        WHERE id = p_patient_id AND doctor_id = p_doctor_id
          AND role = 'child' AND is_active = true
    ) THEN RAISE EXCEPTION 'doctor_patient_forbidden' USING ERRCODE = '42501'; END IF;

    INSERT INTO public.blood_glucose_records
        (patient_id, recorded_by, value_mg_dl, recorded_at, created_at)
    VALUES (p_patient_id, p_doctor_id, p_value_mg_dl, p_recorded_at, v_now)
    RETURNING * INTO v_row;

    INSERT INTO public.activity_logs
        (user_id, action, entity_type, entity_id, metadata, created_at, wib_month)
    VALUES (
        p_doctor_id, 'blood_glucose.create', 'blood_glucose', v_row.id,
        jsonb_build_object('role', 'doctor', 'child_id', p_patient_id,
            'description', 'Created patient blood glucose reading.',
            'outcome', 'success', 'request_id', p_request_id),
        v_now, to_char(v_now AT TIME ZONE 'Asia/Jakarta', 'YYYY-MM')
    );

    RETURN jsonb_build_object('id', v_row.id, 'patient_id', v_row.patient_id,
        'value_mg_dl', v_row.value_mg_dl, 'recorded_at', v_row.recorded_at,
        'created_at', v_row.created_at);
END $$;

CREATE OR REPLACE FUNCTION public.doctor_create_appointment(
    p_doctor_id UUID, p_patient_id UUID, p_title TEXT,
    p_starts_at TIMESTAMPTZ, p_request_id TEXT
) RETURNS JSONB
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE v_row public.doctor_appointments; v_now TIMESTAMPTZ := now();
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM public.users
        WHERE id = p_patient_id AND doctor_id = p_doctor_id
          AND role = 'child' AND is_active = true
    ) THEN RAISE EXCEPTION 'doctor_patient_forbidden' USING ERRCODE = '42501'; END IF;

    INSERT INTO public.doctor_appointments
        (patient_id, doctor_id, title, starts_at, status, created_at, updated_at)
    VALUES (p_patient_id, p_doctor_id, btrim(p_title), p_starts_at,
        'scheduled', v_now, v_now)
    RETURNING * INTO v_row;

    INSERT INTO public.activity_logs
        (user_id, action, entity_type, entity_id, metadata, created_at, wib_month)
    VALUES (
        p_doctor_id, 'appointment.create', 'appointment', v_row.id,
        jsonb_build_object('role', 'doctor', 'child_id', p_patient_id,
            'description', 'Scheduled patient appointment.',
            'outcome', 'success', 'request_id', p_request_id),
        v_now, to_char(v_now AT TIME ZONE 'Asia/Jakarta', 'YYYY-MM')
    );

    RETURN jsonb_build_object('id', v_row.id, 'patient_id', v_row.patient_id,
        'title', v_row.title, 'starts_at', v_row.starts_at, 'status', v_row.status,
        'created_at', v_row.created_at);
END $$;

CREATE OR REPLACE FUNCTION public.doctor_create_diagnosis(
    p_doctor_id UUID, p_patient_id UUID, p_chief_complaint TEXT,
    p_medical_diagnosis TEXT, p_therapy TEXT, p_price_amount NUMERIC,
    p_currency TEXT, p_request_id TEXT
) RETURNS JSONB
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE v_row public.doctor_diagnoses; v_now TIMESTAMPTZ := now();
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM public.users
        WHERE id = p_patient_id AND doctor_id = p_doctor_id
          AND role = 'child' AND is_active = true
    ) THEN RAISE EXCEPTION 'doctor_patient_forbidden' USING ERRCODE = '42501'; END IF;

    INSERT INTO public.doctor_diagnoses
        (patient_id, doctor_id, chief_complaint, medical_diagnosis,
         therapy, price_amount, currency, created_at)
    VALUES (p_patient_id, p_doctor_id, btrim(p_chief_complaint),
        btrim(p_medical_diagnosis), btrim(p_therapy), p_price_amount,
        p_currency, v_now)
    RETURNING * INTO v_row;

    INSERT INTO public.activity_logs
        (user_id, action, entity_type, entity_id, metadata, created_at, wib_month)
    VALUES (
        p_doctor_id, 'diagnosis.create', 'diagnosis', v_row.id,
        jsonb_build_object('role', 'doctor', 'child_id', p_patient_id,
            'description', 'Created patient diagnosis.', 'outcome', 'success',
            'request_id', p_request_id, 'price_amount', v_row.price_amount,
            'currency', v_row.currency),
        v_now, to_char(v_now AT TIME ZONE 'Asia/Jakarta', 'YYYY-MM')
    );

    RETURN jsonb_build_object('id', v_row.id, 'patient_id', v_row.patient_id,
        'doctor_id', v_row.doctor_id, 'chief_complaint', v_row.chief_complaint,
        'medical_diagnosis', v_row.medical_diagnosis, 'therapy', v_row.therapy,
        'price_amount', v_row.price_amount, 'currency', v_row.currency,
        'created_at', v_row.created_at);
END $$;

REVOKE ALL ON FUNCTION public.doctor_create_blood_glucose(UUID, UUID, NUMERIC, TIMESTAMPTZ, TEXT) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.doctor_create_appointment(UUID, UUID, TEXT, TIMESTAMPTZ, TEXT) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.doctor_create_diagnosis(UUID, UUID, TEXT, TEXT, TEXT, NUMERIC, TEXT, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.doctor_create_blood_glucose(UUID, UUID, NUMERIC, TIMESTAMPTZ, TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION public.doctor_create_appointment(UUID, UUID, TEXT, TIMESTAMPTZ, TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION public.doctor_create_diagnosis(UUID, UUID, TEXT, TEXT, TEXT, NUMERIC, TEXT, TEXT) TO service_role;
