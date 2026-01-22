# Namibia GBV ICT Readiness Survey Tracking System

A comprehensive dashboard system for tracking Gender-Based Violence (GBV) ICT Readiness survey completion across Namibia's 14 regions. The system integrates with **KoBoToolbox** to automatically fetch survey submissions and calculate institutional readiness scores.

---

## Features

- **KoBoToolbox Integration**: Automatic data synchronization from KoBoToolbox surveys
- **Real-time Progress Tracking**: Monitor survey completion at national and regional levels
- **GBV ICT Readiness Scoring**: Calculate and visualize institutional readiness across 10 domains
- **Regional Analysis**: Compare progress and readiness across Namibia's 14 regions
- **Daily Trends**: Track completion rates over time
- **Interactive Dashboard**: Streamlit-based visualization with charts and maps

---

## Project Structure

```
survey_tracking_system/
├── backend/
│   ├── app.py              # Flask REST API
│   ├── kobo_client.py      # KoBoToolbox API integration
│   ├── config.py           # Configuration management
│   ├── requirements.txt    # Python dependencies
│   └── env.template        # Environment variables template
├── frontend/
│   ├── dashboard.py        # Streamlit dashboard
│   ├── config.py           # Frontend configuration
│   └── requirements.txt    # Frontend dependencies
├── database/
│   ├── schema_v2.sql       # PostgreSQL schema with GBV indicators
│   ├── sample_data.sql     # Sample data for testing
│   └── migration_scripts/  # Database migrations
├── docs/
│   ├── README.md           # This file
│   ├── API_DOCUMENTATION.md
│   ├── USER_GUIDE.md
│   └── GBV_ICT_READINESS_INDICATORS.md  # Complete indicator framework
└── tests/
    ├── test_api.py
    └── test_database.py
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 14+
- KoBoToolbox account (for live data sync)

### 1. Database Setup

```bash
# Create database and user
psql -U postgres
CREATE DATABASE survey_tracking;
CREATE USER survey_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE survey_tracking TO survey_user;
\q

# Apply schema
cd survey_tracking_system
psql -U survey_user -d survey_tracking -f database/schema_v2.sql
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy env.template .env  # Windows
# cp env.template .env  # Linux/Mac

# Edit .env with your settings (database URL, KoBoToolbox token)
notepad .env

# Run backend
python app.py
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies (in same or new venv)
pip install -r requirements.txt

# Run dashboard
streamlit run dashboard.py
```

### 4. Access the System

- **API**: http://localhost:5000/api/health
- **Dashboard**: http://localhost:8501

---

## KoBoToolbox Integration

### Getting Your API Token

1. Log in to [KoBoToolbox](https://kf.kobotoolbox.org)
2. Go to **Account Settings** → **Security**
3. Copy your **API Token**
4. Add to `backend/.env`:
   ```
   KOBO_API_TOKEN=your_token_here
   ```

### Getting Your Form Asset UID

1. Open your survey form in KoBoToolbox
2. Copy the UID from the URL: `https://kf.kobotoolbox.org/#/forms/YOUR_ASSET_UID`
3. Create a campaign with this UID:
   ```bash
   curl -X POST http://localhost:5000/api/campaigns \
     -H "Content-Type: application/json" \
     -d '{
       "name": "GBV ICT Readiness Assessment 2024",
       "start_date": "2024-01-01",
       "end_date": "2024-12-31",
       "kobo_asset_uid": "YOUR_ASSET_UID",
       "target_institutions": 500
     }'
   ```

### Syncing Data

Trigger a sync via API:
```bash
curl -X POST http://localhost:5000/api/campaigns/1/sync-kobo
```

Or use the dashboard's "Sync Now" button.

---

## GBV ICT Readiness Indicators

The system assesses institutions across **10 domains** with **50+ indicators**:

| Domain | Key Indicators |
|--------|---------------|
| Policy & Governance | GBV policy, action plan, budget allocation |
| Human Resources | Trained staff, dedicated GBV unit |
| ICT Infrastructure | Computers, internet connectivity |
| Case Management | Electronic CMS, data backup |
| Data Protection | Privacy policy, access controls |
| Service Delivery | Referral pathways, helplines |
| Survivor Support | Counseling, legal, medical services |
| Monitoring | M&E system, performance indicators |
| Partnerships | Inter-agency coordination |
| Community Engagement | Outreach, awareness programs |

See [GBV_ICT_READINESS_INDICATORS.md](./GBV_ICT_READINESS_INDICATORS.md) for the complete indicator framework.

---

## API Endpoints

### Campaigns
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/campaigns` | List all campaigns |
| POST | `/api/campaigns` | Create campaign |
| GET | `/api/campaigns/{id}` | Get campaign details |
| GET | `/api/campaigns/{id}/national-summary` | National statistics |
| GET | `/api/campaigns/{id}/regional-summary` | Regional breakdown |
| GET | `/api/campaigns/{id}/daily-progress` | Daily completion trend |
| GET | `/api/campaigns/{id}/progress-report` | Comprehensive report |
| GET | `/api/campaigns/{id}/readiness-summary` | GBV readiness statistics |
| GET | `/api/campaigns/{id}/regional-readiness` | Readiness by region |
| POST | `/api/campaigns/{id}/sync-kobo` | Sync from KoBoToolbox |

### Surveys
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/surveys` | List surveys (filterable) |
| POST | `/api/surveys` | Create survey |
| GET | `/api/surveys/{id}` | Survey with readiness data |
| PUT | `/api/surveys/{id}` | Update survey status |

### Reference Data
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/regions` | List 14 Namibian regions |
| GET | `/api/institutions` | List institutions |
| POST | `/api/institutions` | Add institution |

---

## Namibia's 14 Regions

| Code | Region | Code | Region |
|------|--------|------|--------|
| CA | Zambezi | OW | Ohangwena |
| ER | Erongo | OH | Omaheke |
| HA | Hardap | OS | Omusati |
| KA | //Karas | ON | Oshana |
| KE | Kavango East | OT | Oshikoto |
| KW | Kavango West | OD | Otjozondjupa |
| KH | Khomas | | |
| KU | Kunene | | |

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `KOBO_API_URL` | KoBoToolbox server URL | `https://kf.kobotoolbox.org` |
| `KOBO_API_TOKEN` | KoBoToolbox API token | Required for sync |
| `CORS_ORIGINS` | Allowed CORS origins | `*` |
| `PORT` | Backend server port | `5000` |
| `FLASK_ENV` | Environment mode | `development` |

---

## Development

### Running Tests

```bash
cd tests
pytest test_api.py test_database.py -v
```

### Database Migrations

Place migration scripts in `database/migration_scripts/` with naming convention:
```
001_initial_schema.sql
002_add_readiness_fields.sql
...
```

---

## License

This project is developed for the Government of Namibia's GBV response initiatives.

---

## Support

For technical support or questions about the GBV ICT Readiness Assessment, contact the system administrator.
