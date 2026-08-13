-- Cross-app notification delivery and atomic Child confirmations.

ALTER TABLE public.alerts
    ADD COLUMN IF NOT EXISTS recipient_user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS doctor_notification_id UUID REFERENCES public.doctor_notifications(id) ON DELETE CASCADE;

CREATE UNIQUE INDEX IF NOT EXISTS idx_alerts_doctor_notification
    ON public.alerts(doctor_notification_id) WHERE doctor_notification_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_alerts_recipient_created
    ON public.alerts(recipient_user_id, created_at DESC);

INSERT INTO public.alerts (
    child_id, recipient_user_id, doctor_notification_id, type,
    sender_type, title, message, is_read, created_at
)
SELECT
    patient_id, recipient_user_id, id, type,
    'doctor', title, body, false, created_at
FROM public.doctor_notifications
ON CONFLICT (doctor_notification_id) WHERE doctor_notification_id IS NOT NULL DO NOTHING;

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
        INSERT INTO public.alerts (
            child_id, recipient_user_id, doctor_notification_id, type,
            sender_type, title, message, is_read, created_at
        ) VALUES (
            v_row.patient_id, v_row.recipient_user_id, v_row.id, v_row.type,
            'doctor', v_row.title, v_row.body, false, v_row.created_at
        ) ON CONFLICT (doctor_notification_id) WHERE doctor_notification_id IS NOT NULL DO NOTHING;
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

    INSERT INTO public.alerts (
        child_id, recipient_user_id, doctor_notification_id, type,
        sender_type, title, message, is_read, created_at
    ) VALUES (
        p_patient_id, v_recipient_user_id, v_row.id, p_type,
        'doctor', p_title, p_body, false, v_now
    );

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

CREATE OR REPLACE FUNCTION public.confirm_child_analysis(
    p_child_id UUID,
    p_analysis_id UUID,
    p_analysis_type TEXT,
    p_portion_grams NUMERIC DEFAULT NULL,
    p_nutrition JSONB DEFAULT '{}'::jsonb,
    p_is_healthy BOOLEAN DEFAULT true
) RETURNS JSONB
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
    v_draft public.analysis_drafts;
    v_history JSONB;
    v_history_id UUID;
    v_schedule public.custom_meal_schedules;
    v_occurrence_date DATE := (now() AT TIME ZONE 'Asia/Jakarta')::date;
    v_now_time TIME := (now() AT TIME ZONE 'Asia/Jakarta')::time;
    v_now TIMESTAMPTZ := now();
    v_pet public.virtual_pets;
    v_exp_delta INTEGER;
    v_happiness_delta INTEGER;
    v_hunger_delta INTEGER;
    v_target NUMERIC := 500;
    v_calories NUMERIC := COALESCE((p_nutrition->>'kcal')::numeric, 0);
    v_streak INTEGER;
    v_previous_level INTEGER;
