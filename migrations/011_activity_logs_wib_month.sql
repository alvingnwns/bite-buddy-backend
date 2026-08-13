-- Add the authoritative Asia/Jakarta month index used by monthly audit searches.
-- Apply after 010_doctor_auth_profile.sql.

ALTER TABLE public.activity_logs
    ADD COLUMN IF NOT EXISTS wib_month VARCHAR(7);

-- Public authentication attempts may not have a canonical user yet.
ALTER TABLE public.activity_logs
    ALTER COLUMN user_id DROP NOT NULL;

UPDATE public.activity_logs
SET wib_month = to_char(created_at AT TIME ZONE 'Asia/Jakarta', 'YYYY-MM')
WHERE wib_month IS NULL;

ALTER TABLE public.activity_logs
    ALTER COLUMN wib_month SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_activity_logs_wib_month
    ON public.activity_logs (wib_month, created_at DESC);

COMMENT ON COLUMN public.activity_logs.wib_month IS
    'Authoritative YYYY-MM bucket derived using Asia/Jakarta (GMT+7).';
