-- PostgreSQL schema for Namibia GBV ICT Readiness Survey Tracking System
-- Version 2.0 - Includes KoBoToolbox integration and GBV readiness indicators

-- ============================================================================
-- ENUMS
-- ============================================================================

CREATE TYPE survey_status AS ENUM ('pending', 'in_progress', 'completed');
CREATE TYPE connectivity_level AS ENUM ('none', 'limited', 'moderate', 'good', 'excellent');
CREATE TYPE institution_sector AS ENUM (
    'government',
    'health',
    'education',
    'police',
    'justice',
    'social_welfare',
    'ngo',
    'private',
    'community',
    'other'
);

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- 14 Namibian Regions
CREATE TABLE regions (
    id SERIAL PRIMARY KEY,
    code VARCHAR(2) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Institutions being surveyed
CREATE TABLE institutions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type institution_sector NOT NULL DEFAULT 'other',
    region_id INTEGER NOT NULL REFERENCES regions(id) ON DELETE CASCADE,
    address TEXT,
    contact_person VARCHAR(255),
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Survey Campaigns (e.g., "GBV ICT Readiness Assessment 2024")
CREATE TABLE survey_campaigns (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    kobo_asset_uid VARCHAR(100),  -- KoBoToolbox form/asset UID
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    target_institutions INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Individual Survey Submissions
CREATE TABLE surveys (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES survey_campaigns(id) ON DELETE CASCADE,
    institution_id INTEGER NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
    status survey_status NOT NULL DEFAULT 'pending',
    kobo_submission_id VARCHAR(100) UNIQUE,  -- KoBoToolbox submission ID
    submitted_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Daily Progress Tracking
CREATE TABLE daily_progress (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES survey_campaigns(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    total_completed INTEGER NOT NULL DEFAULT 0,
    total_in_progress INTEGER NOT NULL DEFAULT 0,
    total_pending INTEGER NOT NULL DEFAULT 0,
    UNIQUE (campaign_id, date)
);

-- ============================================================================
-- GBV ICT READINESS INDICATORS TABLE
-- ============================================================================

CREATE TABLE gbv_readiness_data (
    id SERIAL PRIMARY KEY,
    survey_id INTEGER NOT NULL UNIQUE REFERENCES surveys(id) ON DELETE CASCADE,
    
    -- 1. Policy & Governance Indicators
    has_gbv_policy BOOLEAN DEFAULT FALSE,
    gbv_policy_year INTEGER,
    has_gbv_action_plan BOOLEAN DEFAULT FALSE,
    has_gbv_focal_point BOOLEAN DEFAULT FALSE,
    gbv_focal_point_name VARCHAR(255),
    has_gbv_budget_allocation BOOLEAN DEFAULT FALSE,
    annual_gbv_budget DECIMAL(15, 2),
    
    -- 2. Human Resources & Capacity Indicators
    has_trained_staff BOOLEAN DEFAULT FALSE,
    num_trained_staff INTEGER DEFAULT 0,
    num_total_staff INTEGER DEFAULT 0,
    last_training_date DATE,
    training_frequency VARCHAR(50),  -- annual, biannual, quarterly, etc.
    has_dedicated_gbv_unit BOOLEAN DEFAULT FALSE,
    num_gbv_staff INTEGER DEFAULT 0,
    
    -- 3. ICT Infrastructure Indicators
    has_computers BOOLEAN DEFAULT FALSE,
    num_computers INTEGER DEFAULT 0,
    num_functional_computers INTEGER DEFAULT 0,
    internet_connectivity connectivity_level DEFAULT 'none',
    internet_speed_mbps INTEGER,
    has_backup_power BOOLEAN DEFAULT FALSE,
    has_server_room BOOLEAN DEFAULT FALSE,
    
    -- 4. Case Management & Data Systems
    has_case_management_system BOOLEAN DEFAULT FALSE,
    cms_type VARCHAR(100),  -- paper-based, spreadsheet, custom software, etc.
    cms_name VARCHAR(255),
    has_electronic_records BOOLEAN DEFAULT FALSE,
    has_data_backup_system BOOLEAN DEFAULT FALSE,
    backup_frequency VARCHAR(50),
    
    -- 5. Data Protection & Security
    has_data_protection_policy BOOLEAN DEFAULT FALSE,
    has_confidentiality_protocols BOOLEAN DEFAULT FALSE,
    has_access_controls BOOLEAN DEFAULT FALSE,
    has_data_encryption BOOLEAN DEFAULT FALSE,
    has_audit_trail BOOLEAN DEFAULT FALSE,
    
    -- 6. Service Delivery Indicators
    has_referral_pathway BOOLEAN DEFAULT FALSE,
    referral_partners_count INTEGER DEFAULT 0,
    has_24hr_service BOOLEAN DEFAULT FALSE,
    has_helpline BOOLEAN DEFAULT FALSE,
    helpline_number VARCHAR(50),
    has_mobile_services BOOLEAN DEFAULT FALSE,
    
    -- 7. Survivor Support Services
    has_survivor_support BOOLEAN DEFAULT FALSE,
    has_counseling_services BOOLEAN DEFAULT FALSE,
    has_legal_support BOOLEAN DEFAULT FALSE,
    has_medical_support BOOLEAN DEFAULT FALSE,
    has_shelter_services BOOLEAN DEFAULT FALSE,
    has_economic_support BOOLEAN DEFAULT FALSE,
    
    -- 8. Reporting & Monitoring
    has_reporting_mechanism BOOLEAN DEFAULT FALSE,
    reporting_frequency VARCHAR(50),
    has_monitoring_system BOOLEAN DEFAULT FALSE,
    has_performance_indicators BOOLEAN DEFAULT FALSE,
    num_cases_reported_last_year INTEGER,
    num_cases_resolved_last_year INTEGER,
    
    -- 9. Partnerships & Coordination
    has_partnerships BOOLEAN DEFAULT FALSE,
    num_active_partnerships INTEGER DEFAULT 0,
    has_mou_with_partners BOOLEAN DEFAULT FALSE,
    participates_in_coordination_meetings BOOLEAN DEFAULT FALSE,
    coordination_meeting_frequency VARCHAR(50),
    
    -- 10. Community Engagement
    has_community_outreach BOOLEAN DEFAULT FALSE,
    outreach_frequency VARCHAR(50),
    has_awareness_programs BOOLEAN DEFAULT FALSE,
    has_community_volunteers BOOLEAN DEFAULT FALSE,
    num_community_volunteers INTEGER DEFAULT 0,
    
    -- Respondent Information
    respondent_name VARCHAR(255),
    respondent_position VARCHAR(255),
    respondent_email VARCHAR(255),
    respondent_phone VARCHAR(50),
    
    -- Calculated Readiness Score (0-100)
    readiness_score DECIMAL(5, 2),
    
    -- Additional notes
    notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- SYNC LOG TABLE (for KoBoToolbox synchronization)
-- ============================================================================

CREATE TABLE kobo_sync_log (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER REFERENCES survey_campaigns(id) ON DELETE CASCADE,
    sync_started_at TIMESTAMPTZ NOT NULL,
    sync_completed_at TIMESTAMPTZ,
    submissions_fetched INTEGER DEFAULT 0,
    new_records INTEGER DEFAULT 0,
    updated_records INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    error_details JSONB,
    status VARCHAR(20) DEFAULT 'running',  -- running, completed, failed
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

CREATE INDEX idx_institutions_region ON institutions(region_id);
CREATE INDEX idx_institutions_type ON institutions(type);
CREATE INDEX idx_surveys_campaign ON surveys(campaign_id);
CREATE INDEX idx_surveys_institution ON surveys(institution_id);
CREATE INDEX idx_surveys_status ON surveys(status);
CREATE INDEX idx_surveys_kobo_id ON surveys(kobo_submission_id);
CREATE INDEX idx_surveys_completed_at ON surveys(completed_at);
CREATE INDEX idx_daily_progress_campaign_date ON daily_progress(campaign_id, date);
CREATE INDEX idx_gbv_readiness_survey ON gbv_readiness_data(survey_id);
CREATE INDEX idx_kobo_sync_campaign ON kobo_sync_log(campaign_id);

-- ============================================================================
-- VIEWS
-- ============================================================================

-- National Summary View
CREATE OR REPLACE VIEW v_national_summary AS
SELECT
    c.id AS campaign_id,
    c.name AS campaign_name,
    c.target_institutions,
    COUNT(DISTINCT i.id) AS institutions_surveyed,
    COUNT(s.id) AS total_surveys,
    COUNT(*) FILTER (WHERE s.status = 'completed') AS completed_surveys,
    COUNT(*) FILTER (WHERE s.status = 'in_progress') AS in_progress_surveys,
    COUNT(*) FILTER (WHERE s.status = 'pending') AS pending_surveys,
    CASE
        WHEN c.target_institutions > 0 THEN
            ROUND(COUNT(*) FILTER (WHERE s.status = 'completed')::numeric * 100.0 / c.target_institutions, 2)
        WHEN COUNT(s.id) > 0 THEN
            ROUND(COUNT(*) FILTER (WHERE s.status = 'completed')::numeric * 100.0 / COUNT(s.id), 2)
        ELSE 0
    END AS completion_rate
FROM survey_campaigns c
LEFT JOIN surveys s ON s.campaign_id = c.id
LEFT JOIN institutions i ON i.id = s.institution_id
GROUP BY c.id, c.name, c.target_institutions;

-- Regional Summary View
CREATE OR REPLACE VIEW v_regional_summary AS
SELECT
    c.id AS campaign_id,
    r.id AS region_id,
    r.code AS region_code,
    r.name AS region_name,
    COUNT(DISTINCT i.id) AS institutions_surveyed,
    COUNT(s.id) AS total_surveys,
    COUNT(*) FILTER (WHERE s.status = 'completed') AS completed_surveys,
    COUNT(*) FILTER (WHERE s.status = 'in_progress') AS in_progress_surveys,
    CASE
        WHEN COUNT(s.id) = 0 THEN 0
        ELSE ROUND(COUNT(*) FILTER (WHERE s.status = 'completed')::numeric * 100.0 / COUNT(s.id), 2)
    END AS completion_rate
FROM survey_campaigns c
CROSS JOIN regions r
LEFT JOIN institutions i ON i.region_id = r.id
LEFT JOIN surveys s ON s.institution_id = i.id AND s.campaign_id = c.id
GROUP BY c.id, r.id, r.code, r.name;

-- Daily Progress Trend View
CREATE OR REPLACE VIEW v_daily_progress_trend AS
SELECT
    dp.campaign_id,
    c.name AS campaign_name,
    dp.date,
    dp.total_completed,
    dp.total_in_progress,
    dp.total_pending,
    SUM(dp.total_completed) OVER (
        PARTITION BY dp.campaign_id 
        ORDER BY dp.date 
        ROWS UNBOUNDED PRECEDING
    ) AS cumulative_completed
FROM daily_progress dp
JOIN survey_campaigns c ON c.id = dp.campaign_id
ORDER BY dp.campaign_id, dp.date;

-- GBV Readiness Summary by Region
CREATE OR REPLACE VIEW v_regional_readiness_summary AS
SELECT
    r.id AS region_id,
    r.code AS region_code,
    r.name AS region_name,
    COUNT(grd.id) AS surveys_with_data,
    ROUND(AVG(grd.readiness_score), 2) AS avg_readiness_score,
    ROUND(AVG(CASE WHEN grd.has_gbv_policy THEN 100 ELSE 0 END), 2) AS policy_adoption_rate,
    ROUND(AVG(CASE WHEN grd.has_case_management_system THEN 100 ELSE 0 END), 2) AS cms_adoption_rate,
    ROUND(AVG(CASE WHEN grd.has_trained_staff THEN 100 ELSE 0 END), 2) AS training_rate,
    ROUND(AVG(CASE WHEN grd.has_computers THEN 100 ELSE 0 END), 2) AS computer_access_rate,
    ROUND(AVG(CASE WHEN grd.internet_connectivity IN ('good', 'excellent') THEN 100 ELSE 0 END), 2) AS good_connectivity_rate
FROM regions r
LEFT JOIN institutions i ON i.region_id = r.id
LEFT JOIN surveys s ON s.institution_id = i.id
LEFT JOIN gbv_readiness_data grd ON grd.survey_id = s.id
GROUP BY r.id, r.code, r.name;

-- Institution Type Readiness Summary
CREATE OR REPLACE VIEW v_sector_readiness_summary AS
SELECT
    i.type AS institution_sector,
    COUNT(grd.id) AS surveys_with_data,
    ROUND(AVG(grd.readiness_score), 2) AS avg_readiness_score,
    ROUND(AVG(CASE WHEN grd.has_gbv_policy THEN 100 ELSE 0 END), 2) AS policy_adoption_rate,
    ROUND(AVG(CASE WHEN grd.has_case_management_system THEN 100 ELSE 0 END), 2) AS cms_adoption_rate,
    ROUND(AVG(grd.num_trained_staff), 0) AS avg_trained_staff
FROM institutions i
LEFT JOIN surveys s ON s.institution_id = i.id
LEFT JOIN gbv_readiness_data grd ON grd.survey_id = s.id
WHERE grd.id IS NOT NULL
GROUP BY i.type;

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Update daily progress statistics
CREATE OR REPLACE FUNCTION update_daily_progress()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'completed' AND (OLD IS NULL OR OLD.status != 'completed') THEN
        INSERT INTO daily_progress (campaign_id, date, total_completed)
        VALUES (NEW.campaign_id, COALESCE(NEW.completed_at::date, CURRENT_DATE), 1)
        ON CONFLICT (campaign_id, date)
        DO UPDATE SET total_completed = daily_progress.total_completed + 1;
    ELSIF TG_OP = 'UPDATE' AND OLD.status = 'completed' AND NEW.status != 'completed' THEN
        UPDATE daily_progress
        SET total_completed = GREATEST(total_completed - 1, 0)
        WHERE campaign_id = OLD.campaign_id
          AND date = COALESCE(OLD.completed_at::date, CURRENT_DATE);
    END IF;
    
    -- Update the updated_at timestamp
    NEW.updated_at = NOW();
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Calculate GBV ICT Readiness Score (0-100)
CREATE OR REPLACE FUNCTION calculate_readiness_score(p_survey_id INTEGER)
RETURNS DECIMAL AS $$
DECLARE
    v_score DECIMAL := 0;
    v_weights DECIMAL := 0;
    rec gbv_readiness_data%ROWTYPE;
BEGIN
    SELECT * INTO rec FROM gbv_readiness_data WHERE survey_id = p_survey_id;
    
    IF NOT FOUND THEN
        RETURN 0;
    END IF;
    
    -- Policy & Governance (15% weight)
    IF rec.has_gbv_policy THEN v_score := v_score + 5; END IF;
    IF rec.has_gbv_action_plan THEN v_score := v_score + 3; END IF;
    IF rec.has_gbv_focal_point THEN v_score := v_score + 4; END IF;
    IF rec.has_gbv_budget_allocation THEN v_score := v_score + 3; END IF;
    
    -- Human Resources (15% weight)
    IF rec.has_trained_staff THEN v_score := v_score + 5; END IF;
    IF rec.num_trained_staff >= 5 THEN v_score := v_score + 5; 
    ELSIF rec.num_trained_staff >= 2 THEN v_score := v_score + 3;
    ELSIF rec.num_trained_staff >= 1 THEN v_score := v_score + 1; END IF;
    IF rec.has_dedicated_gbv_unit THEN v_score := v_score + 5; END IF;
    
    -- ICT Infrastructure (20% weight)
    IF rec.has_computers THEN v_score := v_score + 5; END IF;
    IF rec.num_functional_computers >= 5 THEN v_score := v_score + 5;
    ELSIF rec.num_functional_computers >= 2 THEN v_score := v_score + 3; END IF;
    CASE rec.internet_connectivity
        WHEN 'excellent' THEN v_score := v_score + 10;
        WHEN 'good' THEN v_score := v_score + 7;
        WHEN 'moderate' THEN v_score := v_score + 4;
        WHEN 'limited' THEN v_score := v_score + 2;
        ELSE v_score := v_score + 0;
    END CASE;
    
    -- Case Management (15% weight)
    IF rec.has_case_management_system THEN v_score := v_score + 8; END IF;
    IF rec.has_electronic_records THEN v_score := v_score + 4; END IF;
    IF rec.has_data_backup_system THEN v_score := v_score + 3; END IF;
    
    -- Data Protection (10% weight)
    IF rec.has_data_protection_policy THEN v_score := v_score + 4; END IF;
    IF rec.has_confidentiality_protocols THEN v_score := v_score + 3; END IF;
    IF rec.has_access_controls THEN v_score := v_score + 3; END IF;
    
    -- Service Delivery (10% weight)
    IF rec.has_referral_pathway THEN v_score := v_score + 5; END IF;
    IF rec.has_helpline THEN v_score := v_score + 3; END IF;
    IF rec.has_24hr_service THEN v_score := v_score + 2; END IF;
    
    -- Survivor Support (10% weight)
    IF rec.has_survivor_support THEN v_score := v_score + 4; END IF;
    IF rec.has_counseling_services THEN v_score := v_score + 2; END IF;
    IF rec.has_legal_support THEN v_score := v_score + 2; END IF;
    IF rec.has_medical_support THEN v_score := v_score + 2; END IF;
    
    -- Monitoring & Reporting (5% weight)
    IF rec.has_monitoring_system THEN v_score := v_score + 3; END IF;
    IF rec.has_reporting_mechanism THEN v_score := v_score + 2; END IF;
    
    -- Update the stored score
    UPDATE gbv_readiness_data 
    SET readiness_score = v_score, updated_at = NOW()
    WHERE survey_id = p_survey_id;
    
    RETURN v_score;
END;
$$ LANGUAGE plpgsql;

-- Get comprehensive progress report for a campaign
CREATE OR REPLACE FUNCTION get_progress_report(p_campaign_id INTEGER)
RETURNS TABLE (
    campaign_id INTEGER,
    target_institutions INTEGER,
    total_surveys BIGINT,
    completed BIGINT,
    in_progress BIGINT,
    pending BIGINT,
    completion_rate NUMERIC,
    avg_readiness_score NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p_campaign_id,
        c.target_institutions,
        COUNT(s.id) AS total_surveys,
        COUNT(*) FILTER (WHERE s.status = 'completed') AS completed,
        COUNT(*) FILTER (WHERE s.status = 'in_progress') AS in_progress,
        COUNT(*) FILTER (WHERE s.status = 'pending') AS pending,
        CASE
            WHEN c.target_institutions > 0 THEN
                ROUND(COUNT(*) FILTER (WHERE s.status = 'completed')::numeric * 100.0 / c.target_institutions, 2)
            WHEN COUNT(s.id) > 0 THEN
                ROUND(COUNT(*) FILTER (WHERE s.status = 'completed')::numeric * 100.0 / COUNT(s.id), 2)
            ELSE 0
        END AS completion_rate,
        ROUND(AVG(grd.readiness_score), 2) AS avg_readiness_score
    FROM survey_campaigns c
    LEFT JOIN surveys s ON s.campaign_id = c.id
    LEFT JOIN gbv_readiness_data grd ON grd.survey_id = s.id
    WHERE c.id = p_campaign_id
    GROUP BY c.id, c.target_institutions;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- TRIGGERS
-- ============================================================================

DROP TRIGGER IF EXISTS trg_update_daily_progress ON surveys;
CREATE TRIGGER trg_update_daily_progress
AFTER INSERT OR UPDATE OF status ON surveys
FOR EACH ROW
EXECUTE FUNCTION update_daily_progress();

-- Auto-calculate readiness score on insert/update
CREATE OR REPLACE FUNCTION trg_calculate_readiness_score()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM calculate_readiness_score(NEW.survey_id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_auto_readiness_score ON gbv_readiness_data;
CREATE TRIGGER trg_auto_readiness_score
AFTER INSERT OR UPDATE ON gbv_readiness_data
FOR EACH ROW
EXECUTE FUNCTION trg_calculate_readiness_score();

-- ============================================================================
-- SEED DATA: 14 Namibian Regions
-- ============================================================================

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
    ('OD', 'Otjozondjupa')
ON CONFLICT (code) DO NOTHING;
