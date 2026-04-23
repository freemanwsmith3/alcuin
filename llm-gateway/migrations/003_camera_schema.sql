CREATE TABLE IF NOT EXISTS camera_readings (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    value       FLOAT,
    unit        TEXT,
    label       TEXT,
    notes       TEXT,
    image_url   TEXT
);

CREATE INDEX IF NOT EXISTS camera_readings_user_time_idx
    ON camera_readings (user_id, captured_at ASC);
