# API Documentation

## Namibia GBV ICT Readiness Survey Tracking System

**Base URL:** `http://localhost:5000/api`

**Version:** 2.0

---

## Authentication

Currently, the API does not require authentication. For production deployments, implement API key or OAuth2 authentication.

---

## Endpoints

### Health Check

#### `GET /api/health`

Check API health status.

**Response:**
```json
{
  "status": "ok",
  "version": "2.0"
}
```

---

## Campaign Endpoints

### List Campaigns

#### `GET /api/campaigns`

Get all survey campaigns.

**Response:**
```json
[
  {
    "id": 1,
    "name": "GBV ICT Readiness Assessment 2024",
    "description": "National assessment of institutional GBV ICT readiness",
    "kobo_asset_uid": "aXyz123abc",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "target_institutions": 500,
    "is_active": true
  }
]
```

---

### Create Campaign

#### `POST /api/campaigns`

Create a new survey campaign.

**Request Body:**
```json
{
  "name": "GBV ICT Readiness Assessment 2024",
  "description": "Optional description",
  "kobo_asset_uid": "aXyz123abc",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "target_institutions": 500
}
```

**Required fields:** `name`, `start_date`, `end_date`

**Response:** `201 Created`
```json
{
  "id": 1
}
```

---

### Get Campaign

#### `GET /api/campaigns/{id}`

Get campaign details.

**Response:**
```json
{
  "id": 1,
  "name": "GBV ICT Readiness Assessment 2024",
  "description": "National assessment",
  "kobo_asset_uid": "aXyz123abc",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "target_institutions": 500,
  "is_active": true
}
```

---

### Update Campaign

#### `PUT /api/campaigns/{id}`

Update campaign details.

**Request Body:**
```json
{
  "name": "Updated name",
  "kobo_asset_uid": "newAssetUID",
  "target_institutions": 600,
  "is_active": false
}
```

**Response:**
```json
{
  "message": "Updated"
}
```

---

### National Summary

#### `GET /api/campaigns/{id}/national-summary`

Get national-level statistics for a campaign.

**Response:**
```json
{
  "campaign_id": 1,
  "campaign_name": "GBV ICT Readiness Assessment 2024",
  "target_institutions": 500,
  "total_surveys": 350,
  "completed_surveys": 280,
  "in_progress_surveys": 45,
  "pending_surveys": 25,
  "completion_rate": 56.0,
  "avg_readiness_score": 62.5
}
```

---

### Regional Summary

#### `GET /api/campaigns/{id}/regional-summary`

Get survey statistics broken down by region.

**Response:**
```json
[
  {
    "region_id": 1,
    "region_code": "KH",
    "region_name": "Khomas",
    "total_surveys": 45,
    "completed_surveys": 38,
    "completion_rate": 84.44,
    "avg_readiness_score": 68.5
  },
  {
    "region_id": 2,
    "region_code": "ER",
    "region_name": "Erongo",
    "total_surveys": 30,
    "completed_surveys": 25,
    "completion_rate": 83.33,
    "avg_readiness_score": 55.2
  }
]
```

---

### Daily Progress

#### `GET /api/campaigns/{id}/daily-progress`

Get daily completion trend.

**Query Parameters:**
- `days` (optional, default: 30) - Number of days to include

**Response:**
```json
[
  {
    "date": "2024-03-01",
    "daily_completed": 5,
    "cumulative_completed": 250
  },
  {
    "date": "2024-03-02",
    "daily_completed": 8,
    "cumulative_completed": 258
  }
]
```

---

### Progress Report

#### `GET /api/campaigns/{id}/progress-report`

Get comprehensive campaign progress report.

**Response:**
```json
{
  "campaign_id": 1,
  "campaign_name": "GBV ICT Readiness Assessment 2024",
  "target_institutions": 500,
  "total_surveys": 350,
  "completed": 280,
  "in_progress": 45,
  "pending": 25,
  "completion_rate": 56.0,
  "readiness_indicators": {
    "avg_readiness_score": 62.5,
    "policy_adoption_rate": 78.5,
    "cms_adoption_rate": 45.2,
    "staff_training_rate": 65.8,
    "computer_access_rate": 82.1
  }
}
```

