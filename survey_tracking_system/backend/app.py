"""
Flask Backend API for Namibia GBV ICT Readiness Survey Tracking System

Provides RESTful endpoints for:
- Campaign management
- Survey tracking (with KoBoToolbox integration)
- Regional and national statistics
- GBV ICT readiness indicators
"""

import os
import json
from datetime import date, datetime, timedelta
from decimal import Decimal

from flask import Flask, jsonify, request
from flask_cors import CORS
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, scoped_session, sessionmaker
from sqlalchemy import create_engine

from config import get_config

Base = declarative_base()

# ============================================================================
# ENUMS
# ============================================================================

survey_status_enum = ENUM(
    "pending", "in_progress", "completed",
    name="survey_status", create_type=False
)

connectivity_enum = ENUM(
    "none", "limited", "moderate", "good", "excellent",
    name="connectivity_level", create_type=False
)

institution_sector_enum = ENUM(
    "government", "health", "education", "police", "justice",
    "social_welfare", "ngo", "private", "community", "other",
    name="institution_sector", create_type=False
)

# ============================================================================
# MODELS
# ============================================================================

class Region(Base):
    __tablename__ = "regions"

    id = Column(Integer, primary_key=True)
    code = Column(String(2), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=func.now())

    institutions = relationship("Institution", back_populates="region")


class Institution(Base):
    __tablename__ = "institutions"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    type = Column(institution_sector_enum, nullable=False, default="other")
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    address = Column(Text)
    contact_person = Column(String(255))
    contact_email = Column(String(255))
    contact_phone = Column(String(50))
    latitude = Column(Numeric(10, 8))
    longitude = Column(Numeric(11, 8))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    region = relationship("Region", back_populates="institutions")
    surveys = relationship("Survey", back_populates="institution")


class SurveyCampaign(Base):
    __tablename__ = "survey_campaigns"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    kobo_asset_uid = Column(String(100))
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    target_institutions = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    surveys = relationship("Survey", back_populates="campaign")
    sync_logs = relationship("KoboSyncLog", back_populates="campaign")


class Survey(Base):
    __tablename__ = "surveys"

    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey("survey_campaigns.id"), nullable=False)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False)
    status = Column(survey_status_enum, nullable=False, default="pending")
    kobo_submission_id = Column(String(100), unique=True)
    submitted_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    campaign = relationship("SurveyCampaign", back_populates="surveys")
    institution = relationship("Institution", back_populates="surveys")
    readiness_data = relationship("GBVReadinessData", back_populates="survey", uselist=False)


class DailyProgress(Base):
    __tablename__ = "daily_progress"

    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey("survey_campaigns.id"), nullable=False)
    date = Column(Date, nullable=False)
    total_completed = Column(Integer, default=0)
    total_in_progress = Column(Integer, default=0)
    total_pending = Column(Integer, default=0)


