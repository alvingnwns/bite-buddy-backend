# Row Level Security (RLS) Policies for BiteBuddy

## Overview

Supabase uses PostgreSQL's Row Level Security to restrict access to data based on the authenticated user's role and relationships. Below are the RLS policies for each table.

---

## 1. Users Table

| Policy Name | Operation | Role | Policy Expression |
|---|---|---|---|
| `users_select_own` | SELECT | authenticated | `id = auth.uid()` |
| `users_select_parents_children` | SELECT | authenticated | `parent_id = auth.uid()` OR `id IN (SELECT parent_id FROM users WHERE id = auth.uid())` |
| `users_select_doctors_patients` | SELECT | authenticated | `doctor_id = auth.uid()` OR `id IN (SELECT doctor_id FROM users WHERE id = auth.uid())` |
| `users_insert` | INSERT | authenticated | `id = auth.uid()` (user can only insert their own record) |
| `users_update_own` | UPDATE | authenticated | `id = auth.uid()` |
| `users_update_parent_child` | UPDATE | authenticated (parent) | `id IN (SELECT id FROM users WHERE parent_id = auth.uid())` |
| `users_delete` | DELETE | service_role only | No public deletion |

**SQL Implementation:**
```sql
-- Enable RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Select policies
CREATE POLICY users_select_own ON users
    FOR SELECT USING (id = auth.uid());

CREATE POLICY users_select_family ON users
    FOR SELECT USING (
        parent_id = auth.uid()
        OR doctor_id = auth.uid()
        OR id IN (SELECT parent_id FROM users WHERE id = auth.uid())
        OR id IN (SELECT doctor_id FROM users WHERE id = auth.uid())
    );

-- Insert policy (only self-registration)
CREATE POLICY users_insert_own ON users
    FOR INSERT WITH CHECK (id = auth.uid());

-- Update policies
CREATE POLICY users_update_own ON users
    FOR UPDATE USING (id = auth.uid())
    WITH CHECK (id = auth.uid());

CREATE POLICY users_update_as_parent ON users
    FOR UPDATE USING (parent_id = auth.uid())
    WITH CHECK (parent_id = auth.uid());
```

---

## 2. Clinical Parameters Table

| Policy Name | Operation | Role | Policy Expression |
|---|---|---|---|
| `clinical_select_parent` | SELECT | authenticated (parent) | `child_id IN (SELECT id FROM users WHERE parent_id = auth.uid())` |
| `clinical_select_doctor` | SELECT | authenticated (doctor) | `child_id IN (SELECT id FROM users WHERE doctor_id = auth.uid())` |
| `clinical_insert_parent` | INSERT | authenticated (parent/doctor) | `child_id IN (SELECT id FROM users WHERE parent_id = auth.uid() OR doctor_id = auth.uid())` |
| `clinical_update` | UPDATE | authenticated (parent/doctor) | Same as insert |
| `clinical_delete` | DELETE | service_role only | No public deletion |

**SQL Implementation:**
```sql
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
```

---

## 3. Custom Meal Schedules Table

| Policy Name | Operation | Role | Policy Expression |
|---|---|---|---|
| `meal_schedules_select` | SELECT | authenticated | `child_id IN (SELECT id FROM users WHERE parent_id = auth.uid())` OR `child_id = auth.uid()` |
| `meal_schedules_insert` | INSERT | authenticated (parent/doctor) | `child_id IN (SELECT id FROM users WHERE parent_id = auth.uid())` |
| `meal_schedules_update` | UPDATE | authenticated (parent/doctor) | Same as insert |
| `meal_schedules_delete` | DELETE | authenticated (parent) | `child_id IN (SELECT id FROM users WHERE parent_id = auth.uid())` |

**SQL Implementation:**
```sql
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
```

---

## 4. Virtual Pets Table

| Policy Name | Operation | Role | Policy Expression |
|---|---|---|---|
| `virtual_pets_select` | SELECT | authenticated | `child_id = auth.uid()` OR `child_id IN (SELECT id FROM users WHERE parent_id = auth.uid())` |
| `virtual_pets_insert` | INSERT | authenticated | `child_id = auth.uid()` (child creates own pet) |
| `virtual_pets_update` | UPDATE | authenticated | `child_id = auth.uid()` (child updates own pet) |
| `virtual_pets_delete` | DELETE | service_role only | No public deletion |

**SQL Implementation:**
```sql
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
```

---

## 5. Food Logs Table

| Policy Name | Operation | Role | Policy Expression |
|---|---|---|---|
| `food_logs_select` | SELECT | authenticated | `child_id = auth.uid()` OR `child_id IN (SELECT id FROM users WHERE parent_id = auth.uid())` OR `logged_by = auth.uid()` |
| `food_logs_insert` | INSERT | authenticated | `logged_by = auth.uid()` AND (`child_id = auth.uid()` OR `child_id IN (SELECT id FROM users WHERE parent_id = auth.uid())`) |
| `food_logs_update` | UPDATE | authenticated (parent) | `child_id IN (SELECT id FROM users WHERE parent_id = auth.uid())` |
| `food_logs_delete` | DELETE | authenticated (parent) | `child_id IN (SELECT id FROM users WHERE parent_id = auth.uid())` |

**SQL Implementation:**
```sql
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
```

---

## 6. Medication Logs Table

| Policy Name | Operation | Role | Policy Expression |
|---|---|---|---|
| `medication_logs_select` | SELECT | authenticated | `child_id = auth.uid()` OR `child_id IN (SELECT id FROM users WHERE parent_id = auth.uid())` OR `administered_by = auth.uid()` |
| `medication_logs_insert` | INSERT | authenticated (parent) | `administered_by = auth.uid()` AND `child_id IN (SELECT id FROM users WHERE parent_id = auth.uid())` |
| `medication_logs_update` | UPDATE | authenticated (parent) | `child_id IN (SELECT id FROM users WHERE parent_id = auth.uid())` |
| `medication_logs_delete` | DELETE | service_role only | No public deletion |

**SQL Implementation:**
```sql
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
```

---

## Summary of Access Patterns

| Role | Can Read | Can Write |
|---|---|---|
| **Child** | Own profile, own pet, own food/medication logs, own meal schedules | Own pet, own food logs |
| **Parent** | Own profile + children's profiles, clinical data, food logs, medication logs, meal schedules | Children's clinical data, meal schedules, food/medication logs |
| **Doctor** | Patient profiles, clinical data | Clinical data (read-only for logs) |
| **Service Role** (backend) | Full access (bypasses RLS) | Full access (bypasses RLS) |

> **Note:** RLS policies use `auth.uid()` which is automatically populated by Supabase Auth with the currently authenticated user's ID. The service role key should be used only for trusted backend operations and should never be exposed to the client.