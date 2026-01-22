-- Sample data for Namibia Survey Tracking System

INSERT INTO regions (code, name) VALUES
('CA', 'Zambezi'),
('ER', 'Erongo'),
('HA', 'Hardap'),
('KA', 'Karas'),
('KE', 'Kavango East'),
('KW', 'Kavango West'),
('KH', 'Khomas'),
('KU', 'Kunene'),
('OW', 'Ohangwena'),
('OH', 'Omaheke'),
('OS', 'Omusati'),
('ON', 'Oshana'),
('OT', 'Oshikoto'),
('OD', 'Otjozondjupa');

INSERT INTO survey_campaigns (name, description, start_date, end_date) VALUES
('GBV Readiness 2025', 'Readiness assessment campaign for GBV data systems', '2025-01-01', '2025-12-31'),
('Health Facility Readiness 2025', 'Health facility readiness survey', '2025-02-01', '2025-11-30');

INSERT INTO institutions (name, type, region_id)
SELECT
    'Institution ' || r.code || ' - ' || i::text,
    'School',
    r.id
FROM regions r,
LATERAL generate_series(1, 5) AS i;

INSERT INTO surveys (campaign_id, institution_id, status, completed_at)
SELECT
    c.id,
    inst.id,
    CASE
        WHEN random() < 0.5 THEN 'completed'
        WHEN random() < 0.8 THEN 'in_progress'
        ELSE 'pending'
    END AS status,
    NOW() - (trunc(random() * 30)::int || ' days')::interval
FROM survey_campaigns c
JOIN institutions inst ON TRUE
WHERE c.name = 'GBV Readiness 2025';