---

### GBV Readiness Summary

#### `GET /api/campaigns/{id}/readiness-summary`

Get detailed GBV ICT readiness indicators summary.

**Response:**
```json
{
  "campaign_id": 1,
  "total_institutions_assessed": 280,
  "readiness_scores": {
    "average": 62.5,
    "minimum": 18.0,
    "maximum": 95.0
  },
  "policy_governance": {
    "has_gbv_policy": 220,
    "has_gbv_policy_pct": 78.5,
    "has_action_plan": 180,
    "has_action_plan_pct": 64.3,
    "has_focal_point": 195,
    "has_focal_point_pct": 69.6
  },
  "human_resources": {
    "has_trained_staff": 184,
    "has_trained_staff_pct": 65.7,
    "avg_trained_staff_per_institution": 3.2,
    "has_dedicated_gbv_unit": 95,
    "has_dedicated_gbv_unit_pct": 33.9
  },
  "ict_infrastructure": {
    "has_computers": 230,
    "has_computers_pct": 82.1,
    "avg_functional_computers": 4.5,
    "has_case_management_system": 126,
    "has_case_management_system_pct": 45.0
  },
  "service_delivery": {
    "has_referral_pathway": 210,
    "has_referral_pathway_pct": 75.0,
    "has_survivor_support": 175,
    "has_survivor_support_pct": 62.5,
    "has_helpline": 85,
    "has_helpline_pct": 30.4
  }
}
```

---

### Regional Readiness

#### `GET /api/campaigns/{id}/regional-readiness`

Get GBV ICT readiness breakdown by region.

**Response:**
```json
[
  {
    "region_id": 1,
    "region_code": "KH",
    "region_name": "Khomas",
    "institutions_assessed": 38,
    "avg_readiness_score": 68.5,
    "policy_adoption_pct": 84.2,
    "cms_adoption_pct": 52.6,
    "training_pct": 73.7
  }
]
```

---

### Sync from KoBoToolbox

#### `POST /api/campaigns/{id}/sync-kobo`

Trigger data synchronization from KoBoToolbox.

**Prerequisites:**
- Campaign must have `kobo_asset_uid` configured
- `KOBO_API_TOKEN` environment variable must be set

**Response:**
```json
{
  "message": "Sync completed",
  "submissions_fetched": 150,
  "new_records": 45,
  "updated_records": 20,
  "errors": 3
}
```

**Error Response (400):**
```json
{
  "error": "Campaign has no KoBoToolbox asset UID configured"
}
```

---

### Sync Status

#### `GET /api/campaigns/{id}/sync-status`

Get the latest sync status for a campaign.

**Response:**
```json
{
  "sync_id": 5,
  "status": "completed",
  "started_at": "2024-03-15T10:30:00Z",
  "completed_at": "2024-03-15T10:32:45Z",
  "submissions_fetched": 150,
  "new_records": 45,
  "updated_records": 20,
  "errors_count": 3
}
```

---

## Survey Endpoints

### List Surveys

#### `GET /api/surveys`

Get surveys with optional filtering.

**Query Parameters:**
- `campaign_id` (optional) - Filter by campaign
- `region_id` (optional) - Filter by region
- `status` (optional) - Filter by status: `pending`, `in_progress`, `completed`

**Response:**
```json
[
  {
    "id": 1,
    "campaign_id": 1,
    "institution_id": 5,
    "institution_name": "Khomas Regional Hospital",
    "region_name": "Khomas",
    "status": "completed",
    "kobo_submission_id": "12345678",
    "completed_at": "2024-03-10T14:30:00Z"
  }
]
```

---

### Create Survey

#### `POST /api/surveys`

Create a new survey record.

