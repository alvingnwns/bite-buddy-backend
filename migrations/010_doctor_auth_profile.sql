-- Doctor authentication/profile foundation.
-- Apply after 009_full_non_doctor_integration.sql.

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS address TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_doctor_code_ci
    ON public.users (lower(doctor_code))
    WHERE doctor_code IS NOT NULL;

COMMENT ON COLUMN public.users.address IS
    'User-facing address; Doctor registration currently requires this field.';
