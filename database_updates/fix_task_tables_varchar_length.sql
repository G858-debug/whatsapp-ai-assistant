-- ============================================
-- FIX: Task Tables VARCHAR Length
-- Issue: Phone numbers (up to 15 chars) don't fit in VARCHAR(10)
-- Solution: Increase to VARCHAR(20) to accommodate phone numbers during registration
-- ============================================

-- Update trainer_tasks table
ALTER TABLE public.trainer_tasks 
ALTER COLUMN trainer_id TYPE VARCHAR(20);

-- Update client_tasks table  
ALTER TABLE public.client_tasks 
ALTER COLUMN client_id TYPE VARCHAR(20);

-- Note: This allows phone numbers to be used as temporary IDs during registration
-- Once registration completes, the actual trainer_id/client_id (5-7 chars) will be used
