-- Food-analysis corrections and level-aware pet progression (WIB deployment).

DO $$
BEGIN
    IF to_regprocedure('public.confirm_child_analysis_legacy(uuid,uuid,text,numeric,jsonb,boolean)') IS NULL THEN
        ALTER FUNCTION public.confirm_child_analysis(UUID, UUID, TEXT, NUMERIC, JSONB, BOOLEAN)
            RENAME TO confirm_child_analysis_legacy;
    END IF;
END $$;

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
    v_result JSONB;
    v_pet public.virtual_pets;
    v_previous_level INTEGER := 1;
    v_previous_exp INTEGER := 0;
    v_previous_happiness INTEGER := 100;
    v_previous_hunger INTEGER := 100;
    v_level INTEGER;
    v_exp INTEGER;
    v_threshold INTEGER;
    v_exp_gain INTEGER;
    v_hp_delta INTEGER;
    v_started_at TIMESTAMPTZ := clock_timestamp();
BEGIN
    SELECT * INTO v_pet
    FROM public.virtual_pets
    WHERE child_id = p_child_id
    FOR UPDATE;

    IF FOUND THEN
        v_previous_level := v_pet.level;
        v_previous_exp := v_pet.experience_points;
        v_previous_happiness := v_pet.happiness;
        v_previous_hunger := v_pet.hunger;
    END IF;

    v_result := public.confirm_child_analysis_legacy(
        p_child_id, p_analysis_id, p_analysis_type,
        p_portion_grams, p_nutrition, p_is_healthy
    );

    IF p_analysis_type <> 'food' THEN
        RETURN v_result;
    END IF;

    v_level := v_previous_level;
    v_exp := v_previous_exp;
    v_exp_gain := round((v_level * 1.5) + (10 * v_level));
    v_exp := v_exp + v_exp_gain;
    v_threshold := (100 * v_level) + 150;

    WHILE v_exp >= v_threshold LOOP
        v_exp := v_exp - v_threshold;
        v_level := v_level + 1;
        v_threshold := (100 * v_level) + 150;
    END LOOP;

    v_hp_delta := CASE WHEN p_is_healthy THEN 5 ELSE -15 END;

    UPDATE public.virtual_pets
    SET experience_points = v_exp,
        level = v_level,
        happiness = greatest(0, least(100, v_previous_happiness + v_hp_delta)),
        hunger = greatest(0, least(100, v_previous_hunger + v_hp_delta)),
        is_active = true
    WHERE child_id = p_child_id
    RETURNING * INTO v_pet;

    -- Remove a level-up alert produced by the legacy fixed-100 threshold.
    DELETE FROM public.alerts
    WHERE child_id = p_child_id
      AND type = 'level_up'
      AND created_at >= v_started_at;

    IF v_level > v_previous_level THEN
        INSERT INTO public.alerts (
            child_id, recipient_user_id, type, sender_type,
            title, message, is_read, created_at
        ) VALUES (
            p_child_id, p_child_id, 'level_up', 'pet', 'BiteBuddy',
            'Hore! Peliharaanmu naik ke level ' || v_level || '!', false, now()
        );
    END IF;

    RETURN jsonb_set(
        jsonb_set(
            jsonb_set(v_result, '{pet,level}', to_jsonb(v_level), true),
            '{pet,hp}', to_jsonb(round(((v_pet.happiness + v_pet.hunger)::numeric / 200), 2)), true
        ),
        '{pet,xp}', to_jsonb(round((v_exp::numeric / v_threshold), 2)), true
    );
END $$;

REVOKE ALL ON FUNCTION public.confirm_child_analysis(UUID, UUID, TEXT, NUMERIC, JSONB, BOOLEAN) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.confirm_child_analysis(UUID, UUID, TEXT, NUMERIC, JSONB, BOOLEAN) TO service_role;

