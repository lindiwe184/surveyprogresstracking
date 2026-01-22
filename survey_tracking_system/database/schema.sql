-- PostgreSQL schema for Namibia Survey Tracking System

CREATE TYPE survey_status AS ENUM ('pending', 'in_progress', 'completed');

CREATE TABLE regions (
    id SERIAL PRIMARY KEY,
    code VARCHAR(2) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE institutions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    region_id INTEGER NOT NULL REFERENCES regions(id) ON DELETE CASCADE
);

CREATE TABLE survey_campaigns (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL
);

CREATE TABLE surveys (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES survey_campaigns(id) ON DELETE CASCADE,
    institution_id INTEGER NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
    status survey_status NOT NULL DEFAULT 'pending',
    completed_at TIMESTAMPTZ
);

CREATE TABLE daily_progress (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES survey_campaigns(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    total_completed INTEGER NOT NULL DEFAULT 0,
    UNIQUE (campaign_id, date)
);

CREATE INDEX idx_institutions_region ON institutions(region_id);
CREATE INDEX idx_surveys_campaign ON surveys(campaign_id);
CREATE INDEX idx_surveys_institution ON surveys(institution_id);
CREATE INDEX idx_surveys_status ON surveys(status);
CREATE INDEX idx_daily_progress_campaign_date ON daily_progress(campaign_id, date);

CREATE OR REPLACE VIEW v_national_summary AS
SELECT
    c.id AS campaign_id,
    c.name AS campaign_name,
    COUNT(s.id) AS total_surveys,
    COUNT(*) FILTER (WHERE s.status = 'completed') AS completed_surveys,
    CASE
        WHEN COUNT(s.id) = 0 THEN 0
        ELSE ROUND(COUNT(*) FILTER (WHERE s.status = 'completed')::numeric * 100.0 / COUNT(s.id), 2)
    END AS completion_rate
FROM survey_campaigns c
LEFT JOIN surveys s ON s.campaign_id = c.id
GROUP BY c.id, c.name;

CREATE OR REPLACE VIEW v_regional_summary AS
SELECT
    c.id AS campaign_id,
    r.id AS region_id,
    r.name AS region_name,
    COUNT(s.id) AS total_surveys,
    COUNT(*) FILTER (WHERE s.status = 'completed') AS completed_surveys,
    CASE
        WHEN COUNT(s.id) = 0 THEN 0
        ELSE ROUND(COUNT(*) FILTER (WHERE s.status = 'completed')::numeric * 100.0 / COUNT(s.id), 2)
    END AS completion_rate
FROM survey_campaigns c
JOIN surveys s ON s.campaign_id = c.id
JOIN institutions i ON i.id = s.institution_id
JOIN regions r ON r.id = i.region_id
GROUP BY c.id, r.id, r.name;

CREATE OR REPLACE VIEW v_daily_progress_trend AS
SELECT
    dp.campaign_id,
    c.name AS campaign_name,
    dp.date,
    dp.total_completed
FROM daily_progress dp
JOIN survey_campaigns c ON c.id = dp.campaign_id;

CREATE OR REPLACE FUNCTION update_daily_progress()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'completed' THEN
        INSERT INTO daily_progress (campaign_id, date, total_completed)
        VALUES (NEW.campaign_id, COALESCE(NEW.completed_at::date, CURRENT_DATE), 1)
        ON CONFLICT (campaign_id, date)
        DO UPDATE SET total_completed = daily_progress.total_completed + 1;
    ELSIF TG_OP = 'UPDATE' AND OLD.status = 'completed' AND NEW.status <> 'completed' THEN
        UPDATE daily_progress
        SET total_completed = GREATEST(total_completed - 1, 0)
        WHERE campaign_id = OLD.campaign_id
          AND date = COALESCE(OLD.completed_at::date, CURRENT_DATE);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_progress_report(p_campaign_id INTEGER)
RETURNS TABLE (
    campaign_id INTEGER,
    total_surveys INTEGER,
    completed INTEGER,
    in_progress INTEGER,
    pending INTEGER,
    completion_rate NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p_campaign_id,
        COUNT(s.id) AS total_surveys,
        COUNT(*) FILTER (WHERE s.status = 'completed') AS completed,
        COUNT(*) FILTER (WHERE s.status = 'in_progress') AS in_progress,
        COUNT(*) FILTER (WHERE s.status = 'pending') AS pending,
        CASE
            WHEN COUNT(s.id) = 0 THEN 0
            ELSE ROUND(COUNT(*) FILTER (WHERE s.status = 'completed')::numeric * 100.0 / COUNT(s.id), 2)
        END AS completion_rate
    FROM surveys s
    WHERE s.campaign_id = p_campaign_id;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_daily_progress ON surveys;

CREATE TRIGGER trg_update_daily_progress
AFTER INSERT OR UPDATE OF status ON surveys
FOR EACH ROW
EXECUTE FUNCTION update_daily_progress();


