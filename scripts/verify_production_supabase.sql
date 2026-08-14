-- Read-only production audit. Run in Supabase SQL Editor after migrations 001-020.

WITH required_tables(name) AS (
    VALUES
        ('users'), ('clinical_parameters'), ('custom_meal_schedules'),
        ('virtual_pets'), ('food_logs'), ('medication_logs'), ('alerts'),
        ('nutrition_database'), ('activity_logs'), ('analysis_drafts'),
        ('schedule_occurrences'), ('patient_invitations'),
        ('doctor_patient_profiles'), ('blood_glucose_records'),
        ('doctor_appointments'), ('doctor_diagnoses'), ('doctor_notifications')
)
SELECT 'missing_table' AS check_name, name AS detail
FROM required_tables
WHERE to_regclass('public.' || name) IS NULL
ORDER BY name;

WITH required_functions(name) AS (
    VALUES
        ('claim_patient_invitation'), ('doctor_create_blood_glucose'),
        ('doctor_create_appointment'), ('doctor_create_diagnosis'),
        ('doctor_create_notification'), ('confirm_child_analysis'),
        ('sync_doctor_medication_schedules')
)
SELECT 'missing_function' AS check_name, required.name AS detail
FROM required_functions AS required
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_proc
    JOIN pg_namespace ON pg_namespace.oid = pg_proc.pronamespace
    WHERE pg_namespace.nspname = 'public' AND pg_proc.proname = required.name
)
ORDER BY required.name;

WITH rls_tables(name) AS (
    VALUES
        ('users'), ('clinical_parameters'), ('custom_meal_schedules'),
        ('virtual_pets'), ('food_logs'), ('medication_logs'), ('alerts'),
        ('activity_logs'), ('patient_invitations'), ('doctor_patient_profiles'),
        ('blood_glucose_records'), ('doctor_appointments'),
        ('doctor_diagnoses'), ('doctor_notifications')
)
SELECT 'rls_disabled' AS check_name, required.name AS detail
FROM rls_tables AS required
JOIN pg_class ON pg_class.relname = required.name
JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace
WHERE pg_namespace.nspname = 'public' AND NOT pg_class.relrowsecurity
ORDER BY required.name;

WITH required_buckets(id) AS (
    VALUES ('food-photos'), ('medicine-photos')
)
SELECT 'missing_bucket' AS check_name, required.id AS detail
FROM required_buckets AS required
LEFT JOIN storage.buckets ON storage.buckets.id = required.id
WHERE storage.buckets.id IS NULL
ORDER BY required.id;

SELECT 'storage_policy_count' AS check_name, count(*)::text AS detail
FROM pg_policies
WHERE schemaname = 'storage' AND tablename = 'objects';

SELECT 'activity_partition' AS check_name, child.relname AS detail
FROM pg_inherits
JOIN pg_class AS parent ON parent.oid = pg_inherits.inhparent
JOIN pg_class AS child ON child.oid = pg_inherits.inhrelid
JOIN pg_namespace ON pg_namespace.oid = parent.relnamespace
WHERE pg_namespace.nspname = 'public' AND parent.relname = 'activity_logs'
ORDER BY child.relname;

SELECT 'nutrition_row_count' AS check_name, count(*)::text AS detail
FROM public.nutrition_database;

SELECT 'latest_activity_wib_month' AS check_name,
       COALESCE(max(wib_month), 'no activity yet') AS detail
FROM public.activity_logs;
