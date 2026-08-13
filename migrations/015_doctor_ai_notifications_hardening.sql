-- Stage 5: Doctor notification outbox, idempotency, and atomic activity logs.

CREATE TABLE IF NOT EXISTS public.doctor_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doctor_id UUID NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
    patient_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    recipient_user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    recipient TEXT NOT NULL CHECK (recipient IN ('patient', 'parent')),
    type TEXT NOT NULL CHECK (type IN (
        'eat_more_vegetables', 'take_medication',
        'appointment_reminder', 'reduce_sugar'
    )),
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    delivery_status TEXT NOT NULL DEFAULT 'accepted'
        CHECK (delivery_status = 'accepted'),
    idempotency_key TEXT NOT NULL CHECK (length(idempotency_key) BETWEEN 8 AND 128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (doctor_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_doctor_notifications_patient_created
    ON public.doctor_notifications(patient_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_doctor_notifications_recipient_created
    ON public.doctor_notifications(recipient_user_id, created_at DESC);
ALTER TABLE public.doctor_notifications ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION public.doctor_create_notification(
    p_doctor_id UUID, p_patient_id UUID, p_recipient TEXT, p_type TEXT,
    p_title TEXT, p_body TEXT, p_idempotency_key TEXT, p_request_id TEXT
) RETURNS JSONB
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
    v_patient public.users;
    v_recipient_user_id UUID;
    v_row public.doctor_notifications;
    v_now TIMESTAMPTZ := now();
BEGIN
    SELECT * INTO v_row FROM public.doctor_notifications
    WHERE doctor_id = p_doctor_id AND idempotency_key = p_idempotency_key;
    IF FOUND THEN
        IF v_row.patient_id <> p_patient_id OR v_row.recipient <> p_recipient
           OR v_row.type <> p_type THEN
            RAISE EXCEPTION 'idempotency_conflict' USING ERRCODE = '23505';
        END IF;
        RETURN to_jsonb(v_row);
    END IF;

    SELECT * INTO v_patient FROM public.users
    WHERE id = p_patient_id AND doctor_id = p_doctor_id
      AND role = 'child' AND is_active = true;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'doctor_patient_forbidden' USING ERRCODE = '42501';
    END IF;

    IF p_recipient = 'patient' THEN
        v_recipient_user_id := p_patient_id;
    ELSIF p_recipient = 'parent' AND v_patient.parent_id IS NOT NULL
          AND EXISTS (SELECT 1 FROM public.users WHERE id = v_patient.parent_id
                      AND role = 'parent' AND is_active = true) THEN
        v_recipient_user_id := v_patient.parent_id;
    ELSE
        RAISE EXCEPTION 'parent_not_linked' USING ERRCODE = 'P0001';
    END IF;

    INSERT INTO public.doctor_notifications (
        doctor_id, patient_id, recipient_user_id, recipient, type,
        title, body, idempotency_key, created_at
    ) VALUES (
        p_doctor_id, p_patient_id, v_recipient_user_id, p_recipient, p_type,
        p_title, p_body, p_idempotency_key, v_now
    ) RETURNING * INTO v_row;

    INSERT INTO public.activity_logs
        (user_id, action, entity_type, entity_id, metadata, created_at, wib_month)
    VALUES (
        p_doctor_id, 'notification.create', 'notification', v_row.id,
        jsonb_build_object(
            'role', 'doctor', 'child_id', p_patient_id,
            'recipient', p_recipient, 'notification_type', p_type,
            'description', 'Created patient-scoped notification.',
            'outcome', 'success', 'request_id', p_request_id
        ), v_now, to_char(v_now AT TIME ZONE 'Asia/Jakarta', 'YYYY-MM')
    );
    RETURN to_jsonb(v_row);
END $$;

REVOKE ALL ON FUNCTION public.doctor_create_notification(
    UUID, UUID, TEXT, TEXT, TEXT, TEXT, TEXT, TEXT
) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.doctor_create_notification(
    UUID, UUID, TEXT, TEXT, TEXT, TEXT, TEXT, TEXT
) TO service_role;
