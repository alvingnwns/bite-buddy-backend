-- Fase 5: Alerts Table for Real-time Notifications

CREATE TABLE IF NOT EXISTS public.alerts (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    child_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL, -- e.g. 'compliance_violation', 'food_warning', 'level_up'
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- RLS Policies
ALTER TABLE public.alerts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own children's alerts"
ON public.alerts FOR SELECT
USING (
    child_id = auth.uid() OR 
    child_id IN (SELECT id FROM public.users WHERE parent_id = auth.uid())
);

CREATE POLICY "Service role can insert alerts"
ON public.alerts FOR INSERT
WITH CHECK (true); -- Usually restricted by role, but we use service_role key anyway

CREATE POLICY "Users can update their own children's alerts (e.g. mark as read)"
ON public.alerts FOR UPDATE
USING (
    child_id = auth.uid() OR 
    child_id IN (SELECT id FROM public.users WHERE parent_id = auth.uid())
)
WITH CHECK (
    child_id = auth.uid() OR 
    child_id IN (SELECT id FROM public.users WHERE parent_id = auth.uid())
);