**Request Body:**
```json
{
  "campaign_id": 1,
  "institution_id": 5,
  "status": "pending",
  "kobo_submission_id": "optional_kobo_id"
}
```

**Required fields:** `campaign_id`, `institution_id`

**Response:** `201 Created`
```json
{
  "id": 1
}
```

---

### Get Survey

#### `GET /api/surveys/{id}`

Get survey details including readiness data.

**Response:**
```json
{
  "id": 1,
  "campaign_id": 1,
  "institution_id": 5,
  "institution_name": "Khomas Regional Hospital",
  "status": "completed",
  "kobo_submission_id": "12345678",
  "completed_at": "2024-03-10T14:30:00Z",
  "readiness_data": {
    "readiness_score": 72.5,
    "has_gbv_policy": true,
    "has_case_management_system": true,
    "has_trained_staff": true,
    "num_trained_staff": 5,
    "has_computers": true,
    "internet_connectivity": "good",
    "has_referral_pathway": true,
    "has_survivor_support": true
  }
}
```

---

### Update Survey

#### `PUT /api/surveys/{id}`

Update survey status.

**Request Body:**
```json
{
  "status": "completed"
}
```

**Valid status values:** `pending`, `in_progress`, `completed`

**Response:**
```json
{
  "message": "Updated"
}
```

---

## Reference Data Endpoints

### List Regions

#### `GET /api/regions`

Get all 14 Namibian regions.

**Response:**
```json
[
  {"id": 1, "code": "CA", "name": "Zambezi"},
  {"id": 2, "code": "ER", "name": "Erongo"},
  {"id": 3, "code": "HA", "name": "Hardap"},
  {"id": 4, "code": "KA", "name": "Karas"},
  {"id": 5, "code": "KE", "name": "Kavango East"},
  {"id": 6, "code": "KW", "name": "Kavango West"},
  {"id": 7, "code": "KH", "name": "Khomas"},
  {"id": 8, "code": "KU", "name": "Kunene"},
  {"id": 9, "code": "OW", "name": "Ohangwena"},
  {"id": 10, "code": "OH", "name": "Omaheke"},
  {"id": 11, "code": "OS", "name": "Omusati"},
  {"id": 12, "code": "ON", "name": "Oshana"},
  {"id": 13, "code": "OT", "name": "Oshikoto"},
  {"id": 14, "code": "OD", "name": "Otjozondjupa"}
]
```

---

### List Institutions

#### `GET /api/institutions`

Get institutions with optional filtering.

**Query Parameters:**
- `region_id` (optional) - Filter by region
- `type` (optional) - Filter by sector type

**Response:**
```json
[
  {
    "id": 1,
    "name": "Khomas Regional Hospital",
    "type": "health",
    "region_id": 7,
    "region_name": "Khomas",
    "contact_person": "Dr. Jane Smith",
    "contact_email": "jane.smith@health.gov.na"
  }
]
```

---

### Create Institution

#### `POST /api/institutions`

Add a new institution.

**Request Body:**
```json
{
  "name": "Khomas Regional Hospital",
  "type": "health",
  "region_id": 7,
  "address": "123 Independence Ave, Windhoek",
  "contact_person": "Dr. Jane Smith",
  "contact_email": "jane.smith@health.gov.na",
  "contact_phone": "+264 61 123456"
}
```

**Required fields:** `name`, `type`, `region_id`

**Valid type values:** `government`, `health`, `education`, `police`, `justice`, `social_welfare`, `ngo`, `private`, `community`, `other`

**Response:** `201 Created`
```json
{
  "id": 1
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "error": "Missing required fields"
}
```

### 404 Not Found
```json
{
  "error": "Campaign not found"
}
```

### 500 Internal Server Error
```json
{
  "error": "Database connection failed"
}
```

---

## Rate Limiting

No rate limiting is currently implemented. For production, consider implementing rate limiting at the API gateway level.

---

## CORS

CORS is enabled for all `/api/*` endpoints. Configure allowed origins via the `CORS_ORIGINS` environment variable.