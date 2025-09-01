-- Add calendar preferences table
CREATE TABLE calendar_preferences (
    id uuid DEFAULT extensions.uuid_generate_v4() PRIMARY KEY,
    trainer_id uuid REFERENCES trainers(id) ON DELETE CASCADE,
    default_view varchar NOT NULL DEFAULT 'month',
    color_scheme jsonb DEFAULT '{}',
    start_time varchar NOT NULL DEFAULT '06:00',
    end_time varchar NOT NULL DEFAULT '20:00',
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()),
    updated_at timestamp with time zone DEFAULT timezone('utc'::text, now())
);

-- Add index on trainer_id
CREATE INDEX idx_calendar_preferences_trainer_id ON calendar_preferences(trainer_id);

-- Add unique constraint
ALTER TABLE calendar_preferences ADD CONSTRAINT unique_trainer_preferences UNIQUE (trainer_id);