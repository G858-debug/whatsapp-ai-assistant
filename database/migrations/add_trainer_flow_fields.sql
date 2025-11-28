-- Migration: Add missing fields for trainer flow data
-- Date: 2025-11-29
-- Description: Adds columns to store all data collected from WhatsApp Flow trainer onboarding

-- Add new columns for data not currently captured
ALTER TABLE public.trainers 
ADD COLUMN IF NOT EXISTS sex character varying(20) NULL,
ADD COLUMN IF NOT EXISTS birthdate date NULL,
ADD COLUMN IF NOT EXISTS specializations_arr jsonb NULL DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS working_hours jsonb NULL DEFAULT '{}'::jsonb;

-- Add comments for documentation
COMMENT ON COLUMN public.trainers.sex IS 'Gender identity (male, female, transgender, other)';
COMMENT ON COLUMN public.trainers.birthdate IS 'Date of birth';
COMMENT ON COLUMN public.trainers.specializations_arr IS 'Array of training specializations (JSONB)';
COMMENT ON COLUMN public.trainers.working_hours IS 'Weekly availability schedule (JSONB) - {monday: {preset, hours}, tuesday: {...}, ...}';

-- Add indexes for new columns
CREATE INDEX IF NOT EXISTS idx_trainers_sex ON public.trainers (sex);
CREATE INDEX IF NOT EXISTS idx_trainers_birthdate ON public.trainers (birthdate);
CREATE INDEX IF NOT EXISTS idx_trainers_specializations_arr ON public.trainers USING gin (specializations_arr jsonb_path_ops);
CREATE INDEX IF NOT EXISTS idx_trainers_working_hours ON public.trainers USING gin (working_hours jsonb_path_ops);

-- Update existing working_hours column if it doesn't exist (it should from schema)
-- This is just to ensure backward compatibility
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'trainers' AND column_name = 'working_hours'
    ) THEN
        ALTER TABLE public.trainers ADD COLUMN working_hours jsonb NULL DEFAULT '{}'::jsonb;
    END IF;
END $$;
