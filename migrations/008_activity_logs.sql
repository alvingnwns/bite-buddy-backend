-- Create partitioned activity_logs table
CREATE TABLE IF NOT EXISTS public.activity_logs (
    id UUID DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    action VARCHAR(255) NOT NULL, -- e.g., 'login', 'create', 'update', 'delete', 'confirm'
    entity_type VARCHAR(255) NOT NULL, -- e.g., 'food_log', 'medication_log', 'user'
    entity_id UUID,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Create partitions for MVP months
CREATE TABLE IF NOT EXISTS public.activity_logs_2026_08 PARTITION OF public.activity_logs
    FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');

CREATE TABLE IF NOT EXISTS public.activity_logs_2026_09 PARTITION OF public.activity_logs
    FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');

CREATE TABLE IF NOT EXISTS public.activity_logs_2026_10 PARTITION OF public.activity_logs
    FOR VALUES FROM ('2026-10-01') TO ('2026-11-01');
    
CREATE TABLE IF NOT EXISTS public.activity_logs_2026_11 PARTITION OF public.activity_logs
    FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');

CREATE TABLE IF NOT EXISTS public.activity_logs_2026_12 PARTITION OF public.activity_logs
    FOR VALUES FROM ('2026-12-01') TO ('2027-01-01');

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_activity_logs_user_id ON public.activity_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_created_at ON public.activity_logs(created_at);

-- RLS
ALTER TABLE public.activity_logs ENABLE ROW LEVEL SECURITY;

-- Admins / Users can see their own logs
CREATE POLICY "Users can view their own activity logs"
    ON public.activity_logs FOR SELECT
    USING (auth.uid() = user_id OR 
           auth.uid() IN (SELECT id FROM public.users WHERE parent_id = auth.uid()));

CREATE POLICY "System can insert activity logs"
    ON public.activity_logs FOR INSERT
    WITH CHECK (true); -- Usually inserted by service_role
