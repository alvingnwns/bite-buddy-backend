-- 003_spec_fixes.sql
-- Migration for adding necessary columns based on Phase 1-4 Code Review and Spec checks.

-- 1. Add time window columns to custom_meal_schedules
-- We need to know when the meal is expected (e.g., 07:00:00 to 09:00:00) 
-- so the compliance worker can penalize if the end_time has passed without food log.
ALTER TABLE public.custom_meal_schedules
ADD COLUMN start_time TIME,
ADD COLUMN end_time TIME;

-- 2. Add target nutrition columns to clinical_parameters
-- Gamification engine needs these to evaluate if a meal's calories match the child's medical targets.
ALTER TABLE public.clinical_parameters
ADD COLUMN target_daily_calories INT,
ADD COLUMN target_daily_carbs FLOAT;
