-- Row Level Security (RLS) Policies for BiteBuddy
-- Auto-generated from rls_policies.md

-- 1. Users Table
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

CREATE POLICY users_select_own ON users
    FOR SELECT USING (id = auth.uid());

CREATE POLICY users_select_family ON users
    FOR SELECT USING (
        parent_id = auth.uid()
        OR doctor_id = auth.uid()
        OR id IN (SELECT parent_id FROM users WHERE id = auth.uid())
        OR id IN (SELECT doctor_id FROM users WHERE id = auth.uid())
    );

CREATE POLICY users_insert_own ON users
    FOR INSERT WITH CHECK (id = auth.uid());

CREATE POLICY users_update_own ON users
    FOR UPDATE USING (id = auth.uid())
    WITH CHECK (id = auth.uid());

CREATE POLICY users_update_as_parent ON users
    FOR UPDATE USING (parent_id = auth.uid())
    WITH CHECK (parent_id = auth.uid());


-- 2. Clinical Parameters Table
ALTER TABLE clinical_parameters ENABLE ROW LEVEL SECURITY;

CREATE POLICY clinical_select ON clinical_parameters
    FOR SELECT USING (
        child_id IN (SELECT id FROM users WHERE parent_id = auth.uid())
        OR child_id IN (SELECT id FROM users WHERE doctor_id = auth.uid())
        OR child_id = auth.uid()
    );

CREATE POLICY clinical_insert ON clinical_parameters
    FOR INSERT WITH CHECK (
        child_id IN (SELECT id FROM users WHERE parent_id = auth.uid())
        OR child_id IN (SELECT id FROM users WHERE doctor_id = auth.uid())
    );

CREATE POLICY clinical_update ON clinical_parameters
    FOR UPDATE USING (
        child_id IN (SELECT id FROM users WHERE parent_id = auth.uid())
        OR child_id IN (SELECT id FROM users WHERE doctor_id = auth.uid())
    );


-- 3. Custom Meal Schedules Table
ALTER TABLE custom_meal_schedules ENABLE ROW LEVEL SECURITY;

CREATE POLICY meal_schedules_select ON custom_meal_schedules
    FOR SELECT USING (
        child_id = auth.uid()
        OR child_id IN (SELECT id FROM users WHERE parent_id = auth.uid())
        OR created_by = auth.uid()
    );

CREATE POLICY meal_schedules_insert ON custom_meal_schedules
    FOR INSERT WITH CHECK (
        child_id IN (SELECT id FROM users WHERE parent_id = auth.uid())
        OR child_id IN (SELECT id FROM users WHERE doctor_id = auth.uid())
    );

CREATE POLICY meal_schedules_update ON custom_meal_schedules
    FOR UPDATE USING (
        child_id IN (SELECT id FROM users WHERE parent_id = auth.uid())
    );

CREATE POLICY meal_schedules_delete ON custom_meal_schedules
    FOR DELETE USING (
        child_id IN (SELECT id FROM users WHERE parent_id = auth.uid())
    );


-- 4. Virtual Pets Table
ALTER TABLE virtual_pets ENABLE ROW LEVEL SECURITY;

CREATE POLICY virtual_pets_select ON virtual_pets
    FOR SELECT USING (
        child_id = auth.uid()
        OR child_id IN (SELECT id FROM users WHERE parent_id = auth.uid())
    );

CREATE POLICY virtual_pets_insert ON virtual_pets
    FOR INSERT WITH CHECK (child_id = auth.uid());

CREATE POLICY virtual_pets_update ON virtual_pets
    FOR UPDATE USING (child_id = auth.uid())
    WITH CHECK (child_id = auth.uid());


-- 5. Food Logs Table
ALTER TABLE food_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY food_logs_select ON food_logs
    FOR SELECT USING (
        child_id = auth.uid()
        OR child_id IN (SELECT id FROM users WHERE parent_id = auth.uid())
        OR logged_by = auth.uid()
    );

CREATE POLICY food_logs_insert ON food_logs
    FOR INSERT WITH CHECK (
        logged_by = auth.uid()
        AND (
            child_id = auth.uid()
            OR child_id IN (SELECT id FROM users WHERE parent_id = auth.uid())
        )
    );

CREATE POLICY food_logs_update ON food_logs
    FOR UPDATE USING (
        child_id IN (SELECT id FROM users WHERE parent_id = auth.uid())
    );

CREATE POLICY food_logs_delete ON food_logs
    FOR DELETE USING (
        child_id IN (SELECT id FROM users WHERE parent_id = auth.uid())
    );


-- 6. Medication Logs Table
ALTER TABLE medication_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY medication_logs_select ON medication_logs
    FOR SELECT USING (
        child_id = auth.uid()
        OR child_id IN (SELECT id FROM users WHERE parent_id = auth.uid())
        OR administered_by = auth.uid()
    );

CREATE POLICY medication_logs_insert ON medication_logs
    FOR INSERT WITH CHECK (
        administered_by = auth.uid()
        AND child_id IN (SELECT id FROM users WHERE parent_id = auth.uid())
    );

CREATE POLICY medication_logs_update ON medication_logs
    FOR UPDATE USING (
        child_id IN (SELECT id FROM users WHERE parent_id = auth.uid())
    );
