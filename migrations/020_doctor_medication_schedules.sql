-- Materialize Doctor medication instructions as recurring schedules visible to Child.

ALTER TABLE public.custom_meal_schedules
    ADD COLUMN IF NOT EXISTS managed_by_doctor BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS recurrence_type TEXT,
    ADD COLUMN IF NOT EXISTS recurrence_interval_days INTEGER,
    ADD COLUMN IF NOT EXISTS recurrence_anchor_date DATE;

DO $$ BEGIN
    ALTER TABLE public.custom_meal_schedules
        ADD CONSTRAINT custom_meal_schedules_recurrence_type_check
        CHECK (recurrence_type IS NULL OR recurrence_type IN (
            'everyday', 'every_x_days', 'once_a_week', 'once_a_month'
        ));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE public.custom_meal_schedules
        ADD CONSTRAINT custom_meal_schedules_recurrence_days_check
        CHECK (recurrence_interval_days IS NULL OR recurrence_interval_days > 0);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_doctor_medication_schedules_child
    ON public.custom_meal_schedules (child_id, is_active)
    WHERE managed_by_doctor = true AND schedule_type = 'medicine';

CREATE OR REPLACE FUNCTION public.sync_doctor_medication_schedules(
    p_child_id UUID,
    p_doctor_id UUID,
    p_instructions JSONB
) RETURNS VOID
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
    v_instruction TEXT;
    v_match TEXT[];
    v_days_match TEXT[];
    v_recurrence TEXT;
    v_recurrence_type TEXT;
    v_interval_days INTEGER;
    v_start_time TIME;
    v_end_time TIME;
    v_anchor DATE := (now() AT TIME ZONE 'Asia/Jakarta')::date;
    v_existing_id UUID;
BEGIN
    IF jsonb_typeof(COALESCE(p_instructions, '[]'::jsonb)) <> 'array' THEN
        RAISE EXCEPTION 'invalid_medication_schedule' USING ERRCODE = '22023';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM public.users
        WHERE id = p_child_id AND doctor_id = p_doctor_id
          AND role = 'child' AND is_active = true
    ) THEN
        RAISE EXCEPTION 'patient_forbidden' USING ERRCODE = '42501';
    END IF;

    UPDATE public.custom_meal_schedules
    SET is_active = false
    WHERE child_id = p_child_id
      AND managed_by_doctor = true
      AND schedule_type = 'medicine';

    FOR v_instruction IN
        SELECT trim(value) FROM jsonb_array_elements_text(COALESCE(p_instructions, '[]'::jsonb))
        WHERE trim(value) <> ''
    LOOP
        v_match := regexp_match(
            v_instruction,
            '^([01][0-9]|2[0-3]):([0-5][0-9])(?:[[:space:]]*\|[[:space:]]*(.+))?$'
        );
        IF v_match IS NULL THEN
            RAISE EXCEPTION 'invalid_medication_schedule' USING ERRCODE = '22023';
        END IF;

        v_start_time := (v_match[1] || ':' || v_match[2])::time;
        v_end_time := CASE
            WHEN v_start_time >= time '23:00' THEN time '23:59'
            ELSE (v_start_time + interval '1 hour')::time
        END;
        v_recurrence := lower(COALESCE(NULLIF(trim(v_match[3]), ''), 'everyday'));
        v_interval_days := NULL;

        IF v_recurrence = 'everyday' THEN
            v_recurrence_type := 'everyday';
        ELSIF v_recurrence = 'once a week' THEN
            v_recurrence_type := 'once_a_week';
        ELSIF v_recurrence = 'once a month' THEN
            v_recurrence_type := 'once_a_month';
        ELSE
            v_days_match := regexp_match(v_recurrence, '^every ([0-9]+) days$');
            IF v_days_match IS NULL OR v_days_match[1]::integer < 2 THEN
                RAISE EXCEPTION 'invalid_medication_schedule' USING ERRCODE = '22023';
            END IF;
            v_recurrence_type := 'every_x_days';
            v_interval_days := v_days_match[1]::integer;
        END IF;

        SELECT id INTO v_existing_id
        FROM public.custom_meal_schedules
        WHERE child_id = p_child_id
          AND managed_by_doctor = true
          AND schedule_type = 'medicine'
          AND description = v_instruction
        ORDER BY created_at
        LIMIT 1;

        IF v_existing_id IS NULL THEN
            INSERT INTO public.custom_meal_schedules (
                child_id, created_by, meal_type, day_of_week, meal_name,
                description, is_active, start_date, start_time, end_time,
                schedule_type, managed_by_doctor, recurrence_type,
                recurrence_interval_days, recurrence_anchor_date
            ) VALUES (
                p_child_id, p_doctor_id, 'snack', EXTRACT(ISODOW FROM v_anchor)::integer - 1,
                'Medication', v_instruction, true, v_anchor, v_start_time, v_end_time,
                'medicine', true, v_recurrence_type, v_interval_days, v_anchor
            );
        ELSE
            UPDATE public.custom_meal_schedules
            SET created_by = p_doctor_id,
                day_of_week = EXTRACT(ISODOW FROM v_anchor)::integer - 1,
                is_active = true,
                start_time = v_start_time,
                end_time = v_end_time,
                recurrence_type = v_recurrence_type,
                recurrence_interval_days = v_interval_days
            WHERE id = v_existing_id;
        END IF;
        v_existing_id := NULL;
    END LOOP;
