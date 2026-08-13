-- Finalize game rules after 017. Apply in WIB deployment order.

DO $$
BEGIN
    IF to_regprocedure('public.confirm_child_analysis_v017(uuid,uuid,text,numeric,jsonb,boolean)') IS NULL THEN
        ALTER FUNCTION public.confirm_child_analysis(UUID, UUID, TEXT, NUMERIC, JSONB, BOOLEAN)
            RENAME TO confirm_child_analysis_v017;
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
    v_draft public.analysis_drafts;
    v_pet public.virtual_pets;
    v_result JSONB;
    v_previous_level INTEGER := 1;
    v_previous_exp INTEGER := 0;
    v_previous_happiness INTEGER := 100;
    v_previous_hunger INTEGER := 100;
    v_threshold INTEGER;
    v_started_at TIMESTAMPTZ := clock_timestamp();
BEGIN
    -- Serialize by draft before touching the pet. A concurrent retry must not award twice.
    SELECT * INTO v_draft
    FROM public.analysis_drafts
    WHERE id = p_analysis_id AND analysis_type = p_analysis_type
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'analysis_not_found' USING ERRCODE = 'P0002';
    END IF;
    IF v_draft.child_id <> p_child_id THEN
        RAISE EXCEPTION 'analysis_forbidden' USING ERRCODE = '42501';
    END IF;

    IF v_draft.status = 'confirmed' THEN
        v_result := public.confirm_child_analysis_legacy(
            p_child_id, p_analysis_id, p_analysis_type,
            p_portion_grams, p_nutrition, p_is_healthy
        );
        SELECT * INTO v_pet FROM public.virtual_pets WHERE child_id = p_child_id;
        v_threshold := (100 * v_pet.level) + 150;
        RETURN jsonb_set(
            jsonb_set(
                jsonb_set(v_result, '{pet,level}', to_jsonb(v_pet.level), true),
                '{pet,hp}', to_jsonb(round(((v_pet.happiness + v_pet.hunger)::numeric / 200), 2)), true
            ),
            '{pet,xp}', to_jsonb(round((v_pet.experience_points::numeric / v_threshold), 2)), true
        );
    END IF;

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

    v_result := public.confirm_child_analysis_v017(
        p_child_id, p_analysis_id, p_analysis_type,
        p_portion_grams, p_nutrition, p_is_healthy
    );

    -- The requested game contract awards XP/HP for healthy food only.
    IF p_analysis_type = 'medicine' THEN
        UPDATE public.virtual_pets
        SET level = v_previous_level,
            experience_points = v_previous_exp,
            happiness = v_previous_happiness,
            hunger = v_previous_hunger,
            is_active = true
        WHERE child_id = p_child_id
        RETURNING * INTO v_pet;

        v_threshold := (100 * v_previous_level) + 150;
        v_result := jsonb_set(
            jsonb_set(
                jsonb_set(v_result, '{pet,level}', to_jsonb(v_previous_level), true),
                '{pet,hp}', to_jsonb(round(((v_previous_happiness + v_previous_hunger)::numeric / 200), 2)), true
            ),
            '{pet,xp}', to_jsonb(round((v_previous_exp::numeric / v_threshold), 2)), true
        );
        DELETE FROM public.alerts
        WHERE child_id = p_child_id
          AND type = 'level_up'
          AND created_at >= v_started_at;
    END IF;

    -- Alerts must target the child account so the warning is visible in the app.
    UPDATE public.alerts
    SET recipient_user_id = p_child_id
    WHERE child_id = p_child_id
      AND recipient_user_id IS NULL
      AND created_at >= v_started_at;

    RETURN v_result;
END $$;

REVOKE ALL ON FUNCTION public.confirm_child_analysis(UUID, UUID, TEXT, NUMERIC, JSONB, BOOLEAN) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.confirm_child_analysis(UUID, UUID, TEXT, NUMERIC, JSONB, BOOLEAN) TO service_role;
