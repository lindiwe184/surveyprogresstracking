"""
KoBoToolbox API Client for GBV ICT Readiness Survey Data

This module handles authentication and data retrieval from KoBoToolbox API.
It fetches survey submissions and transforms them into the format needed
for the survey tracking database.
"""

import os
import logging
from datetime import datetime
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)


class KoBoToolboxClient:
    """Client for interacting with KoBoToolbox API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_token: Optional[str] = None,
    ):
        """
        Initialize the KoBoToolbox client.

        Args:
            base_url: KoBoToolbox API base URL (default from env)
            api_token: API token for authentication (default from env)
        """
        self.base_url = (
            base_url or os.getenv("KOBO_API_URL", "https://kf.kobotoolbox.org")
        ).rstrip("/")
        self.api_token = api_token or os.getenv("KOBO_API_TOKEN", "")

        if not self.api_token:
            logger.warning(
                "KOBO_API_TOKEN not set. API calls will fail authentication."
            )

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Token {self.api_token}",
                "Accept": "application/json",
            }
        )

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None,
    ) -> dict:
        """
        Make an authenticated request to the KoBoToolbox API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON body data

        Returns:
            Response JSON as dictionary

        Raises:
            requests.HTTPError: If request fails
        """
        url = f"{self.base_url}{endpoint}"
        response = self.session.request(
            method=method,
            url=url,
            params=params,
            json=json_data,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def get_assets(self) -> list[dict]:
        """
        Get all survey assets (forms) accessible to the authenticated user.

        Returns:
            List of asset objects
        """
        data = self._request("GET", "/api/v2/assets/")
        return data.get("results", [])

    def get_asset(self, asset_uid: str) -> dict:
        """
        Get details for a specific asset.

        Args:
            asset_uid: The unique identifier of the asset

        Returns:
            Asset details dictionary
        """
        return self._request("GET", f"/api/v2/assets/{asset_uid}/")

    def get_submissions(
        self,
        asset_uid: str,
        start: int = 0,
        limit: int = 30000,
        query: Optional[dict] = None,
    ) -> list[dict]:
        """
        Get survey submissions for a specific asset.

        Args:
            asset_uid: The unique identifier of the asset/form
            start: Starting index for pagination
            limit: Maximum number of results
            query: Optional filter query

        Returns:
            List of submission dictionaries
        """
        params = {"start": start, "limit": limit}
        if query:
            import json
            params["query"] = json.dumps(query)

        data = self._request("GET", f"/api/v2/assets/{asset_uid}/data/", params=params)
        return data.get("results", [])

    def get_submission_count(self, asset_uid: str) -> int:
        """
        Get total count of submissions for an asset.

        Args:
            asset_uid: The unique identifier of the asset

        Returns:
            Total submission count
        """
        data = self._request("GET", f"/api/v2/assets/{asset_uid}/data/", params={"limit": 1})
        return data.get("count", 0)

    def get_submissions_since(
        self,
        asset_uid: str,
        since_date: datetime,
    ) -> list[dict]:
        """
        Get submissions created or modified since a specific date.

        Args:
            asset_uid: The unique identifier of the asset
            since_date: Datetime to filter from

        Returns:
            List of submission dictionaries
        """
        query = {
            "_submission_time": {"$gte": since_date.isoformat()}
        }
        return self.get_submissions(asset_uid, query=query)


class GBVReadinessDataTransformer:
    """
    Transform KoBoToolbox submission data into GBV ICT Readiness survey records.

    Maps KoBoToolbox field names to database schema fields.
    """

    # Mapping of Namibian region names to region codes
    REGION_CODE_MAP = {
        "zambezi": "CA",
        "caprivi": "CA",  # Old name
        "erongo": "ER",
        "hardap": "HA",
        "karas": "KA",
        "//karas": "KA",
        "kharas": "KA",
        "kavango east": "KE",
        "kavango_east": "KE",
        "kavango west": "KW",
        "kavango_west": "KW",
        "khomas": "KH",
        "kunene": "KU",
        "ohangwena": "OW",
        "omaheke": "OH",
        "omusati": "OS",
        "oshana": "ON",
        "oshikoto": "OT",
        "otjozondjupa": "OD",
    }

    # KoBoToolbox field mappings for GBV ICT Readiness indicators
    # Adjust these based on your actual KoBoToolbox form field names
    FIELD_MAPPINGS = {
        # Core identifiers
        "institution_name": [
            "institution_name",
            "name_of_institution",
            "org_name",
            "institution",
        ],
        "institution_type": [
            "institution_type",
            "type_of_institution",
            "org_type",
            "sector",
        ],
        "region": ["region", "region_name", "location/region"],
        "submission_date": ["_submission_time", "submission_date", "date"],

        # GBV ICT Readiness Indicators
        "has_gbv_policy": [
            "has_gbv_policy",
            "gbv_policy_exists",
            "policy/gbv_policy",
        ],
        "has_ict_infrastructure": [
            "has_ict_infrastructure",
            "ict_infrastructure",
            "infrastructure/ict",
        ],
        "has_case_management_system": [
            "case_management_system",
            "cms_exists",
            "has_cms",
        ],
        "has_data_protection_policy": [
            "data_protection_policy",
            "data_privacy_policy",
            "has_data_protection",
        ],
        "has_trained_staff": [
            "trained_staff",
            "staff_trained",
            "has_trained_staff",
        ],
        "num_trained_staff": [
            "num_trained_staff",
            "number_trained",
            "trained_staff_count",
        ],
        "has_referral_pathway": [
            "referral_pathway",
            "has_referral_pathway",
            "referral_system",
        ],
        "has_reporting_mechanism": [
            "reporting_mechanism",
            "has_reporting_mechanism",
            "complaint_mechanism",
        ],
        "has_survivor_support": [
            "survivor_support",
            "has_survivor_support",
            "victim_support",
        ],
        "has_monitoring_system": [
            "monitoring_system",
            "has_monitoring",
            "m_and_e_system",
        ],
        "internet_connectivity": [
            "internet_connectivity",
            "internet_access",
            "connectivity",
        ],
        "has_computers": [
            "has_computers",
            "computer_access",
            "computers_available",
        ],
        "num_computers": [
            "num_computers",
            "number_of_computers",
            "computer_count",
        ],
        "has_dedicated_gbv_budget": [
            "gbv_budget",
            "has_gbv_budget",
            "dedicated_budget",
        ],
        "has_partnerships": [
            "partnerships",
            "has_partnerships",
            "partner_organizations",
        ],
        "respondent_name": [
            "respondent_name",
            "respondent",
            "enumerator",
        ],
        "respondent_position": [
            "respondent_position",
            "position",
            "job_title",
        ],
        "respondent_contact": [
            "contact",
            "phone",
            "email",
        ],
    }

    def __init__(self):
        """Initialize the transformer."""
        pass

    def _get_field_value(
        self,
        submission: dict,
        field_key: str,
        default: Any = None,
    ) -> Any:
        """
        Get a field value from submission using multiple possible field names.

        Args:
            submission: KoBoToolbox submission dictionary
            field_key: Key in FIELD_MAPPINGS
            default: Default value if not found

        Returns:
            Field value or default
        """
        possible_names = self.FIELD_MAPPINGS.get(field_key, [field_key])
        for name in possible_names:
            if name in submission:
                return submission[name]
            # Handle nested fields (e.g., "group/field")
            parts = name.split("/")
            val = submission
            for part in parts:
                if isinstance(val, dict) and part in val:
                    val = val[part]
                else:
                    val = None
                    break
            if val is not None:
                return val
        return default

    def _normalize_region(self, region_str: str) -> Optional[str]:
        """
        Normalize region name to region code.

        Args:
            region_str: Region name from submission

        Returns:
            Two-letter region code or None
        """
        if not region_str:
            return None
        normalized = region_str.lower().strip().replace("-", " ").replace("_", " ")
        return self.REGION_CODE_MAP.get(normalized)

    def _parse_boolean(self, value: Any) -> bool:
        """Convert various representations to boolean."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("yes", "true", "1", "y", "oui")
        if isinstance(value, (int, float)):
            return bool(value)
        return False

    def _parse_int(self, value: Any, default: int = 0) -> int:
        """Convert value to integer."""
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def transform_submission(self, submission: dict) -> dict:
        """
        Transform a KoBoToolbox submission into a database record format.

        Args:
            submission: Raw KoBoToolbox submission

        Returns:
            Dictionary ready for database insertion
        """
        region_name = self._get_field_value(submission, "region", "")
        region_code = self._normalize_region(region_name)

        # Parse submission time
        submission_time_str = self._get_field_value(submission, "submission_date")
        try:
            submission_time = datetime.fromisoformat(
                submission_time_str.replace("Z", "+00:00")
            ) if submission_time_str else datetime.utcnow()
        except (ValueError, AttributeError):
            submission_time = datetime.utcnow()

        return {
            # Core fields
            "kobo_submission_id": submission.get("_id"),
            "institution_name": self._get_field_value(submission, "institution_name", "Unknown"),
            "institution_type": self._get_field_value(submission, "institution_type", "Other"),
            "region_code": region_code,
            "region_name": region_name,
            "submission_time": submission_time,

            # GBV ICT Readiness Indicators
            "has_gbv_policy": self._parse_boolean(
                self._get_field_value(submission, "has_gbv_policy")
            ),
            "has_ict_infrastructure": self._parse_boolean(
                self._get_field_value(submission, "has_ict_infrastructure")
            ),
            "has_case_management_system": self._parse_boolean(
                self._get_field_value(submission, "has_case_management_system")
            ),
            "has_data_protection_policy": self._parse_boolean(
                self._get_field_value(submission, "has_data_protection_policy")
            ),
            "has_trained_staff": self._parse_boolean(
                self._get_field_value(submission, "has_trained_staff")
            ),
            "num_trained_staff": self._parse_int(
                self._get_field_value(submission, "num_trained_staff")
            ),
            "has_referral_pathway": self._parse_boolean(
                self._get_field_value(submission, "has_referral_pathway")
            ),
            "has_reporting_mechanism": self._parse_boolean(
                self._get_field_value(submission, "has_reporting_mechanism")
            ),
            "has_survivor_support": self._parse_boolean(
                self._get_field_value(submission, "has_survivor_support")
            ),
            "has_monitoring_system": self._parse_boolean(
                self._get_field_value(submission, "has_monitoring_system")
            ),
            "internet_connectivity": self._get_field_value(
                submission, "internet_connectivity", "none"
            ),
            "has_computers": self._parse_boolean(
                self._get_field_value(submission, "has_computers")
            ),
            "num_computers": self._parse_int(
                self._get_field_value(submission, "num_computers")
            ),
            "has_dedicated_gbv_budget": self._parse_boolean(
                self._get_field_value(submission, "has_dedicated_gbv_budget")
            ),
            "has_partnerships": self._parse_boolean(
                self._get_field_value(submission, "has_partnerships")
            ),

            # Respondent info
            "respondent_name": self._get_field_value(submission, "respondent_name"),
            "respondent_position": self._get_field_value(submission, "respondent_position"),
            "respondent_contact": self._get_field_value(submission, "respondent_contact"),

            # Raw data for reference
            "raw_submission": submission,
        }

    def transform_submissions(self, submissions: list[dict]) -> list[dict]:
        """
        Transform multiple submissions.

        Args:
            submissions: List of raw KoBoToolbox submissions

        Returns:
            List of transformed records
        """
        return [self.transform_submission(s) for s in submissions]


