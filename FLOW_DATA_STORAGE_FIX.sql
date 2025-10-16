-- ============================================
-- FLOW DATA STORAGE ENHANCEMENT
-- ============================================
-- This migration adds missing columns to store all WhatsApp Flow data

-- Add missing columns to trainers table for complete flow data storage
ALTER TABLE public.trainers
  ADD COLUMN IF NOT EXISTS services_offered jsonb DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS pricing_flexibility jsonb DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS additional_notes text,
  ADD COLUMN IF NOT EXISTS registration_method varchar(20) DEFAULT 'text';


-- If columns pre-existed as text, cast them to jsonb (NULL-safe)
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'trainers'
      AND column_name = 'services_offered' AND data_type = 'text'
  ) THEN
    ALTER TABLE public.trainers
      ALTER COLUMN services_offered TYPE jsonb USING
        CASE
          WHEN trim(services_offered) IN ('', 'null') THEN '[]'::jsonb
          WHEN services_offered ~ '^\s*\[' THEN services_offered::jsonb
          WHEN services_offered ~ '^\s*\{' THEN services_offered::jsonb
          ELSE to_jsonb(services_offered)
        END,
      ALTER COLUMN services_offered SET DEFAULT '[]'::jsonb;
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'trainers'
      AND column_name = 'pricing_flexibility' AND data_type = 'text'
  ) THEN
    ALTER TABLE public.trainers
      ALTER COLUMN pricing_flexibility TYPE jsonb USING
        CASE
          WHEN trim(pricing_flexibility) IN ('', 'null') THEN '[]'::jsonb
          WHEN pricing_flexibility ~ '^\s*\[' THEN pricing_flexibility::jsonb
          WHEN pricing_flexibility ~ '^\s*\{' THEN pricing_flexibility::jsonb
          ELSE to_jsonb(pricing_flexibility)
        END,
      ALTER COLUMN pricing_flexibility SET DEFAULT '[]'::jsonb;
  END IF;
END$$;

-- Indexes: specify JSONB opclass explicitly
CREATE INDEX IF NOT EXISTS idx_trainers_services_offered
  ON public.trainers USING gin (services_offered jsonb_path_ops);

CREATE INDEX IF NOT EXISTS idx_trainers_pricing_flexibility
  ON public.trainers USING gin (pricing_flexibility jsonb_path_ops);

-- registration_method can stay BTREE
CREATE INDEX IF NOT EXISTS idx_trainers_registration_method
  ON public.trainers (registration_method);

-- Add comments for documentation
COMMENT ON COLUMN trainers.services_offered IS 'Array of services offered by trainer (from flow)';
COMMENT ON COLUMN trainers.pricing_flexibility IS 'Array of pricing flexibility options (from flow)';
COMMENT ON COLUMN trainers.additional_notes IS 'Additional notes from trainer registration flow';
COMMENT ON COLUMN trainers.registration_method IS 'Method used for registration: text, flow, or manual';

-- Verify the changes
SELECT 'Flow data storage columns added successfully' as status;

-- Show the new columns
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'trainers' 
AND table_schema = 'public'
AND column_name IN ('services_offered', 'pricing_flexibility', 'additional_notes', 'registration_method')
ORDER BY column_name;