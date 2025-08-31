-- Add transaction_id column to payment_requests
ALTER TABLE payment_requests
ADD COLUMN IF NOT EXISTS transaction_id VARCHAR(100);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_payment_requests_status ON payment_requests(status);
CREATE INDEX IF NOT EXISTS idx_payment_requests_transaction_id ON payment_requests(transaction_id);