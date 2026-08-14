-- Read-only production audit. Run as one statement in Supabase SQL Editor.

WITH
required_tables(name) AS (
    VALUES
        ('users'), ('clinical_parameters'), ('custom_meal_schedules'),
        ('virtual_pets'), ('food_logs'), ('medication_logs'), ('alerts'),
        ('nutrition_database'), ('activity_logs'), ('analysis_drafts'),
        ('schedule_occurrences'), ('patient_invitations'),
        ('doctor_patient_profiles'), ('blood_glucose_records'),
        ('doctor_appointments'), ('doctor_diagnoses'), ('doctor_notifications')
),
required_functions(name) AS (
    VALUES
        ('claim_patient_invitation'), ('doctor_create_blood_glucose'),
        ('doctor_create_appointment'), ('doctor_create_diagnosis'),
        ('doctor_create_notification'), ('confirm_child_analysis'),
        ('sync_doctor_medication_schedules')
),
rls_tables(name) AS (
    VALUES
        ('users'), ('clinical_parameters'), ('custom_meal_schedules'),
        ('virtual_pets'), ('food_logs'), ('medication_logs'), ('alerts'),
        ('activity_logs'), ('patient_invitations'), ('doctor_patient_profiles'),
        ('blood_glucose_records'), ('doctor_appointments'),
        ('doctor_diagnoses'), ('doctor_notifications')
),
required_buckets(id) AS (
    VALUES ('food-photos'), ('medicine-photos')
),
audit AS (
    SELECT
        'tables' AS check_name,
        COALESCE(
            'MISSING: ' || string_agg(name, ', ' ORDER BY name),
            'OK'
        ) AS detail
    FROM required_tables
    WHERE to_regclass('public.' || name) IS NULL

    UNION ALL

    SELECT
        'functions',
        COALESCE(
            'MISSING: ' || string_agg(required.name, ', ' ORDER BY required.name),
            'OK'
        )
    FROM required_functions AS required
    WHERE NOT EXISTS (
        SELECT 1
        FROM pg_proc
        JOIN pg_namespace ON pg_namespace.oid = pg_proc.pronamespace
        WHERE pg_namespace.nspname = 'public'
          AND pg_proc.proname = required.name
    )

    UNION ALL

    SELECT
        'rls',
        COALESCE(
            'DISABLED: ' || string_agg(required.name, ', ' ORDER BY required.name),
            'OK'
        )
    FROM rls_tables AS required
    JOIN pg_class ON pg_class.relname = required.name
    JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace
    WHERE pg_namespace.nspname = 'public'
      AND NOT pg_class.relrowsecurity

    UNION ALL

    SELECT
        'storage_buckets',
        COALESCE(
            'MISSING: ' || string_agg(required.id, ', ' ORDER BY required.id),
            'OK'
        )
    FROM required_buckets AS required
    LEFT JOIN storage.buckets ON storage.buckets.id = required.id
    WHERE storage.buckets.id IS NULL

    UNION ALL

    SELECT
        'storage_policy_count',
        count(*)::text
    FROM pg_policies
    WHERE schemaname = 'storage' AND tablename = 'objects'

    UNION ALL

    SELECT
        'activity_partitions',
        COALESCE(string_agg(child.relname, ', ' ORDER BY child.relname), 'MISSING')
    FROM pg_inherits
    JOIN pg_class AS parent ON parent.oid = pg_inherits.inhparent
    JOIN pg_class AS child ON child.oid = pg_inherits.inhrelid
    JOIN pg_namespace ON pg_namespace.oid = parent.relnamespace
    WHERE pg_namespace.nspname = 'public' AND parent.relname = 'activity_logs'

    UNION ALL

    SELECT 'nutrition_row_count', count(*)::text
    FROM public.nutrition_database

    UNION ALL

    SELECT
        'latest_activity_wib_month',
        COALESCE(max(wib_month), 'no activity yet')
    FROM public.activity_logs
)
SELECT check_name, detail
FROM audit
ORDER BY check_name;
