-- Doctor patient invitation lifecycle and profile persistence.
-- Apply after 011_activity_logs_wib_month.sql.

CREATE TABLE IF NOT EXISTS public.patient_invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doctor_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    patient_code TEXT NOT NULL,
    full_name TEXT NOT NULL,
    gender gender_type NOT NULL,
    birth_date DATE NOT NULL,
    address TEXT NOT NULL,
    height_cm NUMERIC(5,1) NOT NULL CHECK (height_cm BETWEEN 20 AND 250),
    weight_kg NUMERIC(5,1) NOT NULL CHECK (weight_kg BETWEEN 1 AND 300),
    medical_history TEXT NOT NULL DEFAULT '',
    medication_instructions JSONB NOT NULL DEFAULT '[]'::jsonb,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'claimed', 'expired', 'cancelled')),
    claimed_user_id UUID UNIQUE REFERENCES public.users(id) ON DELETE SET NULL,
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + interval '30 days'),
    claimed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (jsonb_typeof(medication_instructions) = 'array')
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_patient_invitations_code_ci
    ON public.patient_invitations (lower(patient_code));
CREATE INDEX IF NOT EXISTS idx_patient_invitations_doctor_status
    ON public.patient_invitations (doctor_id, status, created_at DESC);

CREATE TABLE IF NOT EXISTS public.doctor_patient_profiles (
    patient_id UUID PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
    doctor_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    medical_history TEXT NOT NULL DEFAULT '',
    medication_instructions JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (jsonb_typeof(medication_instructions) = 'array')
);

CREATE INDEX IF NOT EXISTS idx_doctor_patient_profiles_doctor
    ON public.doctor_patient_profiles (doctor_id, patient_id);

CREATE OR REPLACE FUNCTION public.claim_patient_invitation(
    p_auth_user_id UUID,
    p_email TEXT,
    p_username TEXT,
    p_password_hash TEXT,
    p_doctor_code TEXT,
    p_patient_code TEXT
) RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    invitation public.patient_invitations%ROWTYPE;
BEGIN
    SELECT * INTO invitation
    FROM public.patient_invitations pi
    WHERE lower(pi.patient_code) = lower(trim(p_patient_code))
      AND pi.status = 'pending'
      AND pi.expires_at > now()
      AND pi.doctor_id = (
          SELECT id FROM public.users
          WHERE role = 'doctor'
            AND is_active = true
            AND lower(doctor_code) = lower(trim(p_doctor_code))
      )
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'patient_invitation_invalid' USING ERRCODE = 'P0001';
    END IF;

    INSERT INTO public.users (
        id, email, username, password_hash, full_name, role, doctor_id,
        patient_code, birth_date, gender, address, is_active
    ) VALUES (
        p_auth_user_id, p_email, p_username, p_password_hash,
        invitation.full_name, 'child', invitation.doctor_id,
        invitation.patient_code, invitation.birth_date, invitation.gender,
        invitation.address, true
    );

    INSERT INTO public.clinical_parameters (
        child_id, recorded_by, height_cm, weight_kg, medical_conditions, notes
    ) VALUES (
        p_auth_user_id, invitation.doctor_id, invitation.height_cm,
        invitation.weight_kg, '[]'::jsonb, invitation.medical_history
    );

    INSERT INTO public.doctor_patient_profiles (
        patient_id, doctor_id, medical_history, medication_instructions
    ) VALUES (
        p_auth_user_id, invitation.doctor_id, invitation.medical_history,
        invitation.medication_instructions
    );

    UPDATE public.patient_invitations
    SET status = 'claimed', claimed_user_id = p_auth_user_id,
        claimed_at = now(), updated_at = now()
    WHERE id = invitation.id;

    RETURN invitation.id;
END;
$$;

REVOKE ALL ON FUNCTION public.claim_patient_invitation(UUID, TEXT, TEXT, TEXT, TEXT, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.claim_patient_invitation(UUID, TEXT, TEXT, TEXT, TEXT, TEXT) TO service_role;

ALTER TABLE public.patient_invitations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.doctor_patient_profiles ENABLE ROW LEVEL SECURITY;

DROP TRIGGER IF EXISTS trg_patient_invitations_updated_at ON public.patient_invitations;
CREATE TRIGGER trg_patient_invitations_updated_at
    BEFORE UPDATE ON public.patient_invitations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_doctor_patient_profiles_updated_at ON public.doctor_patient_profiles;
CREATE TRIGGER trg_doctor_patient_profiles_updated_at
    BEFORE UPDATE ON public.doctor_patient_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
