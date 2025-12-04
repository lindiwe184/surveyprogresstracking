# GBV Readiness Survey Dashboard

A comprehensive survey tracking system for the Namibian Statistics Agency (NSA) Gender-Based Violence (GBV) readiness assessment program. This system provides real-time monitoring and analysis of survey submissions across multiple regions.

## Features

- **Real-time Data Tracking**: Live monitoring of survey submissions via KoboToolbox API
- **Regional Analysis**: Performance tracking across 5 active survey regions (Hardap, Erongo, Kavango, Ohangwena, Omaheke)
- **Professional NSA Branding**: Custom styling with official NSA colors and logo
- **Interactive Visualizations**: Vibrant charts and graphs using Plotly with colorful gradients
- **Progress Monitoring**: Daily submission tracking with target vs actual progress
- **Champion Recognition**: Regional top performer showcase system

## System Architecture

### Backend (`backend/`)
- **kobo_app.py**: Main Flask API server providing KoboToolbox integration
- **requirements.txt**: Backend Python dependencies

### Frontend (`frontend/`)
- **kobo_dashboard.py**: Main Streamlit dashboard application
- **config.py**: Configuration settings for API connectivity
- **nsa-logo.png**: Official NSA logo for branding
- **requirements.txt**: Frontend Python dependencies

## Installation & Setup

### Prerequisites
- Python 3.8+
- Virtual environment (recommended)
- KoboToolbox account with API access

### 1. Clone Repository
```bash
git clone <repository-url>
cd survey_tracking_system
```

### 2. Backend Setup
```bash
cd backend
pip install -r requirements.txt

# Copy environment template
cp env.template .env

# Edit .env with your KoboToolbox credentials
# KOBO_TOKEN=your_kobo_api_token
# KOBO_ASSET_ID=your_survey_asset_id
# KOBO_BASE_URL=https://kf.kobotoolbox.org
```

### 3. Frontend Setup
```bash
cd ../frontend
pip install -r requirements.txt
```

## Running the Application

### Start Backend API
```bash
cd backend
python kobo_app.py
```
*Backend will run on http://localhost:5002*

### Start Frontend Dashboard
```bash
cd frontend
streamlit run kobo_dashboard.py
```
*Dashboard will open in your browser at http://localhost:8501*

## Dashboard Features

### National Overview Tab
- **Total Surveys**: Real-time submission count with progress gauge
- **Performance Metrics**: Daily averages and completion rates
- **Survey Progress**: Multi-color progress indicator
- **Completion Rate**: Target achievement tracking

### Regional Analysis Tab
- **Regional Breakdown**: Completion rates by region with color-coded table
- **Champion Showcase**: Top performing region with animated crown icon
- **Regional Targets**: Individual targets for each active region
- **Progress Visualization**: Interactive bar charts with vibrant colors

### Progress Tracking Tab
- **Metric Cards**: Compact cards showing key daily statistics
- **Actual vs Target**: Progress comparison with target trajectory
- **Daily Submissions**: Bar chart with 5-day moving average
- **Cumulative Progress**: Line chart showing total progress over time

## Regional Targets

Active survey regions and their targets:
- **Hardap**: 21 surveys
- **Erongo**: 16 surveys  
- **Kavango**: 18 surveys
- **Ohangwena**: 20 surveys
- **Omaheke**: 15 surveys

**Total Target**: 90 surveys across all regions

## Technical Details

### API Endpoints
- `GET /api/health` - System health check
- `GET /api/kobo/summary` - Survey summary statistics
- `GET /api/kobo/submissions` - Recent submissions data

### Color Schemes
- **NSA Blue**: #1e4a8a, #2563eb
- **NSA Gold**: #c9a961, #d4af37
- **Chart Colors**: Viridis and Plasma colorscales for vibrant visualizations
- **Regional Champion**: Purple gradient (#8b5cf6 to #a78bfa)

### CSS Components
The dashboard includes comprehensive CSS styling with documented components:
- Tab navigation with NSA branding
- Metric cards (both regular and compact sizes)
- Regional champion showcase
- Section dividers and containers
- Responsive layout design

## Environment Configuration

### Backend (.env)
```
KOBO_TOKEN=your_kobo_api_token
KOBO_ASSET_ID=your_survey_asset_id  
KOBO_BASE_URL=https://kf.kobotoolbox.org
FLASK_PORT=5002
```

### Frontend
The frontend automatically connects to the backend API at `http://localhost:5002` (configurable via environment variable).

## Troubleshooting

### Common Issues
1. **Backend Connection Failed**: Ensure backend is running on port 5002
2. **KoboToolbox API Errors**: Verify API token and asset ID in .env file
3. **Missing Data**: Check KoboToolbox survey has submissions
4. **Logo Not Displaying**: Ensure nsa-logo.png is in frontend directory

### Development Notes
- The system uses Africa/Windhoek timezone for proper time handling
- All charts use `use_container_width=True` for responsive design
- Regional mapping handles various institution name formats
- Comprehensive error handling for API connectivity issues

## Deployment

For production deployment:
1. Use a production WSGI server for the backend (e.g., Gunicorn)
2. Configure environment variables for production KoboToolbox instance
3. Set up proper logging and monitoring
4. Use a reverse proxy (nginx) for the Streamlit frontend

## Support

For technical support or feature requests, contact the NSA IT department or the development team.

---

*Built for the Namibian Statistics Agency | GBV Readiness Assessment Program 2025*