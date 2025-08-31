-- Dashboard related tables

CREATE TABLE dashboard_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trainer_id UUID REFERENCES trainers(id),
    stat_date DATE NOT NULL,
    total_clients INTEGER,
    active_clients INTEGER,
    sessions_completed INTEGER,
    sessions_cancelled INTEGER,
    revenue_amount DECIMAL(10,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE dashboard_notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trainer_id UUID REFERENCES trainers(id),
    client_id UUID REFERENCES clients(id),
    notification_type VARCHAR(50),
    message TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_dashboard_stats_trainer ON dashboard_stats(trainer_id);
CREATE INDEX idx_dashboard_stats_date ON dashboard_stats(stat_date);
CREATE INDEX idx_dashboard_notifications_trainer ON dashboard_notifications(trainer_id);