class GBVReadinessData(Base):
    __tablename__ = "gbv_readiness_data"

    id = Column(Integer, primary_key=True)
    survey_id = Column(Integer, ForeignKey("surveys.id"), unique=True, nullable=False)

    # Policy & Governance
    has_gbv_policy = Column(Boolean, default=False)
    gbv_policy_year = Column(Integer)
    has_gbv_action_plan = Column(Boolean, default=False)
    has_gbv_focal_point = Column(Boolean, default=False)
    gbv_focal_point_name = Column(String(255))
    has_gbv_budget_allocation = Column(Boolean, default=False)
    annual_gbv_budget = Column(Numeric(15, 2))

    # Human Resources
    has_trained_staff = Column(Boolean, default=False)
    num_trained_staff = Column(Integer, default=0)
    num_total_staff = Column(Integer, default=0)
    last_training_date = Column(Date)
    training_frequency = Column(String(50))
    has_dedicated_gbv_unit = Column(Boolean, default=False)
    num_gbv_staff = Column(Integer, default=0)

    # ICT Infrastructure
    has_computers = Column(Boolean, default=False)
    num_computers = Column(Integer, default=0)
    num_functional_computers = Column(Integer, default=0)
    internet_connectivity = Column(connectivity_enum, default="none")
    internet_speed_mbps = Column(Integer)
    has_backup_power = Column(Boolean, default=False)
    has_server_room = Column(Boolean, default=False)

    # Case Management
    has_case_management_system = Column(Boolean, default=False)
    cms_type = Column(String(100))
    cms_name = Column(String(255))
    has_electronic_records = Column(Boolean, default=False)
    has_data_backup_system = Column(Boolean, default=False)
    backup_frequency = Column(String(50))

    # Data Protection
    has_data_protection_policy = Column(Boolean, default=False)
    has_confidentiality_protocols = Column(Boolean, default=False)
    has_access_controls = Column(Boolean, default=False)
    has_data_encryption = Column(Boolean, default=False)
    has_audit_trail = Column(Boolean, default=False)

    # Service Delivery
    has_referral_pathway = Column(Boolean, default=False)
    referral_partners_count = Column(Integer, default=0)
    has_24hr_service = Column(Boolean, default=False)
    has_helpline = Column(Boolean, default=False)
    helpline_number = Column(String(50))
    has_mobile_services = Column(Boolean, default=False)

    # Survivor Support
    has_survivor_support = Column(Boolean, default=False)
    has_counseling_services = Column(Boolean, default=False)
    has_legal_support = Column(Boolean, default=False)
    has_medical_support = Column(Boolean, default=False)
    has_shelter_services = Column(Boolean, default=False)
    has_economic_support = Column(Boolean, default=False)

    # Reporting & Monitoring
    has_reporting_mechanism = Column(Boolean, default=False)
    reporting_frequency = Column(String(50))
    has_monitoring_system = Column(Boolean, default=False)
    has_performance_indicators = Column(Boolean, default=False)
    num_cases_reported_last_year = Column(Integer)
    num_cases_resolved_last_year = Column(Integer)

    # Partnerships
    has_partnerships = Column(Boolean, default=False)
    num_active_partnerships = Column(Integer, default=0)
    has_mou_with_partners = Column(Boolean, default=False)
    participates_in_coordination_meetings = Column(Boolean, default=False)
    coordination_meeting_frequency = Column(String(50))

    # Community Engagement
    has_community_outreach = Column(Boolean, default=False)
    outreach_frequency = Column(String(50))
    has_awareness_programs = Column(Boolean, default=False)
    has_community_volunteers = Column(Boolean, default=False)
    num_community_volunteers = Column(Integer, default=0)

    # Respondent
    respondent_name = Column(String(255))
    respondent_position = Column(String(255))
    respondent_email = Column(String(255))
    respondent_phone = Column(String(50))

    # Score
    readiness_score = Column(Numeric(5, 2))
    notes = Column(Text)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    survey = relationship("Survey", back_populates="readiness_data")


class KoboSyncLog(Base):
    __tablename__ = "kobo_sync_log"

    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey("survey_campaigns.id"))
    sync_started_at = Column(DateTime, nullable=False)
    sync_completed_at = Column(DateTime)
    submissions_fetched = Column(Integer, default=0)
    new_records = Column(Integer, default=0)
    updated_records = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    error_details = Column(JSONB)
    status = Column(String(20), default="running")
    created_at = Column(DateTime, default=func.now())

    campaign = relationship("SurveyCampaign", back_populates="sync_logs")


# ============================================================================
# APPLICATION FACTORY
# ============================================================================