END $$;

REVOKE ALL ON FUNCTION public.sync_doctor_medication_schedules(UUID, UUID, JSONB) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.sync_doctor_medication_schedules(UUID, UUID, JSONB) TO service_role;

DO $$
BEGIN
    IF to_regprocedure('public.claim_patient_invitation_v012(uuid,text,text,text,text,text)') IS NULL THEN
        ALTER FUNCTION public.claim_patient_invitation(UUID, TEXT, TEXT, TEXT, TEXT, TEXT)
            RENAME TO claim_patient_invitation_v012;
    END IF;
END $$;

CREATE OR REPLACE FUNCTION public.claim_patient_invitation(
    p_auth_user_id UUID,
    p_email TEXT,
    p_username TEXT,
    p_password_hash TEXT,
    p_doctor_code TEXT,
    p_patient_code TEXT
) RETURNS UUID
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
    v_invitation_id UUID;
    v_profile public.doctor_patient_profiles;
BEGIN
    v_invitation_id := public.claim_patient_invitation_v012(
        p_auth_user_id, p_email, p_username, p_password_hash,
        p_doctor_code, p_patient_code
    );
    SELECT * INTO v_profile
    FROM public.doctor_patient_profiles
    WHERE patient_id = p_auth_user_id;
    PERFORM public.sync_doctor_medication_schedules(
        p_auth_user_id, v_profile.doctor_id, v_profile.medication_instructions
    );
    RETURN v_invitation_id;
END $$;

REVOKE ALL ON FUNCTION public.claim_patient_invitation(UUID, TEXT, TEXT, TEXT, TEXT, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.claim_patient_invitation(UUID, TEXT, TEXT, TEXT, TEXT, TEXT) TO service_role;

-- Backfill schedules for patients that were already claimed before this migration.
DO $$
DECLARE
    v_profile public.doctor_patient_profiles;
BEGIN
    FOR v_profile IN
        SELECT profile.*
        FROM public.doctor_patient_profiles AS profile
        JOIN public.users AS child
          ON child.id = profile.patient_id
         AND child.doctor_id = profile.doctor_id
         AND child.role = 'child'
         AND child.is_active = true
    LOOP
        PERFORM public.sync_doctor_medication_schedules(
            v_profile.patient_id, v_profile.doctor_id, v_profile.medication_instructions
        );
    END LOOP;
END $$;
