-- Enforce BUGS #7: only low/medium-sugar food earns XP; unhealthy food only loses HP.

DO $$
BEGIN
    IF to_regprocedure('public.confirm_child_analysis_v018(uuid,uuid,text,numeric,jsonb,boolean)') IS NULL THEN
        ALTER FUNCTION public.confirm_child_analysis(UUID, UUID, TEXT, NUMERIC, JSONB, BOOLEAN)
            RENAME TO confirm_child_analysis_v018;
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
    v_threshold INTEGER;
    v_started_at TIMESTAMPTZ := clock_timestamp();
BEGIN
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

    SELECT * INTO v_pet
    FROM public.virtual_pets
    WHERE child_id = p_child_id
    FOR UPDATE;
    IF FOUND THEN
        v_previous_level := v_pet.level;
        v_previous_exp := v_pet.experience_points;
    END IF;

    v_result := public.confirm_child_analysis_v018(
        p_child_id, p_analysis_id, p_analysis_type,
        p_portion_grams, p_nutrition, p_is_healthy
    );

    -- Migration 017 applied XP to every food. Restore XP for a first unhealthy confirmation;
    -- the -15 HP and warning created by the wrapped function remain unchanged.
    IF v_draft.status <> 'confirmed'
       AND p_analysis_type = 'food' AND NOT p_is_healthy THEN
        UPDATE public.virtual_pets
        SET level = v_previous_level,
            experience_points = v_previous_exp
        WHERE child_id = p_child_id
        RETURNING * INTO v_pet;

        v_threshold := (100 * v_previous_level) + 150;
        v_result := jsonb_set(
            jsonb_set(v_result, '{pet,level}', to_jsonb(v_previous_level), true),
            '{pet,xp}', to_jsonb(round((v_previous_exp::numeric / v_threshold), 2)), true
        );

        DELETE FROM public.alerts
        WHERE child_id = p_child_id
          AND type = 'level_up'
          AND created_at >= v_started_at;
    END IF;

    RETURN v_result;
END $$;

REVOKE ALL ON FUNCTION public.confirm_child_analysis(UUID, UUID, TEXT, NUMERIC, JSONB, BOOLEAN) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.confirm_child_analysis(UUID, UUID, TEXT, NUMERIC, JSONB, BOOLEAN) TO service_role;
