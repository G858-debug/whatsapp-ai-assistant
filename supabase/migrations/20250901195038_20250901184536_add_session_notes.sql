-- Add notes column to bookings table
ALTER TABLE bookings ADD COLUMN notes TEXT;

-- Add indices for day view queries
CREATE INDEX idx_bookings_trainer_date ON bookings(trainer_id, session_date);
CREATE INDEX idx_bookings_client_date ON bookings(client_id, session_date);