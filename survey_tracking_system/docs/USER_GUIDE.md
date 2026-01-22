## User Guide

### Overview

The Namibia Survey Tracking Dashboard allows you to track survey completion:

- **Nationally** across all regions.
- **By region** to see disparities.
- **Over time** using daily completion trends.

### Accessing the Dashboard

1. Start the **backend API** (`python app.py` in the `backend` folder).
2. Start the **frontend dashboard** (`streamlit run dashboard.py` in the `frontend` folder).
3. Open the Streamlit URL in your browser (usually `http://localhost:8501`).

### Using the Dashboard

- **Campaign selector**: Choose an active campaign at the top of the page.
- **National Summary tab**: View country-level totals and completion percentage.
- **Regional Breakdown tab**: See totals and completion rates by region, with a bar chart.
- **Daily Trend tab**: View line chart of completed surveys over recent days.
- **Report tab**: See a compact summary of total, completed, in-progress, and pending surveys.

### Data Refresh

- The dashboard fetches live data from the backend API.
- Refresh the page or use Streamlit’s “Rerun” to see updated progress.


