-- Fix Client Schema - Ensure all columns exist
-- Run this in Supabase SQL Editor

-- Check if columns exist and add comments for clarity
COMMENT ON COLUMN public.clients.name IS 'Client full name (maps to full_name in config)';
COMMENT ON COLUMN public.clients.whatsapp IS 'Client WhatsApp phone number (maps to phone_number in config)';
COMMENT ON COLUMN public.clients.preferred_training_times IS 'Preferred training type (maps to preferred_training_type in config)';

-- Verify the schema is correct
DO $$
BEGIN
    -- Check if 'name' column exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'clients' 
        AND column_name = 'name'
    ) THEN
        RAISE EXCEPTION 'ERROR: Column "name" does not exist in clients table!';
    END IF;

    -- Check if 'whatsapp' column exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'clients' 
        AND column_name = 'whatsapp'
    ) THEN
        RAISE EXCEPTION 'ERROR: Column "whatsapp" does not exist in clients table!';
    END IF;

    -- Check if 'preferred_training_times' column exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'clients' 
        AND column_name = 'preferred_training_times'
    ) THEN
        RAISE EXCEPTION 'ERROR: Column "preferred_training_times" does not exist in clients table!';
    END IF;

    RAISE NOTICE 'SUCCESS: All required columns exist in clients table';
END $$;

-- If you need to add the preferred_training_times column (if it doesn't exist), uncomment below:
-- ALTER TABLE public.clients ADD COLUMN IF NOT EXISTS preferred_training_times text;

-- Update any NULL values to empty string for better display
UPDATE public.clients 
SET name = 'Unknown' 
WHERE name IS NULL OR name = '';

-- Show current schema
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public' 
AND table_name = 'clients'
ORDER BY ordinal_position;