def sync_kobo_data(
    db_session,
    asset_uid: str,
    campaign_id: int,
    client: Optional[KoBoToolboxClient] = None,
    transformer: Optional[GBVReadinessDataTransformer] = None,
) -> dict:
    """
    Synchronize data from KoBoToolbox to the local database.

    Args:
        db_session: SQLAlchemy database session
        asset_uid: KoBoToolbox asset/form UID
        campaign_id: Campaign ID to associate surveys with
        client: Optional KoBoToolbox client instance
        transformer: Optional data transformer instance

    Returns:
        Dictionary with sync statistics
    """
    from app import Region, Institution, Survey, GBVReadinessData

    client = client or KoBoToolboxClient()
    transformer = transformer or GBVReadinessDataTransformer()

    stats = {
        "total_fetched": 0,
        "new_institutions": 0,
        "new_surveys": 0,
        "updated_surveys": 0,
        "errors": [],
    }

    try:
        submissions = client.get_submissions(asset_uid)
        stats["total_fetched"] = len(submissions)

        for submission in submissions:
            try:
                record = transformer.transform_submission(submission)
                kobo_id = record["kobo_submission_id"]

                # Find or create region
                region = None
                if record["region_code"]:
                    region = db_session.query(Region).filter_by(
                        code=record["region_code"]
                    ).first()

                if not region:
                    # Try to find by name similarity or skip
                    stats["errors"].append(
                        f"Unknown region for submission {kobo_id}: {record['region_name']}"
                    )
                    continue

                # Find or create institution
                institution = db_session.query(Institution).filter_by(
                    name=record["institution_name"],
                    region_id=region.id,
                ).first()

                if not institution:
                    institution = Institution(
                        name=record["institution_name"],
                        type=record["institution_type"],
                        region_id=region.id,
                    )
                    db_session.add(institution)
                    db_session.flush()
                    stats["new_institutions"] += 1

                # Check for existing survey by kobo_submission_id
                existing_survey = db_session.query(Survey).filter_by(
                    kobo_submission_id=kobo_id
                ).first() if kobo_id else None

                if existing_survey:
                    # Update existing survey
                    existing_survey.status = "completed"
                    existing_survey.completed_at = record["submission_time"]
                    stats["updated_surveys"] += 1
                else:
                    # Create new survey
                    survey = Survey(
                        campaign_id=campaign_id,
                        institution_id=institution.id,
                        status="completed",
                        completed_at=record["submission_time"],
                        kobo_submission_id=kobo_id,
                    )
                    db_session.add(survey)
                    db_session.flush()
                    stats["new_surveys"] += 1

                    # Store GBV readiness data
                    readiness_data = GBVReadinessData(
                        survey_id=survey.id,
                        has_gbv_policy=record["has_gbv_policy"],
                        has_ict_infrastructure=record["has_ict_infrastructure"],
                        has_case_management_system=record["has_case_management_system"],
                        has_data_protection_policy=record["has_data_protection_policy"],
                        has_trained_staff=record["has_trained_staff"],
                        num_trained_staff=record["num_trained_staff"],
                        has_referral_pathway=record["has_referral_pathway"],
                        has_reporting_mechanism=record["has_reporting_mechanism"],
                        has_survivor_support=record["has_survivor_support"],
                        has_monitoring_system=record["has_monitoring_system"],
                        internet_connectivity=record["internet_connectivity"],
                        has_computers=record["has_computers"],
                        num_computers=record["num_computers"],
                        has_dedicated_gbv_budget=record["has_dedicated_gbv_budget"],
                        has_partnerships=record["has_partnerships"],
                        respondent_name=record["respondent_name"],
                        respondent_position=record["respondent_position"],
                    )
                    db_session.add(readiness_data)

            except Exception as e:
                stats["errors"].append(f"Error processing submission: {str(e)}")
                continue

        db_session.commit()

    except requests.HTTPError as e:
        stats["errors"].append(f"KoBoToolbox API error: {str(e)}")
    except Exception as e:
        stats["errors"].append(f"Sync error: {str(e)}")
        db_session.rollback()

    return stats