BEGIN
    IF p_analysis_type NOT IN ('food', 'medicine') THEN
        RAISE EXCEPTION 'invalid_analysis_type' USING ERRCODE = '22023';
    END IF;

    SELECT * INTO v_draft FROM public.analysis_drafts
    WHERE id = p_analysis_id AND analysis_type = p_analysis_type
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'analysis_not_found' USING ERRCODE = 'P0002';
    END IF;
    IF v_draft.child_id <> p_child_id THEN
        RAISE EXCEPTION 'analysis_forbidden' USING ERRCODE = '42501';
    END IF;

    IF v_draft.status = 'confirmed' THEN
        IF p_analysis_type = 'food' THEN
            SELECT to_jsonb(f), f.id INTO v_history, v_history_id
            FROM public.food_logs f WHERE f.analysis_id = p_analysis_id;
        ELSE
            SELECT to_jsonb(m), m.id INTO v_history, v_history_id
            FROM public.medication_logs m WHERE m.analysis_id = p_analysis_id;
        END IF;
        IF v_history IS NULL THEN
            RAISE EXCEPTION 'confirmed_history_missing' USING ERRCODE = 'P0001';
        END IF;
    ELSE
        IF p_analysis_type = 'medicine'
           AND NOT COALESCE((v_draft.payload->>'isMedicine')::boolean, false) THEN
            RAISE EXCEPTION 'invalid_medicine' USING ERRCODE = '22023';
        END IF;

        SELECT * INTO v_schedule FROM public.custom_meal_schedules
        WHERE child_id = p_child_id AND is_active = true
          AND schedule_type = CASE WHEN p_analysis_type = 'food' THEN 'meal' ELSE 'medicine' END
          AND day_of_week = EXTRACT(ISODOW FROM v_occurrence_date)::integer - 1
          AND start_time <= v_now_time AND end_time >= v_now_time
        ORDER BY start_time LIMIT 1 FOR UPDATE;

        IF FOUND THEN
            INSERT INTO public.schedule_occurrences
                (schedule_id, child_id, occurrence_date, status, completed_at)
            VALUES (v_schedule.id, p_child_id, v_occurrence_date, 'done', v_now)
            ON CONFLICT (schedule_id, occurrence_date) DO UPDATE
            SET status = 'done', completed_at = EXCLUDED.completed_at;
        END IF;

        IF p_analysis_type = 'food' THEN
            INSERT INTO public.food_logs (
                child_id, logged_by, meal_schedule_id, meal_type, food_name,
                portion_size, portion_grams, calories, photo_url, nutrition,
                is_healthy, analysis_id, consumed_at
            ) VALUES (
                p_child_id, p_child_id, v_schedule.id, 'snack',
                COALESCE(v_draft.payload->>'foodName', 'Food'),
                p_portion_grams::text || ' g', p_portion_grams,
                round(v_calories), v_draft.image_url, p_nutrition,
                p_is_healthy, p_analysis_id, v_now
            ) RETURNING food_logs.id, to_jsonb(food_logs) INTO v_history_id, v_history;

            SELECT COALESCE(target_daily_calories / 3, 500) INTO v_target
            FROM public.clinical_parameters WHERE child_id = p_child_id
            ORDER BY created_at DESC LIMIT 1;
            v_target := COALESCE(v_target, 500);
            IF NOT p_is_healthy THEN
                v_exp_delta := 0; v_happiness_delta := -20; v_hunger_delta := 20;
            ELSIF v_calories <= v_target * 1.15 THEN
                v_exp_delta := 15; v_happiness_delta := 15; v_hunger_delta := 30;
            ELSE
                v_exp_delta := 5; v_happiness_delta := -5; v_hunger_delta := 20;
            END IF;
        ELSE
            INSERT INTO public.medication_logs (
                child_id, administered_by, medication_name, dosage, dosage_unit,
                route, scheduled_time, was_taken, analysis_id, photo_url,
                is_medicine, status, administered_at
            ) VALUES (
                p_child_id, p_child_id,
                COALESCE(v_draft.payload->'detected'->>'detected', 'Medicine'),
                1, 'unit', 'oral', v_now_time, true, p_analysis_id,
                v_draft.image_url, true, 'done', v_now
            ) RETURNING medication_logs.id, to_jsonb(medication_logs) INTO v_history_id, v_history;
            v_exp_delta := 20; v_happiness_delta := 15; v_hunger_delta := 0;
        END IF;

        SELECT * INTO v_pet FROM public.virtual_pets WHERE child_id = p_child_id FOR UPDATE;
        IF NOT FOUND THEN
            INSERT INTO public.virtual_pets (child_id, pet_name, pet_type)
            VALUES (p_child_id, 'Buddy', 'dog') RETURNING * INTO v_pet;
        END IF;
        v_previous_level := v_pet.level;
        UPDATE public.virtual_pets SET
            experience_points = (v_pet.experience_points + v_exp_delta) % 100,
            level = v_pet.level + floor((v_pet.experience_points + v_exp_delta)::numeric / 100)::integer,
            happiness = greatest(0, least(100, v_pet.happiness + v_happiness_delta)),
            hunger = greatest(0, least(100, v_pet.hunger + v_hunger_delta)),
            is_active = true
        WHERE id = v_pet.id RETURNING * INTO v_pet;

        IF p_analysis_type = 'food' AND NOT p_is_healthy THEN
            INSERT INTO public.alerts (child_id, type, sender_type, title, message, is_read, created_at)
            VALUES (
                p_child_id, 'food_warning', 'pet', 'BiteBuddy',
                'Waduh, makanan ini kurang sehat! Peliharaanmu jadi sedih dan sakit.', false, v_now
            );
        END IF;
        IF v_pet.level > v_previous_level THEN
            INSERT INTO public.alerts (child_id, type, sender_type, title, message, is_read, created_at)
            VALUES (
                p_child_id, 'level_up', 'pet', 'BiteBuddy',
                'Hore! Peliharaanmu naik ke level ' || v_pet.level || '!', false, v_now
            );
        END IF;

        UPDATE public.analysis_drafts SET
            status = 'confirmed', confirmed_history_id = v_history_id, confirmed_at = v_now
        WHERE id = p_analysis_id;

        INSERT INTO public.activity_logs
            (user_id, action, entity_type, entity_id, metadata, created_at, wib_month)
        VALUES (
            p_child_id, p_analysis_type || '.confirm', p_analysis_type || '_log', v_history_id,
            jsonb_build_object(
                'role', 'child', 'child_id', p_child_id,
                'description', 'Confirmed ' || p_analysis_type || ' analysis.',
                'outcome', 'success'
            ), v_now, to_char(v_now AT TIME ZONE 'Asia/Jakarta', 'YYYY-MM')
        );
    END IF;

    WITH completed_days AS (
        SELECT DISTINCT (consumed_at AT TIME ZONE 'Asia/Jakarta')::date AS day
        FROM public.food_logs WHERE child_id = p_child_id
          AND consumed_at >= v_now - interval '90 days'
    ), offsets AS (
        SELECT generate_series(0, 89) AS offset_days
    )
    SELECT COALESCE(min(offset_days) FILTER (
        WHERE NOT EXISTS (
            SELECT 1 FROM completed_days
            WHERE day = v_occurrence_date - offset_days
        )
    ), 90) INTO v_streak FROM offsets;

    SELECT * INTO v_pet FROM public.virtual_pets WHERE child_id = p_child_id;
    RETURN jsonb_build_object(
        'history', v_history,
        'affectedSchedule', CASE WHEN v_schedule.id IS NULL THEN NULL ELSE
            jsonb_build_object('id', v_schedule.id, 'status', 'done') END,
        'pet', jsonb_build_object(
            'level', v_pet.level,
            'hp', round(((v_pet.happiness + v_pet.hunger)::numeric / 200), 2),
            'xp', round((v_pet.experience_points::numeric / 100), 2)
        ),
        'streakDays', v_streak
    );
END $$;

REVOKE ALL ON FUNCTION public.confirm_child_analysis(UUID, UUID, TEXT, NUMERIC, JSONB, BOOLEAN) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.confirm_child_analysis(UUID, UUID, TEXT, NUMERIC, JSONB, BOOLEAN) TO service_role;
