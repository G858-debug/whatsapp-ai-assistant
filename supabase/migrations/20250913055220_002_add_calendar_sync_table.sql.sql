CREATE TABLE calendar_sync_logs (
    id SERIAL PRIMARY KEY,
    trainer_id UUID NOT NULL,
    sync_date TIMESTAMP NOT NULL,
    sync_status VARCHAR(50) NOT NULL
);