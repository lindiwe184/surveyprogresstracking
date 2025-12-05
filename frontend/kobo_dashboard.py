import os
from datetime import datetime, timedelta
from typing import Dict, List, Any

import pandas as pd
import requests
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pytz

from config import get_api_base_url


API_BASE_URL = get_api_base_url().rstrip("/")

# Namibia timezone for real-time updates
TZ = pytz.timezone("Africa/Windhoek")

def now_cat():
    """Return real-time Namibia local time"""
    return datetime.now(TZ)

def clean_timestamp(ts):
    """Safely parse and convert timestamp to Namibia timezone"""
    try:
        dt = pd.to_datetime(ts, utc=True, errors="coerce")
        if pd.isna(dt): 
            return None
        return dt.tz_convert(TZ)
    except:
        return None


def fetch_json(path: str, params=None) -> Dict[str, Any]:
    """Fetch JSON data from the API."""
    url = f"{API_BASE_URL}{path}"
    try:
        resp = requests.get(url, params=params or {}, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        st.error(f"Failed to fetch {path}: {exc}")
        return {}


def show_national_overview():
    """Display national overview with targets and progress."""
    st.markdown('<h2 class="section-header">National Overview</h2>', unsafe_allow_html=True)
    
    # Fetch summary data
    summary_data = fetch_json("/api/kobo/summary")
    if not summary_data:
        st.error("Unable to fetch survey data")
        return
    
    total_submissions = summary_data.get("total_submissions", 0)
    by_date = summary_data.get("by_date", {})
    
    # Survey targets - 5-day survey period (Monday to Friday)
    TARGET_SURVEYS = 90  # Total target for active survey regions (21+16+18+20+15)
    
    # Dynamic survey window (Monday–Friday of the current week)
    current_datetime = now_cat()
    current_date = current_datetime.date()
    
    # Calculate this week's Monday and Friday
    SURVEY_START_DATE = current_date - timedelta(days=current_date.weekday())  # Monday this week
    SURVEY_END_DATE = SURVEY_START_DATE + timedelta(days=4)  # Friday this week
    
    # Calculate real-time progress metrics
    days_elapsed = min(5, max(1, (current_date - SURVEY_START_DATE).days + 1))  # 1-5 days
    total_days = 5  # Monday through Friday
    days_remaining = max(0, (SURVEY_END_DATE - current_date).days)
    
    # Calculate daily progress for performance tracking
    if by_date:
        daily_df = pd.DataFrame([
            {"Date": date, "Daily_Count": count}
            for date, count in by_date.items()
        ])
        daily_df["Date"] = pd.to_datetime(daily_df["Date"])
        daily_df = daily_df.sort_values("Date")
        
        # Get recent performance metrics (dynamic average)
        survey_avg = daily_df["Daily_Count"].mean() if len(daily_df) > 0 else 0
    else:
        survey_avg = total_submissions / max(1, days_elapsed)
    
    # Real-time progress calculations
    completion_percentage = (total_submissions / TARGET_SURVEYS * 100) if TARGET_SURVEYS > 0 else 0
    time_percentage = (days_elapsed / total_days * 100) if total_days > 0 else 0
    
    # Calculate expected submissions based on daily target
    daily_target = TARGET_SURVEYS / total_days  # 18 surveys per day
    expected_submissions = daily_target * days_elapsed
    
    # Display key metrics with modern cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(
            f'<div class="metric-card blue">'
            f'<h3>Total Surveys</h3>'
            f'<h2>{total_submissions:,}</h2>'
            f'<p>of {TARGET_SURVEYS:,} target</p>'
            f'</div>', 
            unsafe_allow_html=True
        )
    
    with col2:
        st.markdown(
            f'<div class="metric-card green">'
            f'<h3>Performance</h3>'
            f'<h2>{completion_percentage - time_percentage:+.1f}%</h2>'
            f'<p>{"Ahead of schedule" if completion_percentage >= time_percentage else "Behind schedule"}</p>'
            f'</div>', 
            unsafe_allow_html=True
        )
    
    with col3:
        # Day name display without time
        current_day_name = current_datetime.strftime("%A")
        
        if days_elapsed <= 0:
            status_text = "Survey Not Started"
        elif days_elapsed > 5:
            status_text = "Survey Complete"
        else:
            status_text = f"{current_day_name}, {current_datetime.strftime('%B %d')}"
        
        st.markdown(
            f'<div class="metric-card purple">'
            f'<h3>Survey Progress</h3>'
            f'<h2>Day {max(1, min(days_elapsed, 5))}/5</h2>'
            f'<p>{status_text}</p>'
            f'</div>', 
            unsafe_allow_html=True
        )
    
    with col4:
        st.markdown(
            f'<div class="metric-card orange">'
            f'<h3>Completion Rate</h3>'
            f'<h2>{completion_percentage:.1f}%</h2>'
            f'<p>vs {time_percentage:.0f}% timeline</p>'
            f'</div>', 
            unsafe_allow_html=True
        )
    
    # Professional progress gauge section
    st.markdown("""
    <div class="section-divider" style="background: linear-gradient(135deg, #8b5cf6 0%, #a78bfa 100%); border-left: 4px solid #7c3aed;">
        <h3 style="color: white;">Overall Progress Gauge</h3>
    </div>
    """, unsafe_allow_html=True)
    
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = completion_percentage,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Survey Completion %"},
        delta = {'reference': time_percentage, 'suffix': "% (vs timeline)"},
        gauge = {
            'axis': {'range': [None, 100]},
            'bar': {'color': "darkgreen" if completion_percentage >= time_percentage else "orange"},
            'steps': [
                {'range': [0, 50], 'color': "lightgray"},
                {'range': [50, 80], 'color': "yellow"},
                {'range': [80, 100], 'color': "lightgreen"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': time_percentage
            }
        }
    ))
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    # Professional refresh section
    st.markdown("""
    <div class="chart-container" style="text-align: center; margin-top: 2rem;">
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🔄 Refresh Data", type="primary", use_container_width=True):
            st.success("Data refreshed successfully!")
            st.rerun()


def show_regional_breakdown():
    """Display regional breakdown of survey progress."""
    st.markdown('<h2 class="section-header">Regional Analysis</h2>', unsafe_allow_html=True)
    
    # Fetch summary data
    summary_data = fetch_json("/api/kobo/summary")
    if not summary_data:
        st.error("Unable to fetch survey data")
        return
    
    by_region = summary_data.get("by_region", {})
    
    if not by_region:
        st.warning("No regional data available")
        return
    
    # Active survey regions only (where surveys are taking place)
    all_regions = ["hardap", "erongo", "kavango", "ohangwena", "omaheke"]
    
    # Get raw submissions for accurate region mapping
    submissions_data = fetch_json("/api/kobo/submissions")
    if submissions_data and isinstance(submissions_data, dict):
        raw_submissions = submissions_data.get("submissions", [])
    elif submissions_data and isinstance(submissions_data, list):
        raw_submissions = submissions_data
    else:
        raw_submissions = []
    
    def map_region_to_code(reported_region):
        """Map reported region to standardized region code."""
        if not reported_region or reported_region == "Unknown":
            return None
            
        region_lower = reported_region.lower().strip()
        
        # Handle Kavango variations (East, West, or just Kavango)
        if "kavango" in region_lower:
            return "kavango"
        # Handle Hardap variations (including "hardap" and "!hardap")
        elif "hardap" in region_lower:
            return "hardap"
        # Handle other active survey regions
        elif region_lower in ["erongo", "ohangwena", "omaheke"]:
            return region_lower
        else:
            return region_lower
    
    # Recalculate region counts using institution mapping
    region_counts = {region: 0 for region in all_regions}
    
    if raw_submissions:
        for submission in raw_submissions:
            region = submission.get("grp_login/resp_region_display", "Unknown")
            
            if region and region != "Unknown":
                correct_region = map_region_to_code(region)
                
                if correct_region and correct_region in region_counts:
                    region_counts[correct_region] += 1
    
    # Create DataFrame for regional analysis with corrected counts
    region_data = []
    for region in all_regions:
        completed = region_counts.get(region, 0)
        region_data.append({"Region": region, "Completed": completed, "Status": "Completed"})
    
    region_df = pd.DataFrame(region_data)
    
    # Real regional targets from NSA planning documents (active survey regions only)
    # These must sum to TARGET_SURVEYS = 90 total
    regional_targets = {
        "hardap": 21, "erongo": 16, "kavango": 18, 
        "ohangwena": 20, "omaheke": 15
    }
    
    # Verify targets sum to 90 (21+16+18+20+15 = 90)
    total_regional_targets = sum(regional_targets.values())
    if total_regional_targets != 90:
        st.warning(f"Regional targets sum to {total_regional_targets}, expected 90. Check configuration.")
    
    # Calculate completion rates
    region_df = region_df.copy()  # Ensure we have a proper copy
    region_df["Target"] = region_df["Region"].map(regional_targets).fillna(20)  # Default target
    region_df["Completion_Rate"] = (region_df["Completed"] / region_df["Target"] * 100).round(1)
    region_df["Remaining"] = region_df["Target"] - region_df["Completed"]
    region_df["Remaining"] = region_df["Remaining"].clip(lower=0)
    
    # Display regional summary with modern layout
    col1, col2 = st.columns([1.2, 0.8])
    
    with col1:
        st.markdown("""
        <div class="section-divider regional-overview" style="text-align: left; background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); border-left: 4px solid #2563eb;">
            <h4>📋 Regional Progress Overview</h4>
        """, unsafe_allow_html=True)
        display_df = region_df[["Region", "Completed", "Target", "Completion_Rate", "Remaining"]].copy()
        # Map region codes to full names
        region_mapping = {
            "erongo": "Erongo", "hardap": "Hardap", "karas": "Karas", "kavango": "Kavango",
            "khomas": "Khomas", "kunene": "Kunene", "ohangwena": "Ohangwena",
            "omaheke": "Omaheke", "omusati": "Omusati", "oshana": "Oshana", "oshikoto": "Oshikoto",
            "otjozondjupa": "Otjozondjupa", "zambezi": "Zambezi"
        }
        display_df = display_df.copy()
        display_df["Region"] = display_df["Region"].str.lower().map(region_mapping).fillna(display_df["Region"].str.title())
        display_df["Completion_Rate"] = display_df["Completion_Rate"].astype(str) + "%"
        st.dataframe(display_df, use_container_width=True)
        
        # Regional champion showcase - positioned below the table in the left column
        if not region_df.empty:
            top_region_idx = region_df["Completion_Rate"].idxmax()
            top_region = region_df.loc[top_region_idx]
            
            st.markdown(f"""
            <div class="regional-champion">
                <div class="champion-header">
                    <span class="crown-icon">👑</span>
                    <h3>Top Performing Team</h3>
                </div>
                <div class="champion-details">
                    <h2>{region_mapping.get(top_region['Region'], top_region['Region'].title())}</h2>
                    <div class="champion-stats">
                        <div class="stat-item">
                            <span class="stat-value">{top_region['Completed']}</span>
                            <span class="stat-label">Completed</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value">{top_region['Completion_Rate']:.1f}%</span>
                            <span class="stat-label">Rate</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value">{int(top_region['Target'])}</span>
                            <span class="stat-label">Target</span>
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="section-divider" style="background: linear-gradient(135deg, #f1f8e9 0%, #dcedc8 100%); border-left: 4px solid #4caf50;">
            <h4>📊 Completion Rate by Region</h4>
        </div>
        """, unsafe_allow_html=True)
        fig = px.bar(
            region_df, 
            x="Region", 
            y="Completion_Rate",
            color="Completion_Rate",
            color_continuous_scale="RdYlGn",
            title="Completion Rate (%)"
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)


def show_daily_progress():
    """Display daily progress tracking and trends."""
    st.markdown('<h2 class="section-header">Progress Tracking</h2>', unsafe_allow_html=True)
    
    # Fetch summary data
    summary_data = fetch_json("/api/kobo/summary")
    if not summary_data:
        st.error("Unable to fetch survey data")
        return
    
    by_date = summary_data.get("by_date", {})
    
    if not by_date:
        st.warning("No daily progress data available")
        return
    
    # Create daily progress DataFrame
    daily_df = pd.DataFrame([
        {"Date": date, "Daily_Count": count}
        for date, count in by_date.items()
    ])
    daily_df["Date"] = pd.to_datetime(daily_df["Date"])
    daily_df = daily_df.sort_values("Date")
    
    # Calculate cumulative progress
    daily_df = daily_df.copy()  # Ensure we have a proper copy
    daily_df["Cumulative"] = daily_df["Daily_Count"].cumsum()
    
    # Calculate moving average for 5-day survey period
    daily_df["5_Day_Avg"] = daily_df["Daily_Count"].rolling(window=5, min_periods=1).mean()
    
    TARGET_SURVEYS = 90  # Real NSA target for active survey regions (21+16+18+20+15)
    
    # Dynamic survey window (Monday–Friday of the current week)
    current_datetime = now_cat()
    current_date = current_datetime.date()
    SURVEY_START_DATE = current_date - timedelta(days=current_date.weekday())  # Monday this week
    SURVEY_END_DATE = SURVEY_START_DATE + timedelta(days=4)  # Friday this week
    
    # Calculate expected daily target for 5-day survey period
    total_days = 5  # 5 working days (Monday to Friday)
    daily_target = TARGET_SURVEYS / total_days
    
    # Create target trajectory for 5-day period
    target_dates = pd.date_range(start=SURVEY_START_DATE, end=SURVEY_END_DATE, freq='D')
    target_cumulative = [daily_target * (i + 1) for i in range(len(target_dates))]
    
    # Display metrics and actual vs target progress side by side
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Metric cards stacked vertically with green on top
        survey_days = min(len(daily_df), 5)  # Max 5 days for survey period
        st.markdown(
            f'<div class="metric-card-small green">'
            f'<h3>🗓️ Survey Days</h3>'
            f'<h2>{survey_days}/5</h2>'
            f'<p>days completed</p>'
            f'</div>', 
            unsafe_allow_html=True
        )
        
        survey_avg = daily_df["Daily_Count"].tail(5).mean() if len(daily_df) >= 5 else daily_df["Daily_Count"].mean()
        st.markdown(
            f'<div class="metric-card-small blue">'
            f'<h3>📊 Day Average</h3>'
            f'<h2>{survey_avg:.1f}</h2>'
            f'<p>submissions per day</p>'
            f'</div>', 
            unsafe_allow_html=True
        )
    
    with col2:
        st.subheader("Actual vs Target Progress")
        fig = go.Figure()
        
        # Add actual progress
        fig.add_trace(go.Scatter(
            x=daily_df["Date"],
            y=daily_df["Cumulative"],
            mode="lines+markers",
            name="Actual Progress",
            line=dict(color="blue", width=3)
        ))
        
        # Add target trajectory
        fig.add_trace(go.Scatter(
            x=target_dates,
            y=target_cumulative,
            mode="lines",
            name="Target Trajectory",
            line=dict(color="red", dash="dash", width=2)
        ))
        
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Cumulative Submissions",
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Daily submissions and cumulative progress charts side by side
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Daily Submissions Over Time")
        fig = go.Figure()
        
        # Add daily counts as bars
        fig.add_trace(go.Bar(
            x=daily_df["Date"],
            y=daily_df["Daily_Count"],
            name="Daily Submissions",
            marker_color="lightblue"
        ))
        
        # Add 5-day moving average as line
        fig.add_trace(go.Scatter(
            x=daily_df["Date"],
            y=daily_df["5_Day_Avg"],
            mode="lines",
            name="5-Day Average",
            line=dict(color="red", width=2)
        ))
        
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Number of Submissions",
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Cumulative Progress")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=daily_df["Date"],
            y=daily_df["Cumulative"],
            mode="lines+markers",
            fill="tonexty",
            name="Cumulative Submissions"
        ))
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)


def show_submissions_summary():
    """Display submissions summary and statistics."""
    st.subheader("📈 Submissions Summary")
    
    summary_data = fetch_json("/api/kobo/summary")
    
    if not summary_data:
        st.warning("No data available from KoboToolbox")
        return
    
    # Main metrics
    col1, col2, col3, col4 = st.columns(4)
    
    total = summary_data.get("total_submissions", 0)
    by_region = summary_data.get("by_region", {})
    by_date = summary_data.get("by_date", {})
    
    col1.metric("Total Submissions", total)
    col2.metric("Regions Covered", len(by_region))
    col3.metric("Days with Data", len(by_date))
    
    if by_date:
        latest_date = max(by_date.keys())
        col4.metric("Latest Submission", latest_date)
    
    # Regional breakdown
    if by_region:
        st.subheader("🗺️ Submissions by Region")
        
        region_df = pd.DataFrame([
            {"Region": region, "Submissions": count}
            for region, count in by_region.items()
        ])
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.dataframe(region_df, use_container_width=True)
        
        with col2:
            # Display as metrics instead of chart to avoid compatibility issues
            st.write("**Regional Distribution:**")
            for _, row in region_df.iterrows():
                st.metric(row["Region"], row["Submissions"])
    
    # Daily submissions trend
    if by_date:
        st.subheader("📅 Daily Submissions")
        
        # Convert to DataFrame and sort by date with timezone awareness
        date_df = pd.DataFrame([
            {"Date": date, "Submissions": count}
            for date, count in by_date.items()
        ])
        date_df = date_df.copy()  # Ensure we have a proper copy
        date_df.loc[:, "Date"] = pd.to_datetime(date_df["Date"], errors='coerce')
        date_df = date_df.sort_values("Date")
        # Format dates for display
        date_df.loc[:, "Date"] = date_df["Date"].dt.strftime('%Y-%m-%d')
        
        # Display as table instead of chart to avoid compatibility issues
        st.dataframe(date_df, use_container_width=True)


def show_raw_submissions():
    """Display raw submissions data."""
    st.subheader(" Recent Submissions")
    
    summary_data = fetch_json("/api/kobo/summary")
    
    if not summary_data:
        st.warning("No submission data available")
        return
    
    recent_submissions = summary_data.get("recent_submissions", [])
    
    if not recent_submissions:
        st.info("No submissions found")
        return
    
    # Show submission count
    st.write(f"**Showing {len(recent_submissions)} most recent submissions**")
    
    # Convert to DataFrame for better display
    df = pd.DataFrame(recent_submissions)
    
    # Select relevant columns for display (exclude system fields)
    display_cols = []
    for col in df.columns:
        if not col.startswith('_') or col in ['_submission_time']:
            display_cols.append(col)
    
    if display_cols:
        display_df = df[display_cols]
        
        # Format submission time with proper timezone conversion
        if '_submission_time' in display_df.columns:
            display_df = display_df.copy()  # Ensure we have a proper copy
            # Apply safe timestamp conversion to all submission times
            display_df.loc[:, '_submission_time'] = display_df['_submission_time'].apply(
                lambda x: clean_timestamp(x).strftime('%Y-%m-%d %H:%M CAT') if clean_timestamp(x) else str(x)
            )
            display_df = display_df.rename(columns={'_submission_time': 'Submission Time (CAT)'})
        
        st.dataframe(display_df, use_container_width=True)
    else:
        st.json(recent_submissions[0])  # Show first submission as JSON if no good columns





def main():
    st.set_page_config(
        page_title="GBV Readiness Survey Progress Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Modern NSA design system
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* GLOBAL FONT SETTING - All text uses Inter font */
    * {
        font-family: 'Inter', sans-serif;
    }
    
    /* MAIN BACKGROUND - Blue gradient background behind entire app */
    .main {
        padding-top: 0.5rem;
        background: linear-gradient(135deg, #1e4a8a 0%, #2563eb 100%);
    }
    
    /* MAIN CONTAINER - Light grey content area with rounded corners */
    .main > div {
        background: #f8fafc;
        border-radius: 16px 16px 0 0;
        padding: 1rem;
        min-height: calc(100vh - 1rem);
    }
    
    /* HEADER CONTAINER - White box containing logo and main title */
    .main-header {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        display: flex;
        align-items: center;
        gap: 2rem;
    }
    
    /* HEADER TEXT WRAPPER - Container for title text next to logo */
    .header-text-content {
        padding: 1rem 0;
    }
    
    .header-text {
        flex: 1;
    }
    
    /* MAIN TITLE - "GBV Assessment Progress" with blue-to-gold gradient text */
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #1e4a8a 0%, #c9a961 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem;
    }
    
    .main-subtitle {
        font-size: 1.1rem;
        color: #6b7280;
        margin-bottom: 1rem;
    }
    
    .live-indicator {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        color: #059669;
        font-weight: 600;
        font-size: 1rem;
        margin-top: 0.5rem;
    }
    
    .status-dot {
        width: 10px;
        height: 10px;
        background: #22c55e;
        border-radius: 50%;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { 
            opacity: 1; 
            transform: scale(1);
        }
        50% { 
            opacity: 0.7;
            transform: scale(1.1);
        }
    }
    
    /* TAB CONTAINER - White rounded container holding all three navigation tabs */
    .stTabs [data-baseweb="tab-list"] {
        display: flex;
        gap: 12px;
        background: #d4af37;
        border-radius: 16px;
        padding: 8px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    /* INDIVIDUAL TABS - Default state (National Overview, Regional Analysis, Track Progress) */
    .stTabs [data-baseweb="tab"] {
        height: 56px;
        padding: 0 2rem;
        background: transparent;
        border: none;
        border-radius: 12px;
        color: #000000;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
    }
    
    /* ACTIVE TAB - Currently selected tab with blue background */
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #1e4a8a 0%, #2563eb 100%);
        color: white;
        box-shadow: 0 4px 12px rgba(30, 74, 138, 0.4);
    }
    
    /* METRIC CARDS - Large cards in National Overview (Total Surveys, Performance, Survey Progress, Completion Rate) */
    .metric-card {
        background: white;
        padding: 1.5rem 1rem;
        border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
        text-align: center;
        margin-bottom: 1rem;
        min-height: 150px;
        max-width: 275px;
        margin-left: auto;
        margin-right: auto;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, var(--gradient-start, #1e4a8a), var(--gradient-end, #2563eb));
    }
    
    .metric-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 24px -4px rgba(0, 0, 0, 0.15);
    }
    
    /* BLUE METRIC CARD - Total Surveys card with light blue background */
    .metric-card.blue {
        --gradient-start: #1e4a8a;
        --gradient-end: #2563eb;
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        border-left: 4px solid #2563eb;
    }
    
    /* GREEN METRIC CARD - Performance card with light green background */
    .metric-card.green {
        --gradient-start: #c9a961;
        --gradient-end: #d4af37;
        background: linear-gradient(135deg, #f1f8e9 0%, #dcedc8 100%);
        border-left: 4px solid #4caf50;
    }
    
    /* PURPLE METRIC CARD - Survey Progress card with light purple background */
    .metric-card.purple {
        --gradient-start: #1e4a8a;
        --gradient-end: #3b82f6;
        background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%);
        border-left: 4px solid #9c27b0;
    }
    
    /* ORANGE METRIC CARD - Completion Rate card with light orange background */
    .metric-card.orange {
        --gradient-start: #c9a961;
        --gradient-end: #b8860b;
        background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
        border-left: 4px solid #ff9800;
    }
    
    .metric-card .stat-icon {
        font-size: 2.5rem;
        margin-bottom: 1rem;
    }
    
    /* SMALL METRIC CARDS - Compact cards in Progress Tracking (Day Average, Survey Days) */
    .metric-card-small {
        background: white;
        padding: 1rem 0.75rem;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
        text-align: center;
        margin-bottom: 0.75rem;
        min-height: 100px;
        max-width: 200px;
        margin-left: auto;
        margin-right: auto;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    
    .metric-card-small::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, var(--gradient-start, #1e4a8a), var(--gradient-end, #2563eb));
    }
    
    .metric-card-small:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
    }
    
    .metric-card-small.blue {
        --gradient-start: #1e4a8a;
        --gradient-end: #2563eb;
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        border-left: 3px solid #2563eb;
    }
    
    .metric-card-small.green {
        --gradient-start: #c9a961;
        --gradient-end: #d4af37;
        background: linear-gradient(135deg, #f1f8e9 0%, #dcedc8 100%);
        border-left: 3px solid #4caf50;
    }
    
    .metric-card-small h3 {
        font-size: 0.75rem;
        color: #6b7280;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.25rem;
        text-align: center;
    }
    
    .metric-card-small h2 {
        font-size: 2rem;
        font-weight: 700;
        color: #1f2937;
        line-height: 1;
        margin: 0.25rem 0;
        text-align: center;
    }
    
    .metric-card-small p {
        font-size: 0.8rem;
        color: #6b7280;
        margin: 0.25rem 0;
        text-align: center;
    }
    
    .metric-card h3 {
        font-size: 0.875rem;
        color: #6b7280;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    
    .metric-card h2 {
        font-size: 3rem;
        font-weight: 700;
        color: #1f2937;
        line-height: 1;
        margin: 0.5rem 0;
        text-align: center;
    }
    
    .metric-card p {
        font-size: 0.95rem;
        color: #6b7280;
        margin: 0.5rem 0;
        text-align: center;
    }
    
    /* PAGE HEADERS - "National Overview", "Regional Analysis", "Progress Tracking" */
    .section-header {
        color: #1f2937;
        font-size: 1.8rem;
        font-weight: 700;
        margin-bottom: 1.5rem;
        text-align: left;
    }
    
    /* DATA TABLES - Styling for pandas dataframes (Regional Progress table, etc.) */
    .stDataFrame {
        background: white;
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border: 1px solid #e5e7eb;
    }
    
    /* CHART CONTAINERS - White boxes around plotly charts */
    .chart-container {
        background: white;
        padding: 1rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    
    /* SECTION DIVIDERS - White boxes with titles like "Overall Progress Gauge" */
    .section-divider {
        background: white;
        padding: 1rem;
        border-radius: 12px;
        margin: 1rem 0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    .section-divider h3 {
        color: #1f2937;
        font-weight: 700;
        margin: 0;
    }
    
    .section-divider p {
        color: #6b7280;
        margin: 0.5rem 0 0 0;
        font-size: 0.9rem;
    }
    
    .top-performer-banner {
        background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%);
        border: 2px solid #f59e0b;
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1.5rem 0;
        display: flex;
        align-items: center;
        gap: 1rem;
        box-shadow: 0 8px 25px rgba(245, 158, 11, 0.3);
        animation: glow 2s infinite alternate;
    }
    
    @keyframes glow {
        from { box-shadow: 0 8px 25px rgba(245, 158, 11, 0.3); }
        to { box-shadow: 0 8px 35px rgba(245, 158, 11, 0.5); }
    }
    
    .trophy-icon {
        font-size: 3rem;
        animation: bounce 2s infinite;
    }
    
    @keyframes bounce {
        0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
        40% { transform: translateY(-10px); }
        60% { transform: translateY(-5px); }
    }
    
    .performer-text h3 {
        color: #92400e;
        font-weight: 700;
        margin: 0;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .performer-text h2 {
        color: #78350f;
        font-weight: 800;
        margin: 0.25rem 0;
        font-size: 1.8rem;
    }
    
    .performer-text p {
        color: #92400e;
        margin: 0;
        font-weight: 600;
    }
    
    /* REGIONAL CHAMPION SHOWCASE - Purple gradient box showing top performing region */
    .regional-champion {
        background: linear-gradient(135deg, #8b5cf6 0%, #a78bfa 100%);
        border-radius: 20px;
        padding: 2rem;
        margin: 1.5rem 0;
        text-align: center;
        box-shadow: 0 10px 30px rgba(139, 92, 246, 0.3);
        border: 3px solid #7c3aed;
    }
    
    /* CHAMPION HEADER - Crown icon and "Top Performing Team" text */
    .champion-header {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        margin-bottom: 1rem;
    }
    
    /* ROTATING CROWN ICON - Animated crown emoji in champion header */
    .crown-icon {
        font-size: 2rem;
        animation: rotate 3s infinite linear;
    }
    
    @keyframes rotate {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    
    .champion-header h3 {
        color: white;
        font-weight: 700;
        margin: 0;
        font-size: 1.1rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }
    
    .champion-details h2 {
        color: white;
        font-weight: 800;
        margin: 0.5rem 0 1.5rem 0;
        font-size: 2.2rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    /* CHAMPION STATISTICS ROW - Three stat boxes showing Completed/Rate/Target */
    .champion-stats {
        display: flex;
        justify-content: space-around;
        gap: 1rem;
    }
    
    /* INDIVIDUAL STAT BOXES - Semi-transparent white boxes within champion showcase */
    .stat-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        background: rgba(255, 255, 255, 0.2);
        border-radius: 12px;
        padding: 0.75rem;
        min-width: 80px;
    }
    
    /* STAT VALUES - Large white numbers in stat boxes */
    .stat-value {
        color: white;
        font-weight: 700;
        font-size: 1.4rem;
        margin-bottom: 0.25rem;
    }
    
    /* STAT LABELS - Small text below values ("Completed", "Rate", "Target") */
    .stat-label {
        color: rgba(255, 255, 255, 0.8);
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Modern NSA header with official logo
    col_logo, col_text = st.columns([1, 4])
    
    with col_logo:
        st.image("nsa-logo.png", width=90)
    
    with col_text:
        st.markdown(
            '''
            <div class="header-text-content">
                <h1 class="main-title">GBV Assessment Progress</h1>
            </div>
            ''', 
            unsafe_allow_html=True
        )
    
    # Test connection
    health_data = fetch_json("/api/health")
    if not health_data:
        st.error("❌ Cannot connect to backend API. Make sure backend is running on http://localhost:5000")
        return
    
    # Professional tab layout
    tab1, tab2, tab3 = st.tabs([
        "National Overview", 
        "Regional Analysis", 
        "Track Progress"
    ])
    
    with tab1:
        show_national_overview()
    
    with tab2:
        show_regional_breakdown()
    
    with tab3:
        show_daily_progress()


if __name__ == "__main__":
    main()