def create_app():
    app = Flask(__name__)
    app_config = get_config()()
    app.config.from_object(app_config)

    origins = os.getenv("CORS_ORIGINS", "*")
    CORS(app, resources={r"/api/*": {"origins": origins}})

    engine = create_engine(
        app.config["SQLALCHEMY_DATABASE_URI"],
        **app.config.get("SQLALCHEMY_ENGINE_OPTIONS", {}),
    )
    Session = scoped_session(sessionmaker(bind=engine))

    @app.teardown_appcontext
    def remove_session(exception=None):
        Session.remove()

    # Utility helpers
    def get_session():
        return Session()

    def parse_int(value, default=None):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def decimal_to_float(obj):
        """Convert Decimal objects to float for JSON serialization."""
        if isinstance(obj, Decimal):
            return float(obj)
        return obj

    # ========================================================================
    # CAMPAIGN ENDPOINTS
    # ========================================================================

    @app.get("/api/campaigns")
    def list_campaigns():
        session = get_session()
        campaigns = session.query(SurveyCampaign).all()
        return jsonify([
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "kobo_asset_uid": c.kobo_asset_uid,
                "start_date": c.start_date.isoformat(),
                "end_date": c.end_date.isoformat(),
                "target_institutions": c.target_institutions,
                "is_active": c.is_active,
            }
            for c in campaigns
        ])

    @app.post("/api/campaigns")
    def create_campaign():
        payload = request.get_json() or {}
        required = ["name", "start_date", "end_date"]
        if not all(k in payload for k in required):
            return jsonify({"error": "Missing required fields"}), 400
        try:
            start_date = date.fromisoformat(payload["start_date"])
            end_date = date.fromisoformat(payload["end_date"])
        except ValueError:
            return jsonify({"error": "Invalid date format"}), 400

        session = get_session()
        campaign = SurveyCampaign(
            name=payload["name"],
            description=payload.get("description"),
            kobo_asset_uid=payload.get("kobo_asset_uid"),
            start_date=start_date,
            end_date=end_date,
            target_institutions=payload.get("target_institutions", 0),
        )
        session.add(campaign)
        session.commit()
        return jsonify({"id": campaign.id}), 201

    @app.get("/api/campaigns/<int:campaign_id>")
    def get_campaign(campaign_id: int):
        session = get_session()
        campaign = session.query(SurveyCampaign).get(campaign_id)
        if not campaign:
            return jsonify({"error": "Campaign not found"}), 404
        return jsonify({
            "id": campaign.id,
            "name": campaign.name,
            "description": campaign.description,
            "kobo_asset_uid": campaign.kobo_asset_uid,
            "start_date": campaign.start_date.isoformat(),
            "end_date": campaign.end_date.isoformat(),
            "target_institutions": campaign.target_institutions,
            "is_active": campaign.is_active,
        })

    @app.put("/api/campaigns/<int:campaign_id>")
    def update_campaign(campaign_id: int):
        payload = request.get_json() or {}
        session = get_session()
        campaign = session.query(SurveyCampaign).get(campaign_id)
        if not campaign:
            return jsonify({"error": "Campaign not found"}), 404

        if "name" in payload:
            campaign.name = payload["name"]
        if "description" in payload:
            campaign.description = payload["description"]
        if "kobo_asset_uid" in payload:
            campaign.kobo_asset_uid = payload["kobo_asset_uid"]
        if "target_institutions" in payload:
            campaign.target_institutions = payload["target_institutions"]
        if "is_active" in payload:
            campaign.is_active = payload["is_active"]

        session.commit()
        return jsonify({"message": "Updated"})

    @app.get("/api/campaigns/<int:campaign_id>/national-summary")
    def national_summary(campaign_id: int):
        session = get_session()
        campaign = session.query(SurveyCampaign).get(campaign_id)
        if not campaign:
            return jsonify({"error": "Campaign not found"}), 404

        total = session.query(func.count(Survey.id)).filter(
            Survey.campaign_id == campaign_id
        ).scalar()
        completed = session.query(func.count(Survey.id)).filter(
            Survey.campaign_id == campaign_id,
            Survey.status == "completed",
        ).scalar()
        in_progress = session.query(func.count(Survey.id)).filter(
            Survey.campaign_id == campaign_id,
            Survey.status == "in_progress",
        ).scalar()

        # Average readiness score
        avg_score = session.query(func.avg(GBVReadinessData.readiness_score)).join(
            Survey, Survey.id == GBVReadinessData.survey_id
        ).filter(Survey.campaign_id == campaign_id).scalar()

        target = campaign.target_institutions or total
        completion_rate = (completed / target * 100) if target else 0.0

        return jsonify({
            "campaign_id": campaign_id,
            "campaign_name": campaign.name,
            "target_institutions": campaign.target_institutions,
            "total_surveys": total,
            "completed_surveys": completed,
            "in_progress_surveys": in_progress,
            "pending_surveys": total - completed - in_progress,
            "completion_rate": round(completion_rate, 2),
            "avg_readiness_score": decimal_to_float(avg_score) if avg_score else None,
        })

    @app.get("/api/campaigns/<int:campaign_id>/regional-summary")
    def regional_summary(campaign_id: int):
        session = get_session()
        rows = (
            session.query(
                Region.id.label("region_id"),
                Region.code.label("region_code"),
                Region.name.label("region_name"),
                func.count(Survey.id).label("total_surveys"),
                func.count(func.nullif(Survey.status != "completed", True)).label("completed_surveys"),
                func.avg(GBVReadinessData.readiness_score).label("avg_readiness_score"),
            )
            .outerjoin(Institution, Institution.region_id == Region.id)
            .outerjoin(Survey, (Survey.institution_id == Institution.id) & (Survey.campaign_id == campaign_id))
            .outerjoin(GBVReadinessData, GBVReadinessData.survey_id == Survey.id)
            .group_by(Region.id, Region.code, Region.name)
            .all()
        )

        data = []
        for r in rows:
            completed = r.completed_surveys or 0
            total = r.total_surveys or 0
            data.append({
                "region_id": r.region_id,
                "region_code": r.region_code,
                "region_name": r.region_name,
                "total_surveys": total,
                "completed_surveys": completed,
                "completion_rate": round((completed / total * 100), 2) if total else 0.0,
                "avg_readiness_score": decimal_to_float(r.avg_readiness_score) if r.avg_readiness_score else None,
            })
        return jsonify(data)

    @app.get("/api/campaigns/<int:campaign_id>/daily-progress")
    def daily_progress(campaign_id: int):
        days = parse_int(request.args.get("days"), 30)
        session = get_session()
        since = date.today() - timedelta(days=days - 1)
        rows = (
            session.query(DailyProgress)
            .filter(
                DailyProgress.campaign_id == campaign_id,
                DailyProgress.date >= since,
            )
            .order_by(DailyProgress.date)
            .all()
        )

        # Calculate cumulative
        cumulative = 0
        result = []
        for r in rows:
            cumulative += r.total_completed
            result.append({
                "date": r.date.isoformat(),
                "daily_completed": r.total_completed,
                "cumulative_completed": cumulative,
            })
        return jsonify(result)

    @app.get("/api/campaigns/<int:campaign_id>/progress-report")
    def progress_report(campaign_id: int):
        session = get_session()
        campaign = session.query(SurveyCampaign).get(campaign_id)
        if not campaign:
            return jsonify({"error": "Campaign not found"}), 404

        total = session.query(func.count(Survey.id)).filter(
            Survey.campaign_id == campaign_id
        ).scalar()
        completed = session.query(func.count(Survey.id)).filter(
            Survey.campaign_id == campaign_id,
            Survey.status == "completed",
        ).scalar()
        in_progress = session.query(func.count(Survey.id)).filter(
            Survey.campaign_id == campaign_id,
            Survey.status == "in_progress",
        ).scalar()
        pending = session.query(func.count(Survey.id)).filter(
            Survey.campaign_id == campaign_id,
            Survey.status == "pending",
        ).scalar()

        # GBV Readiness indicators summary
        readiness_stats = session.query(
            func.avg(GBVReadinessData.readiness_score).label("avg_score"),
            func.avg(func.cast(GBVReadinessData.has_gbv_policy, Integer) * 100).label("policy_rate"),
            func.avg(func.cast(GBVReadinessData.has_case_management_system, Integer) * 100).label("cms_rate"),
            func.avg(func.cast(GBVReadinessData.has_trained_staff, Integer) * 100).label("training_rate"),
            func.avg(func.cast(GBVReadinessData.has_computers, Integer) * 100).label("computer_rate"),
        ).join(Survey, Survey.id == GBVReadinessData.survey_id).filter(
            Survey.campaign_id == campaign_id
        ).first()

        target = campaign.target_institutions or total
        completion_rate = (completed / target * 100) if target else 0.0

        return jsonify({
            "campaign_id": campaign_id,
            "campaign_name": campaign.name,
            "target_institutions": campaign.target_institutions,
            "total_surveys": total,
            "completed": completed,
            "in_progress": in_progress,
            "pending": pending,
            "completion_rate": round(completion_rate, 2),
            "readiness_indicators": {
                "avg_readiness_score": decimal_to_float(readiness_stats.avg_score) if readiness_stats.avg_score else None,
                "policy_adoption_rate": decimal_to_float(readiness_stats.policy_rate) if readiness_stats.policy_rate else None,
                "cms_adoption_rate": decimal_to_float(readiness_stats.cms_rate) if readiness_stats.cms_rate else None,
                "staff_training_rate": decimal_to_float(readiness_stats.training_rate) if readiness_stats.training_rate else None,
                "computer_access_rate": decimal_to_float(readiness_stats.computer_rate) if readiness_stats.computer_rate else None,
            } if readiness_stats else None,
        })

    # ========================================================================
    # SURVEY ENDPOINTS
    # ========================================================================

    @app.get("/api/surveys")
    def list_surveys():
        session = get_session()
        query = session.query(Survey)
        campaign_id = parse_int(request.args.get("campaign_id"))
        region_id = parse_int(request.args.get("region_id"))
        status = request.args.get("status")

        if campaign_id:
            query = query.filter(Survey.campaign_id == campaign_id)
        if status:
            query = query.filter(Survey.status == status)
        if region_id:
            query = query.join(Survey.institution).filter(
                Institution.region_id == region_id
            )

        surveys = query.all()
        return jsonify([
            {
                "id": s.id,
                "campaign_id": s.campaign_id,
                "institution_id": s.institution_id,
                "institution_name": s.institution.name if s.institution else None,
                "region_name": s.institution.region.name if s.institution and s.institution.region else None,
                "status": s.status,
                "kobo_submission_id": s.kobo_submission_id,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            }
            for s in surveys
        ])

    @app.post("/api/surveys")
    def create_survey():
        payload = request.get_json() or {}
        required = ["campaign_id", "institution_id"]
        if not all(k in payload for k in required):
            return jsonify({"error": "Missing required fields"}), 400
        session = get_session()
        survey = Survey(
            campaign_id=payload["campaign_id"],
            institution_id=payload["institution_id"],
            status=payload.get("status", "pending"),
            kobo_submission_id=payload.get("kobo_submission_id"),
        )
        session.add(survey)
        session.commit()
        return jsonify({"id": survey.id}), 201

    @app.put("/api/surveys/<int:survey_id>")
    def update_survey(survey_id: int):
        payload = request.get_json() or {}
        session = get_session()
        survey = session.query(Survey).get(survey_id)
        if not survey:
            return jsonify({"error": "Survey not found"}), 404

        status = payload.get("status")
        if status:
            if status not in {"pending", "in_progress", "completed"}:
                return jsonify({"error": "Invalid status"}), 400
            survey.status = status
            if status == "completed" and not survey.completed_at:
                survey.completed_at = func.now()

        session.commit()
        return jsonify({"message": "Updated"})

    @app.get("/api/surveys/<int:survey_id>")
    def get_survey(survey_id: int):
        session = get_session()
        survey = session.query(Survey).get(survey_id)
        if not survey:
            return jsonify({"error": "Survey not found"}), 404

        result = {
            "id": survey.id,
            "campaign_id": survey.campaign_id,
            "institution_id": survey.institution_id,
            "institution_name": survey.institution.name if survey.institution else None,
            "status": survey.status,
            "kobo_submission_id": survey.kobo_submission_id,
            "completed_at": survey.completed_at.isoformat() if survey.completed_at else None,
        }

        # Include readiness data if available
        if survey.readiness_data:
            rd = survey.readiness_data
            result["readiness_data"] = {
                "readiness_score": decimal_to_float(rd.readiness_score),
                "has_gbv_policy": rd.has_gbv_policy,
                "has_case_management_system": rd.has_case_management_system,
                "has_trained_staff": rd.has_trained_staff,
                "num_trained_staff": rd.num_trained_staff,
                "has_computers": rd.has_computers,
                "internet_connectivity": rd.internet_connectivity,
                "has_referral_pathway": rd.has_referral_pathway,
                "has_survivor_support": rd.has_survivor_support,
            }

        return jsonify(result)

    # ========================================================================
    # GBV READINESS ENDPOINTS
    # ========================================================================

    @app.get("/api/campaigns/<int:campaign_id>/readiness-summary")
    def readiness_summary(campaign_id: int):
        """Get detailed GBV ICT readiness indicators summary for a campaign."""
        session = get_session()

        stats = session.query(
            func.count(GBVReadinessData.id).label("total_assessed"),
            func.avg(GBVReadinessData.readiness_score).label("avg_score"),
            func.min(GBVReadinessData.readiness_score).label("min_score"),
            func.max(GBVReadinessData.readiness_score).label("max_score"),
            # Policy indicators
            func.sum(func.cast(GBVReadinessData.has_gbv_policy, Integer)).label("has_policy"),
            func.sum(func.cast(GBVReadinessData.has_gbv_action_plan, Integer)).label("has_action_plan"),
            func.sum(func.cast(GBVReadinessData.has_gbv_focal_point, Integer)).label("has_focal_point"),
            # HR indicators
            func.sum(func.cast(GBVReadinessData.has_trained_staff, Integer)).label("has_trained"),
            func.avg(GBVReadinessData.num_trained_staff).label("avg_trained_staff"),
            func.sum(func.cast(GBVReadinessData.has_dedicated_gbv_unit, Integer)).label("has_gbv_unit"),
            # ICT indicators
            func.sum(func.cast(GBVReadinessData.has_computers, Integer)).label("has_computers"),
            func.avg(GBVReadinessData.num_functional_computers).label("avg_computers"),
            func.sum(func.cast(GBVReadinessData.has_case_management_system, Integer)).label("has_cms"),
            # Service indicators
            func.sum(func.cast(GBVReadinessData.has_referral_pathway, Integer)).label("has_referral"),
            func.sum(func.cast(GBVReadinessData.has_survivor_support, Integer)).label("has_support"),
            func.sum(func.cast(GBVReadinessData.has_helpline, Integer)).label("has_helpline"),
        ).join(Survey, Survey.id == GBVReadinessData.survey_id).filter(
            Survey.campaign_id == campaign_id
        ).first()

        if not stats or not stats.total_assessed:
            return jsonify({"message": "No readiness data available"}), 404

        total = stats.total_assessed

        return jsonify({
            "campaign_id": campaign_id,
            "total_institutions_assessed": total,
            "readiness_scores": {
                "average": decimal_to_float(stats.avg_score),
                "minimum": decimal_to_float(stats.min_score),
                "maximum": decimal_to_float(stats.max_score),
            },
            "policy_governance": {
                "has_gbv_policy": stats.has_policy,
                "has_gbv_policy_pct": round(stats.has_policy / total * 100, 1),
                "has_action_plan": stats.has_action_plan,
                "has_action_plan_pct": round(stats.has_action_plan / total * 100, 1),
                "has_focal_point": stats.has_focal_point,
                "has_focal_point_pct": round(stats.has_focal_point / total * 100, 1),
            },
            "human_resources": {
                "has_trained_staff": stats.has_trained,
                "has_trained_staff_pct": round(stats.has_trained / total * 100, 1),
                "avg_trained_staff_per_institution": decimal_to_float(stats.avg_trained_staff),
                "has_dedicated_gbv_unit": stats.has_gbv_unit,
                "has_dedicated_gbv_unit_pct": round(stats.has_gbv_unit / total * 100, 1),
            },
            "ict_infrastructure": {
                "has_computers": stats.has_computers,
                "has_computers_pct": round(stats.has_computers / total * 100, 1),
                "avg_functional_computers": decimal_to_float(stats.avg_computers),
                "has_case_management_system": stats.has_cms,
                "has_case_management_system_pct": round(stats.has_cms / total * 100, 1),
            },
            "service_delivery": {
                "has_referral_pathway": stats.has_referral,
                "has_referral_pathway_pct": round(stats.has_referral / total * 100, 1),
                "has_survivor_support": stats.has_support,
                "has_survivor_support_pct": round(stats.has_support / total * 100, 1),
                "has_helpline": stats.has_helpline,
                "has_helpline_pct": round(stats.has_helpline / total * 100, 1),
            },
        })

    @app.get("/api/campaigns/<int:campaign_id>/regional-readiness")
    def regional_readiness(campaign_id: int):
        """Get GBV ICT readiness breakdown by region."""
        session = get_session()

        rows = session.query(
            Region.id.label("region_id"),
            Region.code.label("region_code"),
            Region.name.label("region_name"),
            func.count(GBVReadinessData.id).label("assessed"),
            func.avg(GBVReadinessData.readiness_score).label("avg_score"),
            func.sum(func.cast(GBVReadinessData.has_gbv_policy, Integer)).label("has_policy"),
            func.sum(func.cast(GBVReadinessData.has_case_management_system, Integer)).label("has_cms"),
            func.sum(func.cast(GBVReadinessData.has_trained_staff, Integer)).label("has_trained"),
        ).outerjoin(Institution, Institution.region_id == Region.id).outerjoin(
            Survey, (Survey.institution_id == Institution.id) & (Survey.campaign_id == campaign_id)
        ).outerjoin(
            GBVReadinessData, GBVReadinessData.survey_id == Survey.id
        ).group_by(Region.id, Region.code, Region.name).all()

        return jsonify([
            {
                "region_id": r.region_id,
                "region_code": r.region_code,
                "region_name": r.region_name,
                "institutions_assessed": r.assessed or 0,
                "avg_readiness_score": decimal_to_float(r.avg_score) if r.avg_score else None,
                "policy_adoption_pct": round((r.has_policy or 0) / r.assessed * 100, 1) if r.assessed else None,
                "cms_adoption_pct": round((r.has_cms or 0) / r.assessed * 100, 1) if r.assessed else None,
                "training_pct": round((r.has_trained or 0) / r.assessed * 100, 1) if r.assessed else None,
            }
            for r in rows
        ])

    # ========================================================================
    # KOBOTOOLBOX SYNC ENDPOINTS
    # ========================================================================

    @app.post("/api/campaigns/<int:campaign_id>/sync-kobo")
    def sync_kobo(campaign_id: int):
        """Trigger synchronization with KoBoToolbox for a campaign."""
        session = get_session()
        campaign = session.query(SurveyCampaign).get(campaign_id)

        if not campaign:
            return jsonify({"error": "Campaign not found"}), 404

        if not campaign.kobo_asset_uid:
            return jsonify({"error": "Campaign has no KoBoToolbox asset UID configured"}), 400

        # Import here to avoid circular imports
        from kobo_client import KoBoToolboxClient, GBVReadinessDataTransformer

        # Create sync log
        sync_log = KoboSyncLog(
            campaign_id=campaign_id,
            sync_started_at=datetime.utcnow(),
            status="running",
        )
        session.add(sync_log)
        session.commit()

        try:
            client = KoBoToolboxClient()
            transformer = GBVReadinessDataTransformer()

            submissions = client.get_submissions(campaign.kobo_asset_uid)
            sync_log.submissions_fetched = len(submissions)

            new_records = 0
            updated_records = 0
            errors = []

            for submission in submissions:
                try:
                    record = transformer.transform_submission(submission)
                    kobo_id = record.get("kobo_submission_id")

                    if not kobo_id:
                        continue

                    # Check if submission already exists
                    existing = session.query(Survey).filter_by(
                        kobo_submission_id=str(kobo_id)
                    ).first()

                    if existing:
                        # Update existing record
                        existing.status = "completed"
                        existing.completed_at = record.get("submission_time")
                        updated_records += 1
                    else:
                        # Find or create region
                        region = None
                        if record.get("region_code"):
                            region = session.query(Region).filter_by(
                                code=record["region_code"]
                            ).first()

                        if not region:
                            errors.append(f"Unknown region: {record.get('region_name')}")
                            continue

                        # Find or create institution
                        institution = session.query(Institution).filter_by(
                            name=record["institution_name"],
                            region_id=region.id,
                        ).first()

                        if not institution:
                            institution = Institution(
                                name=record["institution_name"],
                                type=record.get("institution_type", "other"),
                                region_id=region.id,
                            )
                            session.add(institution)
                            session.flush()

                        # Create survey record
                        survey = Survey(
                            campaign_id=campaign_id,
                            institution_id=institution.id,
                            status="completed",
                            kobo_submission_id=str(kobo_id),
                            completed_at=record.get("submission_time"),
                        )
                        session.add(survey)
                        session.flush()

                        # Create readiness data
                        readiness = GBVReadinessData(
                            survey_id=survey.id,
                            has_gbv_policy=record.get("has_gbv_policy", False),
                            has_ict_infrastructure=record.get("has_ict_infrastructure", False),
                            has_case_management_system=record.get("has_case_management_system", False),
                            has_data_protection_policy=record.get("has_data_protection_policy", False),
                            has_trained_staff=record.get("has_trained_staff", False),
                            num_trained_staff=record.get("num_trained_staff", 0),
                            has_referral_pathway=record.get("has_referral_pathway", False),
                            has_reporting_mechanism=record.get("has_reporting_mechanism", False),
                            has_survivor_support=record.get("has_survivor_support", False),
                            has_monitoring_system=record.get("has_monitoring_system", False),
                            internet_connectivity=record.get("internet_connectivity", "none"),
                            has_computers=record.get("has_computers", False),
                            num_computers=record.get("num_computers", 0),
                            has_partnerships=record.get("has_partnerships", False),
                            respondent_name=record.get("respondent_name"),
                            respondent_position=record.get("respondent_position"),
                        )
                        session.add(readiness)
                        new_records += 1

                except Exception as e:
                    errors.append(str(e))

            # Update sync log
            sync_log.new_records = new_records
            sync_log.updated_records = updated_records
            sync_log.errors_count = len(errors)
            sync_log.error_details = {"errors": errors[:50]}  # Limit stored errors
            sync_log.sync_completed_at = datetime.utcnow()
            sync_log.status = "completed"

            session.commit()

            return jsonify({
                "message": "Sync completed",
                "submissions_fetched": sync_log.submissions_fetched,
                "new_records": new_records,
                "updated_records": updated_records,
                "errors": len(errors),
            })

        except Exception as e:
            sync_log.status = "failed"
            sync_log.error_details = {"error": str(e)}
            sync_log.sync_completed_at = datetime.utcnow()
            session.commit()
            return jsonify({"error": str(e)}), 500

    @app.get("/api/campaigns/<int:campaign_id>/sync-status")
    def sync_status(campaign_id: int):
        """Get the latest sync status for a campaign."""
        session = get_session()
        log = session.query(KoboSyncLog).filter_by(
            campaign_id=campaign_id
        ).order_by(KoboSyncLog.created_at.desc()).first()

        if not log:
            return jsonify({"message": "No sync history found"}), 404

        return jsonify({
            "sync_id": log.id,
            "status": log.status,
            "started_at": log.sync_started_at.isoformat() if log.sync_started_at else None,
            "completed_at": log.sync_completed_at.isoformat() if log.sync_completed_at else None,
            "submissions_fetched": log.submissions_fetched,
            "new_records": log.new_records,
            "updated_records": log.updated_records,
            "errors_count": log.errors_count,
        })

    # ========================================================================
    # REFERENCE DATA ENDPOINTS
    # ========================================================================

    @app.get("/api/regions")
    def list_regions():
        session = get_session()
        regions = session.query(Region).order_by(Region.name).all()
        return jsonify([
            {"id": r.id, "code": r.code, "name": r.name}
            for r in regions
        ])

    @app.get("/api/institutions")
    def list_institutions():
        session = get_session()
        query = session.query(Institution)
        region_id = parse_int(request.args.get("region_id"))
        inst_type = request.args.get("type")

        if region_id:
            query = query.filter(Institution.region_id == region_id)
        if inst_type:
            query = query.filter(Institution.type == inst_type)

        institutions = query.order_by(Institution.name).all()
        return jsonify([
            {
                "id": i.id,
                "name": i.name,
                "type": i.type,
                "region_id": i.region_id,
                "region_name": i.region.name if i.region else None,
                "contact_person": i.contact_person,
                "contact_email": i.contact_email,
            }
            for i in institutions
        ])

    @app.post("/api/institutions")
    def create_institution():
        payload = request.get_json() or {}
        required = ["name", "type", "region_id"]
        if not all(k in payload for k in required):
            return jsonify({"error": "Missing required fields"}), 400

        session = get_session()
        inst = Institution(
            name=payload["name"],
            type=payload["type"],
            region_id=payload["region_id"],
            address=payload.get("address"),
            contact_person=payload.get("contact_person"),
            contact_email=payload.get("contact_email"),
            contact_phone=payload.get("contact_phone"),
        )
        session.add(inst)
        session.commit()
        return jsonify({"id": inst.id}), 201

    # ========================================================================
    # HEALTH CHECK
    # ========================================================================

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "version": "2.0"})

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
