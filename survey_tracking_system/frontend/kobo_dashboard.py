import os
import io
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Any
from functools import lru_cache

import pandas as pd
import requests
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pytz
import numpy as np

from config import get_api_base_url
from auth_manager import auth_manager, authenticated_request


# =============================================
# PDF & CHART EXPORT UTILITIES
# =============================================

def fig_to_image_bytes(fig, format="png", width=800, height=500):
    """Convert a Plotly figure to image bytes."""
    try:
        # Don't use deprecated engine parameter - kaleido is default
        return fig.to_image(format=format, width=width, height=height, scale=2)
    except Exception as e:
        print(f"Image conversion error: {e}")
        return None


def generate_chart_pdf(charts_data: List[Dict], title: str = "GBV ICT Readiness Report"):
    """
    Generate a PDF report with charts and summaries.
    charts_data: List of dicts with 'fig', 'title', 'summary' keys
    """
    try:
        from reportlab.lib.pagesizes import A4, landscape  # pyright: ignore[reportMissingModuleSource]
        from reportlab.lib.units import inch  # pyright: ignore[reportMissingModuleSource]
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak  # pyright: ignore[reportMissingModuleSource]
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # pyright: ignore[reportMissingModuleSource]
        from reportlab.lib import colors  # pyright: ignore[reportMissingModuleSource]
        from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY  # pyright: ignore[reportMissingModuleSource]
    except ImportError as e:
        print(f"PDF Import Error: {e}")
        return None
    
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), 
                               rightMargin=0.5*inch, leftMargin=0.5*inch,
                               topMargin=0.5*inch, bottomMargin=0.5*inch)
        
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1e4a8a')
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#1e4a8a')
        )
        
        summary_style = ParagraphStyle(
            'Summary',
            parent=styles['Normal'],
            fontSize=10,
            spaceBefore=10,
            spaceAfter=15,
            alignment=TA_JUSTIFY,
            leading=14
        )
        
        elements = []
        
        # Title page
        elements.append(Spacer(1, 1*inch))
        elements.append(Paragraph(title, title_style))
        elements.append(Spacer(1, 0.3*inch))
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 
                                 ParagraphStyle('Date', parent=styles['Normal'], alignment=TA_CENTER)))
        elements.append(Spacer(1, 0.5*inch))
        elements.append(Paragraph("Namibia Statistics Agency - GBV ICT Readiness Assessment", 
                                 ParagraphStyle('Subtitle', parent=styles['Normal'], alignment=TA_CENTER, fontSize=14)))
        elements.append(PageBreak())
        
        # Charts and summaries
        for idx, chart_info in enumerate(charts_data):
            # Chart title - sanitize text
            chart_title = str(chart_info.get('title', f'Chart {idx+1}')).replace('•', '-').replace('\n', ' ')
            elements.append(Paragraph(chart_title, heading_style))
            
            # Try to render chart as image
            fig = chart_info.get('fig')
            if fig:
                try:
                    img_bytes = fig_to_image_bytes(fig, width=900, height=400)
                    if img_bytes:
                        img_buffer = io.BytesIO(img_bytes)
                        img = Image(img_buffer, width=9*inch, height=4*inch)
                        elements.append(img)
                except Exception as img_err:
                    print(f"Chart image error: {img_err}")
                    elements.append(Paragraph("[Chart could not be rendered]", styles['Normal']))
            
            # Summary text - sanitize special characters
            summary = chart_info.get('summary', '')
            if summary:
                # Replace special characters that reportlab can't handle
                clean_summary = str(summary).replace('•', '-').replace('–', '-').replace('—', '-')
                clean_summary = clean_summary.replace('"', '"').replace('"', '"')
                clean_summary = clean_summary.replace(''', "'").replace(''', "'")
                # Convert newlines to HTML breaks for proper formatting
                clean_summary = clean_summary.replace('\n\n', '<br/><br/>').replace('\n', '<br/>')
                
                elements.append(Spacer(1, 0.2*inch))
                try:
                    elements.append(Paragraph(f"<b>Analysis:</b><br/>{clean_summary}", summary_style))
                except Exception as para_err:
                    print(f"Paragraph error: {para_err}")
                    # Fallback to basic text
                    simple_summary = summary.replace('\n', ' ').replace('•', '-')[:500]
                    elements.append(Paragraph(f"Analysis: {simple_summary}", styles['Normal']))
            
            elements.append(Spacer(1, 0.3*inch))
            
            # Add page break after each chart for better layout
            if idx < len(charts_data) - 1:
                elements.append(PageBreak())
        
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
    except Exception as e:
        print(f"PDF Generation Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_summary_text(chart_type: str, data: Dict) -> str:
    """Generate a written summary for different chart types."""
    
    summaries = {
        "completion_gauge": lambda d: f"""The survey has achieved {d.get('completion', 0):.1f}% completion against the target of {d.get('target', 90)} surveys. 
        Currently {d.get('completed', 0)} institutions have completed their assessments. 
        {'The survey is ahead of schedule.' if d.get('ahead', False) else 'Additional effort may be needed to meet the target.'}
        With {d.get('days_remaining', 0)} days remaining, an average of {d.get('daily_needed', 0):.1f} surveys per day would be required to reach the goal.""",
        
        "regional_comparison": lambda d: f"""Regional analysis shows varying levels of survey completion across {d.get('num_regions', 0)} regions. 
        {d.get('top_region', 'Unknown')} leads with {d.get('top_count', 0)} completed surveys ({d.get('top_pct', 0):.1f}% of their target), 
        while {d.get('lowest_region', 'Unknown')} has {d.get('lowest_count', 0)} completions. 
        The overall regional completion rate averages {d.get('avg_rate', 0):.1f}%.""",
        
        "indicator_distribution": lambda d: f"""Analysis of {d.get('category', 'indicators')} shows that {d.get('yes_pct', 0):.1f}% of institutions responded 'Yes', 
        {d.get('no_pct', 0):.1f}% responded 'No', and {d.get('unknown_pct', 0):.1f}% had unknown or other responses. 
        The strongest indicator is '{d.get('strongest', 'N/A')}' with {d.get('strongest_pct', 0):.1f}% positive responses, 
        while '{d.get('weakest', 'N/A')}' shows the most room for improvement at {d.get('weakest_pct', 0):.1f}%.""",
        
        "regional_responses": lambda d: f"""Across all {d.get('num_regions', 0)} regions, a total of {d.get('total_responses', 0)} indicator responses were recorded. 
        Of these, {d.get('total_yes', 0)} ({d.get('yes_pct', 0):.1f}%) were positive ('Yes'), 
        {d.get('total_no', 0)} ({d.get('no_pct', 0):.1f}%) were negative ('No'), 
        and {d.get('total_unknown', 0)} ({d.get('unknown_pct', 0):.1f}%) were unknown or other. 
        This indicates {'strong' if d.get('yes_pct', 0) > 60 else 'moderate' if d.get('yes_pct', 0) > 40 else 'limited'} ICT readiness across the assessed institutions.""",
        
        "daily_progress": lambda d: f"""The daily submission trend shows {d.get('total_days', 0)} days of data collection with an average of {d.get('avg_daily', 0):.1f} submissions per day. 
        The peak day recorded {d.get('peak_count', 0)} submissions on {d.get('peak_date', 'N/A')}. 
        Cumulative progress reached {d.get('cumulative', 0)} total submissions. 
        {'The trend is positive with increasing daily submissions.' if d.get('trend_up', False) else 'The submission rate has been steady.'}""",
        
        "heatmap": lambda d: f"""The regional heatmap visualization reveals varying levels of ICT readiness across indicator categories. 
        {d.get('best_region', 'Unknown')} shows the highest overall readiness scores, 
        particularly strong in {d.get('best_category', 'N/A')}. 
        Areas requiring attention include {d.get('weak_areas', 'several categories')} across multiple regions. 
        The data suggests targeted interventions should focus on {d.get('priority_focus', 'improving baseline infrastructure')}."""
    }
    
    generator = summaries.get(chart_type, lambda d: "Analysis of the data presented in this chart.")
    try:
        return generator(data)
    except Exception:
        return "Analysis of the data presented in this chart."


def create_download_section(fig, chart_title: str, summary_data: Dict, chart_type: str, key_prefix: str):
    """Create a download section with PDF and summary export options."""
    
    summary_text = generate_summary_text(chart_type, summary_data)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        # Download chart as PNG
        try:
            img_bytes = fig_to_image_bytes(fig, format="png", width=1200, height=600)
            if img_bytes:
                st.download_button(
                    label="📷 Download Chart (PNG)",
                    data=img_bytes,
                    file_name=f"{chart_title.replace(' ', '_').lower()}.png",
                    mime="image/png",
                    key=f"png_{key_prefix}",
                    use_container_width=True
                )
        except Exception:
            pass
    
    with col2:
        # Download summary as text
        full_summary = f"""
{chart_title}
{'='*len(chart_title)}

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

SUMMARY
-------
{summary_text}

---
Report generated by Namibia Statistics Agency - GBV ICT Readiness Assessment Dashboard
        """
        st.download_button(
            label="📝 Download Summary (TXT)",
            data=full_summary,
            file_name=f"{chart_title.replace(' ', '_').lower()}_summary.txt",
            mime="text/plain",
            key=f"txt_{key_prefix}",
            use_container_width=True
        )
    
    with col3:
        # Show/hide summary in expander
        with st.expander("📊 View Analysis", expanded=False):
            st.markdown(f"**{chart_title}**")
            st.markdown(summary_text)


def create_full_report_download(all_charts: List[Dict]):
    """Create a complete PDF report with all charts."""
    st.markdown("---")
    st.markdown("### 📥 Export Complete Report")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Generate full PDF
        pdf_bytes = generate_chart_pdf(all_charts, "GBV ICT Readiness Assessment Report")
        if pdf_bytes:
            st.download_button(
                label="📄 Download Full Report (PDF)",
                data=pdf_bytes,
                file_name=f"gbv_readiness_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                key="full_pdf_report",
                use_container_width=True
            )
        else:
            st.info("PDF generation requires 'reportlab' package. Install with: pip install reportlab")
    
    with col2:
        # Generate all summaries as text
        all_summaries = f"""
GBV ICT READINESS ASSESSMENT - COMPLETE ANALYSIS
{'='*50}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Namibia Statistics Agency

"""
        for chart in all_charts:
            all_summaries += f"""
{chart.get('title', 'Chart')}
{'-'*len(chart.get('title', 'Chart'))}
{chart.get('summary', 'No summary available.')}

"""
        
        st.download_button(
            label="📋 Download All Summaries (TXT)",
            data=all_summaries,
            file_name=f"gbv_readiness_summaries_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            key="full_summaries",
            use_container_width=True
        )


API_BASE_URL = get_api_base_url().rstrip("/")

# Namibia timezone for real-time updates
TZ = pytz.timezone("Africa/Windhoek")

# =============================================
# CACHING CONFIGURATION
# =============================================
# Cache TTL in seconds (2 minutes for real-time feel, but reduces API calls)
CACHE_TTL = 120


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


@st.cache_data(ttl=CACHE_TTL, show_spinner="Fetching data...")
def fetch_json_cached(path: str) -> Dict[str, Any]:
    """Fetch JSON data from the API with caching."""
    try:
        url = f"{API_BASE_URL}{path}"
        # Increase timeout for KoBoToolbox API which can be slow
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        return {"_fetch_error": str(exc)}


def fetch_json(path: str, params=None) -> Dict[str, Any]:
    """Fetch JSON data from the API."""
    # Use cached version for common endpoints without params
    if params is None and path in ["/api/kobo/summary", "/api/kobo/submissions", "/api/health"]:
        result = fetch_json_cached(path)
        if "_fetch_error" in result:
            st.error(f"Failed to fetch {path}: {result['_fetch_error']}")
            return {}
        return result
    
    # Non-cached fetch for parameterized requests
    try:
        url = f"{API_BASE_URL}{path}"
        resp = requests.get(url, params=params or {}, timeout=60)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        st.error(f"Failed to fetch {path}: {exc}")
        return {}


def apply_light_theme_to_chart(fig):
    """Apply light theme styling to any Plotly chart - white hover tooltips."""
    fig.update_layout(
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_family="Inter, sans-serif",
            font_color="#1a1a1a",
            bordercolor="#d1d5db"
        )
    )
    return fig


@st.cache_data(ttl=CACHE_TTL, show_spinner="Loading survey data...")
def get_all_data():
    """Fetch and cache all data in one call to avoid multiple API requests."""
    summary = fetch_json_cached("/api/kobo/summary")
    submissions_data = fetch_json_cached("/api/kobo/submissions")
    
    # Check for fetch errors
    has_summary_error = "_fetch_error" in summary
    has_submissions_error = "_fetch_error" in submissions_data
    
    # Extract submissions from response
    if has_submissions_error:
        submissions = []
    elif isinstance(submissions_data, dict) and "submissions" in submissions_data:
        submissions = submissions_data.get("submissions", [])
    elif isinstance(submissions_data, list):
        submissions = submissions_data
    else:
        submissions = []
    
    return {
        "summary": {} if has_summary_error else summary,
        "submissions": submissions,
        "by_region": {} if has_summary_error else summary.get("by_region", {}),
        "by_date": {} if has_summary_error else summary.get("by_date", {}),
        "total_submissions": 0 if has_summary_error else summary.get("total_submissions", len(submissions))
    }


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def process_institutions(submissions: List[Dict]) -> List[Dict]:
    """Process and cache institution data from submissions."""
    institutions = []
    for sub in submissions:
        inst_name = get_institution_name(sub)
        region = get_region_name(sub)
        institutions.append({
            "name": inst_name,
            "region": region,
            "data": sub
        })
    institutions.sort(key=lambda x: (x["region"], x["name"]))
    return institutions


def get_institution_name(sub: Dict) -> str:
    """Extract institution name from submission."""
    inst = sub.get("grp_login/institution", "") or sub.get("institution", "") or sub.get("grp_login/institution_name", "")
    if inst:
        return inst.replace("_", " ").title()
    return "Unknown Institution"


def get_region_name(sub: Dict) -> str:
    """Extract and normalize region name from submission."""
    region = sub.get("grp_login/resp_region_display", "") or sub.get("resp_region_display", "") or sub.get("region", "")
    if not region:
        return "Unknown"
    region_lower = region.lower()
    if "kavango" in region_lower:
        if "east" in region_lower:
            return "Kavango East"
        elif "west" in region_lower:
            return "Kavango West"
        return "Kavango"
    if "hardap" in region_lower:
        return "Hardap"
    if "erongo" in region_lower:
        return "Erongo"
    if "ohangwena" in region_lower:
        return "Ohangwena"
    if "omaheke" in region_lower:
        return "Omaheke"
    return region.title()


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def group_by_region(submissions: List[Dict]) -> Dict[str, List[Dict]]:
    """Group submissions by region with caching."""
    regional_data = {}
    for sub in submissions:
        region = get_region_name(sub)
        if region == "Unknown":
            continue
        if region not in regional_data:
            regional_data[region] = []
        regional_data[region].append(sub)
    return regional_data


def show_national_overview():
    """Display national overview with targets and progress."""
    st.markdown('<h2 class="section-header">National Overview</h2>', unsafe_allow_html=True)
    
    # Use cached data
    all_data = get_all_data()
    
    # Check if we have any data (either from summary or submissions)
    total_submissions = all_data["total_submissions"]
    if total_submissions == 0 and not all_data["submissions"]:
        # Try to count submissions directly
        total_submissions = len(all_data["submissions"]) if all_data["submissions"] else 0
    
    if total_submissions == 0 and not all_data["by_date"]:
        st.warning("No survey data available yet. Data will appear once submissions are received.")
        return
    
    by_date = all_data["by_date"]
    
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
    fig.update_layout(height=320, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#1a1a1a'))
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
    
    # Use cached data
    all_data = get_all_data()
    
    # Get submissions for regional analysis
    raw_submissions = all_data["submissions"]
    
    if not raw_submissions:
        st.warning("No survey data available yet.")
        return
    
    by_region = all_data["by_region"]
    
    # Active survey regions only (where surveys are taking place)
    all_regions = ["hardap", "erongo", "kavango", "ohangwena", "omaheke"]
    
    # Use cached submissions
    raw_submissions = all_data["submissions"]
    
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
        fig.update_layout(
            height=320,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#1a1a1a')
        )
        fig.update_xaxes(showgrid=True, gridcolor='lightgray')
        fig.update_yaxes(showgrid=True, gridcolor='lightgray')
        st.plotly_chart(fig, use_container_width=True)

        # === REGION REPORT BUTTONS ===
        regions_list = sorted(region_df['Region'].astype(str).tolist()) if not region_df.empty else []
        # region normalization helper (used by all report actions)
        def _map_region_val(rv):
            if not rv:
                return None
            rl = rv.lower()
            if "kavango" in rl:
                return "kavango"
            if "hardap" in rl:
                return "hardap"
            if "erongo" in rl:
                return "erongo"
            if "ohangwena" in rl:
                return "ohangwena"
            if "omaheke" in rl:
                return "omaheke"
            return rl

        if regions_list:
            st.markdown('<hr />')
            st.markdown('### Generate region-level reports')
            selected_region_quick = st.selectbox("Select region to report", regions_list, key='region_report_quick')
            
            # Helper function for region mapping (used in multiple buttons below)
            def _map_region_val(rv):
                if not rv: return None
                rl = rv.lower()
                if "kavango" in rl:
                    return "kavango"
                if "hardap" in rl:
                    return "hardap"
                if "erongo" in rl:
                    return "erongo"
                if "ohangwena" in rl:
                    return "ohangwena"
                if "omaheke" in rl:
                    return "omaheke"
                return rl
            
            c1, c2, c3 = st.columns([1,1,1])
            with c1:
                if st.button("📄 Generate PDF Report", key='gen_region_pdf'):
                    submissions_data = fetch_json("/api/kobo/submissions")
                    raw_submissions = submissions_data.get("submissions", []) if isinstance(submissions_data, dict) else (submissions_data or [])
                    pdf_bytes = _generate_region_report(selected_region_quick, raw_submissions)
                    st.download_button("Download Region PDF", data=pdf_bytes, file_name=f"region_report_{selected_region_quick.replace(' ','_')}.pdf", mime="application/pdf")
            with c2:
                include_sanitized = st.checkbox("Include sanitized submissions (no PII)", key='region_include_sanitized_quick')
                if st.button("📊 Generate Excel Workbook", key='gen_region_excel'):
                    submissions_data = fetch_json("/api/kobo/submissions")
                    raw_submissions = submissions_data.get("submissions", []) if isinstance(submissions_data, dict) else (submissions_data or [])
                    subs_for_region = [s for s in raw_submissions if _map_region_val(s.get('grp_login/resp_region_display') or s.get('resp_region_display') or s.get('region')) == (selected_region_quick or '').lower()]
                    excel_bytes = build_indicators_excel(subs_for_region, include_sanitized=include_sanitized)
                    st.download_button("Download Region Excel", data=excel_bytes, file_name=f"region_indicators_{selected_region_quick.replace(' ','_')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            with c3:
                if st.button("📥 Generate All Region Reports (ZIP)", key='gen_all_regions'):
                    # generate workbooks for all regions, zip them
                    submissions_data = fetch_json("/api/kobo/submissions")
                    raw_submissions = submissions_data.get("submissions", []) if isinstance(submissions_data, dict) else (submissions_data or [])
                    import zipfile, tempfile
                    from io import BytesIO
                    tmpbuf = BytesIO()
                    with zipfile.ZipFile(tmpbuf, 'w') as zf:
                        for region_name in regions_list:
                            subs_for_region = [s for s in raw_submissions if _map_region_val(s.get('grp_login/resp_region_display') or s.get('resp_region_display') or s.get('region')) == (region_name or '').lower()]
                            excel_bytes = build_indicators_excel(subs_for_region, include_sanitized=include_sanitized)
                            zf.writestr(f"region_{region_name.replace(' ','_')}.xlsx", excel_bytes)
                    tmpbuf.seek(0)
                    st.download_button("Download ZIP of Region Workbooks", data=tmpbuf.read(), file_name="region_reports.zip", mime="application/zip")


# =============================================
# GBV ICT READINESS INDICATORS - COMPLETE LIST
# =============================================

GBV_INDICATORS = {
    "Policy & Legal Framework": {
        "description": "Assessment of institutional policies and legal frameworks for GBV response",
        "indicators": {
            "grp2/q2_1_1": "Has ICT policy document",
            "grp2/q2_1_2": "Policy includes GBV provisions",
            "grp2/q2_1_3": "Has data protection policy",
            "grp2/q2_1_4": "Has information security policy",
            "grp2/q2_1_5": "Has disaster recovery plan",
            "grp2/q2_1_6": "Has business continuity plan",
            "grp2/q2_1_7": "Has ICT governance framework",
            "grp2/q2_4_1": "Has dedicated ICT budget",
            "grp2/q2_5_1": "Conducts regular ICT audits",
            "grp2/q2_5_2": "Has ICT risk assessment process",
            "grp2/q2_5_3": "Staff trained on data protection",
            "grp2/q2_5_4": "Has incident response procedures",
            "grp2/q2_5_5": "Compliant with national ICT standards"
        }
    },
    "Human Resources & Capacity": {
        "description": "ICT staffing levels and technical capabilities",
        "indicators": {
            "grp3/q3_1_1": "Has dedicated ICT staff",
            "grp3/q3_1_2": "ICT staff has formal qualifications",
            "grp3/q3_1_3": "ICT staff receives regular training",
            "grp3/q3_1_4": "Has ICT support arrangement"
        }
    },
    "Network Infrastructure": {
        "description": "Internet connectivity and network equipment",
        "indicators": {
            "grp3/q3_2_1": "Has fiber optic connection",
            "grp3/q3_2_2": "Has wireless network (WiFi)",
            "grp3/q3_2_3": "Has internet connectivity",
            "grp3/q3_2_4": "Has network equipment (routers/switches)",
            "grp3/q3_2_5": "Has network monitoring tools"
        }
    },
    "Hardware & Software": {
        "description": "Computing devices and software systems",
        "indicators": {
            "grp3/q3_3_1": "Has case management system",
            "grp3/q3_4_1": "Has access control system",
            "grp3/q3_4_2": "Has antivirus/security software",
            "grp3/q3_4_3": "Has audit logging system"
        }
    },
    "Data Management & Security": {
        "description": "Data handling, backup, and security measures",
        "indicators": {
            "grp3/q3_5_1": "Has data validation procedures",
            "grp3/q3_5_2": "Has data encryption",
            "grp3/q3_5_3": "Has data sharing protocols",
            "grp3/q3_5_4": "Has data retention policy",
            "grp3/q3_5_5": "Has data quality assurance"
        }
    },
    "Systems & Applications": {
        "description": "Information systems and digital tools for GBV response",
        "indicators": {
            "grp4/q4_1_1": "Has GBV reporting system",
            "grp4/q4_1_2": "System allows anonymous reporting",
            "grp4/q4_2_1": "Has referral management system",
            "grp4/q4_2_2": "Has case tracking system",
            "grp4/q4_3_1": "Type of IT support (in-house/outsourced)",
            "grp4/q4_4_1": "Has data backup system",
            "grp4/q4_4_2": "Has disaster recovery system",
            "grp4/q4_4_3": "Has cloud-based services"
        }
    }
}

def get_all_indicators_flat():
    """Return flattened list of all indicator keys and labels."""
    flat = []
    for category, data in GBV_INDICATORS.items():
        for key, label in data["indicators"].items():
            flat.append({"category": category, "key": key, "label": label})
    return flat


def calculate_indicator_stats(submissions: List[Dict], indicator_key: str) -> Dict:
    """Calculate yes/no/dk statistics for an indicator."""
    values = [s.get(indicator_key, "").lower().strip() for s in submissions if s.get(indicator_key)]
    total = len(values)
    if total == 0:
        return {"yes": 0, "no": 0, "dk": 0, "total": 0, "yes_pct": 0, "no_pct": 0, "dk_pct": 0}
    
    yes_count = sum(1 for v in values if v in ["yes", "y", "true", "1"])
    no_count = sum(1 for v in values if v in ["no", "n", "false", "0"])
    dk_count = sum(1 for v in values if v in ["dk", "don't know", "unknown", "na", "n/a"])
    other_count = total - yes_count - no_count - dk_count
    
    return {
        "yes": yes_count,
        "no": no_count,
        "dk": dk_count + other_count,
        "total": total,
        "yes_pct": round(yes_count / total * 100, 1) if total > 0 else 0,
        "no_pct": round(no_count / total * 100, 1) if total > 0 else 0,
        "dk_pct": round((dk_count + other_count) / total * 100, 1) if total > 0 else 0
    }


def calculate_category_score(submissions: List[Dict], category: str) -> float:
    """Calculate overall readiness score for a category (0-100)."""
    if category not in GBV_INDICATORS:
        return 0
    
    indicators = GBV_INDICATORS[category]["indicators"]
    scores = []
    
    for key in indicators.keys():
        stats = calculate_indicator_stats(submissions, key)
        if stats["total"] > 0:
            scores.append(stats["yes_pct"])
    
    return round(sum(scores) / len(scores), 1) if scores else 0


def show_reports_page():
    """Display GBV ICT Readiness Indicators Report - Institutional and Regional Data."""
    st.markdown('<h2 class="section-header">📋 GBV ICT Readiness Indicators Report</h2>', unsafe_allow_html=True)
    
    # Use cached data
    all_data = get_all_data()
    submissions = all_data["submissions"]
    
    if not submissions:
        st.warning("No submission data available for analysis")
        return
    
    # Helper function to get institution name (use cached version)
    def get_institution(sub):
        inst = sub.get("grp_login/institution", "") or sub.get("institution", "") or sub.get("grp_login/institution_name", "")
        if inst:
            # Clean up institution name
            return inst.replace("_", " ").title()
        return "Unknown Institution"
    
    # Helper function to get region
    def get_region(sub):
        region = sub.get("grp_login/resp_region_display", "") or sub.get("resp_region_display", "") or sub.get("region", "")
        if not region:
            return "Unknown"
        region_lower = region.lower()
        if "kavango" in region_lower:
            if "east" in region_lower:
                return "Kavango East"
            elif "west" in region_lower:
                return "Kavango West"
            return "Kavango"
        if "hardap" in region_lower:
            return "Hardap"
        if "erongo" in region_lower:
            return "Erongo"
        if "ohangwena" in region_lower:
            return "Ohangwena"
        if "omaheke" in region_lower:
            return "Omaheke"
        return region.title()
    
    # Helper to format response value
    def format_response(val):
        if val is None or val == "":
            return "—"
        val_str = str(val).strip().lower()
        if val_str in ["yes", "y", "true", "1"]:
            return "✅ Yes"
        elif val_str in ["no", "n", "false", "0"]:
            return "❌ No"
        elif val_str in ["dk", "don't know", "unknown", "na", "n/a"]:
            return "❓ Unknown"
        else:
            return str(val).title()
    
    st.info(f"**📊 Total Assessments: {len(submissions)} institutions**")
    
    # Build institution list for use in other sections
    institutions = []
    for sub in submissions:
        inst_name = get_institution(sub)
        region = get_region(sub)
        institutions.append({
            "name": inst_name,
            "region": region,
            "data": sub
        })
    
    # Sort by region then institution
    institutions.sort(key=lambda x: (x["region"], x["name"]))
    
    # Region filter for all sections
    regions = sorted(list(set(inst["region"] for inst in institutions if inst["region"] != "Unknown")))
    region_filter = st.selectbox("🗺️ Filter by Region", ["All Regions"] + regions, key="region_filter")
    
    st.markdown("---")
    
    # ==========================================
    # KEY INDICATORS MAPPING - 8 specific indicators
    # ==========================================
    KEY_INDICATORS = {
        "ICT Support": {"key": "grp3/q3_1_4", "label": "Availability of ICT Support Services"},
        "ICT Policy": {"key": "grp2/q2_1_1", "label": "Availability of ICT Policies"},
        "Human Resource": {"key": "grp3/q3_1_1", "label": "Human Resource (ICT Staff)"},
        "Equipment": {"key": "grp3/q3_2_4", "label": "Computing Equipment (Network Devices)"},
        "Email": {"key": "grp3/q3_2_2", "label": "Email/Communication Services (WiFi)"},
        "Data System": {"key": "grp4/q4_1_1", "label": "Data Collection System"},
        "Database": {"key": "grp4/q4_4_1", "label": "Availability of Database/Backup"},
        "Internet": {"key": "grp3/q3_2_3", "label": "Availability of Internet"},
    }
    
    # Institution Group classification
    INSTITUTION_GROUPS = {
        "Police": {"color": "#3b82f6", "keywords": ["police", "nampol", "police station"]},
        "Ministry of Health Services": {"color": "#22c55e", "keywords": ["clinic", "hospital", "health", "medical"]},
        "Correctional Services": {"color": "#ef4444", "keywords": ["prison", "correctional", "custody"]},
        "Ministry of Gender": {"color": "#a855f7", "keywords": ["women", "children", "shelter", "gender"]},
    }
    
    def classify_institution_group(inst_name):
        """Classify institution into groups based on name keywords."""
        inst_lower = inst_name.lower()
        for group, info in INSTITUTION_GROUPS.items():
            for keyword in info["keywords"]:
                if keyword in inst_lower:
                    return group
        return "Other"
    
    def calculate_yes_percentage(insts_list, indicator_key):
        """Calculate percentage of 'Yes' responses for an indicator."""
        yes_count = 0
        total = 0
        for inst in insts_list:
            value = str(inst["data"].get(indicator_key, "")).strip().lower()
            if value:
                total += 1
                if value in ["yes", "y", "true", "1"]:
                    yes_count += 1
        return round(yes_count / total * 100, 1) if total > 0 else 0
    
    # Group data by region
    regional_data = {}
    for inst in institutions:
        region = inst["region"]
        if region == "Unknown":
            continue
        if region not in regional_data:
            regional_data[region] = []
        regional_data[region].append(inst)
    
    # Group data by institution type
    institution_groups_data = {}
    for inst in institutions:
        group = classify_institution_group(inst["name"])
        if group not in institution_groups_data:
            institution_groups_data[group] = []
        institution_groups_data[group].append(inst)
    
    # ==========================================
    # SECTION 0: KEY INDICATOR CHARTS
    # ==========================================
    st.markdown("""
    <div class="section-divider" style="background: linear-gradient(135deg, #0066cc 0%, #3b82f6 100%); border-left: 4px solid #1e40af;">
        <h3 style="color: white;">📊 Key ICT Readiness Indicators</h3>
        <p style="color: rgba(255,255,255,0.8);">8 critical indicators compared across regions and institution groups</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ---- CHART 1: Key Indicators by REGION (Grouped Bar Chart) ----
    st.markdown("### 🗺️ ICT Readiness Indicators by Region")
    
    # Build data for regional grouped bar chart
    region_indicator_data = []
    for region in sorted(regional_data.keys()):
        insts = regional_data[region]
        for ind_name, ind_info in KEY_INDICATORS.items():
            pct = calculate_yes_percentage(insts, ind_info["key"])
            region_indicator_data.append({
                "Region": region,
                "Indicator": ind_name,
                "Yes_Pct": pct
            })
    
    if region_indicator_data:
        region_df = pd.DataFrame(region_indicator_data)
        
        # Define colors for each indicator
        indicator_colors = {
            "ICT Support": "#22c55e",
            "ICT Policy": "#f97316", 
            "Human Resource": "#ef4444",
            "Equipment": "#8b5cf6",
            "Email": "#06b6d4",
            "Data System": "#a855f7",
            "Database": "#eab308",
            "Internet": "#3b82f6"
        }
        
        fig_region = go.Figure()
        
        for indicator in KEY_INDICATORS.keys():
            df_ind = region_df[region_df["Indicator"] == indicator]
            fig_region.add_trace(go.Bar(
                name=indicator,
                x=df_ind["Region"],
                y=df_ind["Yes_Pct"],
                marker_color=indicator_colors.get(indicator, "#64748b"),
                text=[f"{v:.0f}%" for v in df_ind["Yes_Pct"]],
                textposition='outside',
                textfont=dict(size=9)
            ))
        
        # Add 70% threshold line
        fig_region.add_hline(y=70, line_dash="dash", line_color="#3b82f6", 
                           annotation_text="70% Target", annotation_position="right")
        
        fig_region.update_layout(
            barmode='group',
            title=dict(text="ICT Readiness Indicators by Region", font=dict(size=16, color='#1a1a1a')),
            height=450,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#1a1a1a'),
            xaxis=dict(title="Region", tickangle=45),
            yaxis=dict(title="Percentage (%)", range=[0, 110]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hoverlabel=dict(bgcolor="white", font_size=12, font_color="#1a1a1a", bordercolor="#d1d5db"),
            margin=dict(l=60, r=40, t=80, b=100)
        )
        
        st.plotly_chart(fig_region, use_container_width=True, key="key_indicators_by_region")
        
        # Summary stats
        with st.expander("📊 Regional Summary Statistics"):
            summary_rows = []
            for region in sorted(regional_data.keys()):
                row = {"Region": region, "Institutions": len(regional_data[region])}
                for ind_name, ind_info in KEY_INDICATORS.items():
                    pct = calculate_yes_percentage(regional_data[region], ind_info["key"])
                    row[ind_name] = f"{pct:.0f}%"
                summary_rows.append(row)
            st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # ---- CHART 1B: Institution Groups per Region BY INDICATOR (with filter) ----
    st.markdown("### 🏢 Institution Groups per Region by Indicator")
    st.markdown("*Select an indicator to see how many institutions in each group (per region) meet that requirement*")
    
    # Define group order and colors
    group_order = ["Police", "Ministry of Health Services", "Correctional Services", "Ministry of Gender", "Other"]
    group_colors = {
        "Police": "#3b82f6",
        "Ministry of Health Services": "#22c55e", 
        "Correctional Services": "#ef4444",
        "Ministry of Gender": "#a855f7",
        "Other": "#64748b"
    }
    
    # Indicator filter dropdown
    indicator_options = {name: info["label"] for name, info in KEY_INDICATORS.items()}
    selected_indicator = st.selectbox(
        "📊 Select Indicator to View",
        options=list(indicator_options.keys()),
        format_func=lambda x: f"{x} - {indicator_options[x]}",
        key="indicator_filter_chart"
    )
    
    if selected_indicator:
        selected_key = KEY_INDICATORS[selected_indicator]["key"]
        selected_label = KEY_INDICATORS[selected_indicator]["label"]
        
        # Build data: count "Yes" responses per institution group per region
        indicator_region_group_data = []
        
        for region in sorted(regional_data.keys()):
            insts = regional_data[region]
            
            # Group institutions by type within this region
            group_yes_counts = {g: 0 for g in group_order}
            group_total_counts = {g: 0 for g in group_order}
            
            for inst in insts:
                group = classify_institution_group(inst["name"])
                group_total_counts[group] = group_total_counts.get(group, 0) + 1
                
                # Check if this institution answered "Yes" to the selected indicator
                value = str(inst["data"].get(selected_key, "")).strip().lower()
                if value in ["yes", "y", "true", "1"]:
                    group_yes_counts[group] = group_yes_counts.get(group, 0) + 1
            
            for group in group_order:
                indicator_region_group_data.append({
                    "Region": region,
                    "Institution Group": group,
                    "Yes Count": group_yes_counts[group],
                    "Total": group_total_counts[group]
                })
        
        if indicator_region_group_data:
            indicator_df = pd.DataFrame(indicator_region_group_data)
            
            fig_indicator_groups = go.Figure()
            
            for group in group_order:
                df_group = indicator_df[indicator_df["Institution Group"] == group]
                fig_indicator_groups.add_trace(go.Bar(
                    name=group,
                    x=df_group["Region"],
                    y=df_group["Yes Count"],
                    marker_color=group_colors.get(group, "#64748b"),
                    text=df_group["Yes Count"],
                    textposition='outside',
                    textfont=dict(size=9),
                    hovertemplate="<b>%{x}</b><br>" + group + "<br>Yes: %{y}<extra></extra>"
                ))
            
            fig_indicator_groups.update_layout(
                barmode='group',
                title=dict(
                    text=f"'{selected_indicator}' - Institutions with 'Yes' by Region & Group",
                    font=dict(size=15, color='#1a1a1a')
                ),
                height=450,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#1a1a1a'),
                xaxis=dict(title="Region", tickangle=45),
                yaxis=dict(title="Number of Institutions (Yes)"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                hoverlabel=dict(bgcolor="white", font_size=12, font_color="#1a1a1a", bordercolor="#d1d5db"),
                margin=dict(l=60, r=40, t=100, b=100)
            )
            
            st.plotly_chart(fig_indicator_groups, use_container_width=True, key=f"indicator_groups_{selected_indicator}")
            
            # Summary info
            total_yes = indicator_df["Yes Count"].sum()
            total_insts = indicator_df["Total"].sum() // len(group_order)  # Avoid double counting
            st.info(f"**{selected_label}**: {total_yes} institutions answered 'Yes' out of {len(institutions)} total")
            
            # Detailed table
            with st.expander(f"📋 Detailed Data: {selected_indicator}"):
                pivot_yes = indicator_df.pivot(index='Region', columns='Institution Group', values='Yes Count').fillna(0).astype(int)
                pivot_yes['Total Yes'] = pivot_yes.sum(axis=1)
                pivot_yes = pivot_yes.reset_index()
                st.dataframe(pivot_yes, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # ---- CHART 2: Key Indicators by INSTITUTION GROUP (Grouped Bar Chart) ----
    st.markdown("### 🏛️ ICT Readiness Indicators by Institution Group")
    st.markdown("*Classification: Police Stations → Police | Clinics & Hospitals → Ministry of Health Services | Prisons → Correctional Services | Women & Children Shelters → Ministry of Gender*")
    
    # Build data for institution group bar chart
    group_indicator_data = []
    for group in ["Police", "Ministry of Health Services", "Correctional Services", "Ministry of Gender", "Other"]:
        if group in institution_groups_data:
            insts = institution_groups_data[group]
            for ind_name, ind_info in KEY_INDICATORS.items():
                pct = calculate_yes_percentage(insts, ind_info["key"])
                group_indicator_data.append({
                    "Institution Group": group,
                    "Indicator": ind_name,
                    "Yes_Pct": pct,
                    "Count": len(insts)
                })
    
    if group_indicator_data:
        group_df = pd.DataFrame(group_indicator_data)
        
        fig_group = go.Figure()
        
        for indicator in KEY_INDICATORS.keys():
            df_ind = group_df[group_df["Indicator"] == indicator]
            fig_group.add_trace(go.Bar(
                name=indicator,
                x=df_ind["Institution Group"],
                y=df_ind["Yes_Pct"],
                marker_color=indicator_colors.get(indicator, "#64748b"),
                text=[f"{v:.0f}%" for v in df_ind["Yes_Pct"]],
                textposition='outside',
                textfont=dict(size=9)
            ))
        
        # Add 70% threshold line
        fig_group.add_hline(y=70, line_dash="dash", line_color="#3b82f6",
                          annotation_text="70% Target", annotation_position="right")
        
        fig_group.update_layout(
            barmode='group',
            title=dict(text="ICT Readiness Indicators by Institution Group", font=dict(size=16, color='#1a1a1a')),
            height=450,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#1a1a1a'),
            xaxis=dict(title="Institution Group", tickangle=0),
            yaxis=dict(title="Percentage (%)", range=[0, 110]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hoverlabel=dict(bgcolor="white", font_size=12, font_color="#1a1a1a", bordercolor="#d1d5db"),
            margin=dict(l=60, r=40, t=80, b=60)
        )
        
        st.plotly_chart(fig_group, use_container_width=True, key="key_indicators_by_group")
        
        # Institution group counts
        group_counts = []
        for group in ["Police", "Ministry of Health Services", "Correctional Services", "Ministry of Gender", "Other"]:
            if group in institution_groups_data:
                group_counts.append({
                    "Institution Group": group,
                    "Count": len(institution_groups_data[group]),
                    "Color": INSTITUTION_GROUPS.get(group, {}).get("color", "#64748b")
                })
        
        if group_counts:
            st.markdown("**Institution Distribution by Group:**")
            col1, col2, col3, col4, col5 = st.columns(5)
            cols = [col1, col2, col3, col4, col5]
            for i, gc in enumerate(group_counts[:5]):
                with cols[i]:
                    st.metric(gc["Institution Group"], gc["Count"])
    
    st.markdown("---")
    
    # ==========================================
    # SECTION 1: INSTITUTIONAL COMPARISON TABLE
    # ==========================================
    st.markdown("""
    <div class="section-divider" style="background: linear-gradient(135deg, #1e4a8a 0%, #2563eb 100%); border-left: 4px solid #1e3a5f;">
        <h3 style="color: white;">📊 All Institutions - Indicator Comparison</h3>
        <p style="color: rgba(255,255,255,0.8);">Compare responses across all institutions by category</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Category selector for comparison
    selected_category = st.selectbox(
        "Select Indicator Category",
        options=list(GBV_INDICATORS.keys()),
        key="category_comparison"
    )
    
    if selected_category:
        cat_data = GBV_INDICATORS[selected_category]
        
        # Build comparison table
        comparison_rows = []
        for inst in institutions:
            if region_filter != "All Regions" and inst["region"] != region_filter:
                continue
            
            row = {
                "Institution": inst["name"],
                "Region": inst["region"]
            }
            
            for key, label in cat_data["indicators"].items():
                value = inst["data"].get(key, "")
                # Simplify for table display
                val_str = str(value).strip().lower() if value else ""
                if val_str in ["yes", "y", "true", "1"]:
                    row[label] = "✅"
                elif val_str in ["no", "n", "false", "0"]:
                    row[label] = "❌"
                elif val_str in ["dk", "don't know", "unknown", "na", "n/a"]:
                    row[label] = "❓"
                elif val_str:
                    row[label] = "📝"  # Has text response
                else:
                    row[label] = "—"
            
            comparison_rows.append(row)
        
        if comparison_rows:
            comparison_df = pd.DataFrame(comparison_rows)
            st.dataframe(comparison_df, use_container_width=True, hide_index=True)
            
            # Legend
            st.markdown("""
            **Legend:** ✅ Yes | ❌ No | ❓ Unknown/Don't Know | 📝 Text Response | — No Response
            """)
            
            # Visualization: Response distribution per indicator
            st.markdown("#### 📊 Response Distribution Charts")
            
            # Calculate counts for each indicator
            indicator_stats = []
            for key, label in cat_data["indicators"].items():
                yes_count = 0
                no_count = 0
                other_count = 0
                for inst in institutions:
                    if region_filter != "All Regions" and inst["region"] != region_filter:
                        continue
                    value = str(inst["data"].get(key, "")).strip().lower()
                    if value in ["yes", "y", "true", "1"]:
                        yes_count += 1
                    elif value in ["no", "n", "false", "0"]:
                        no_count += 1
                    elif value:
                        other_count += 1
                indicator_stats.append({
                    "Indicator": label[:30] + "..." if len(label) > 30 else label,
                    "Yes": yes_count,
                    "No": no_count,
                    "Unknown": other_count
                })
            
            stats_df = pd.DataFrame(indicator_stats)
            
            if len(stats_df) > 0:
                # Stacked horizontal bar chart
                stack_fig = go.Figure()
                stack_fig.add_trace(go.Bar(
                    name='Yes',
                    y=stats_df['Indicator'],
                    x=stats_df['Yes'],
                    orientation='h',
                    marker_color='#22c55e'
                ))
                stack_fig.add_trace(go.Bar(
                    name='No',
                    y=stats_df['Indicator'],
                    x=stats_df['No'],
                    orientation='h',
                    marker_color='#ef4444'
                ))
                stack_fig.add_trace(go.Bar(
                    name='Unknown',
                    y=stats_df['Indicator'],
                    x=stats_df['Unknown'],
                    orientation='h',
                    marker_color='#94a3b8'
                ))
                stack_fig.update_layout(
                    barmode='stack',
                    title="Response Counts by Indicator",
                    height=max(400, len(stats_df) * 35),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#1a1a1a'),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02)
                )
                st.plotly_chart(stack_fig, use_container_width=True, key=f"stack_{selected_category}")
                
                # Percentage bar chart
                stats_df = stats_df.copy()
                stats_df['Total'] = stats_df['Yes'] + stats_df['No'] + stats_df['Unknown']
                stats_df['Yes_Pct'] = (stats_df['Yes'] / stats_df['Total'].replace(0, 1) * 100).round(1)
                
                pct_fig = px.bar(
                    stats_df,
                    x='Yes_Pct',
                    y='Indicator',
                    orientation='h',
                    color='Yes_Pct',
                    color_continuous_scale=['#ef4444', '#f97316', '#eab308', '#22c55e'],
                    range_color=[0, 100],
                    title="Percentage of 'Yes' Responses"
                )
                pct_fig.update_layout(
                    height=max(400, len(stats_df) * 35),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#1a1a1a'),
                    xaxis_title="Yes %",
                    yaxis_title=""
                )
                pct_fig.update_xaxes(range=[0, 110])
                st.plotly_chart(pct_fig, use_container_width=True, key=f"pct_{selected_category}")
    
    # ==========================================
    # SECTION 2: REGIONAL LEVEL DATA
    # ==========================================
    st.markdown("""
    <div class="section-divider" style="background: linear-gradient(135deg, #059669 0%, #10b981 100%); border-left: 4px solid #047857;">
        <h3 style="color: white;">🗺️ Regional Level Data</h3>
        <p style="color: rgba(255,255,255,0.8);">Aggregated indicator data by region</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Group by region
    regional_data = {}
    for inst in institutions:
        region = inst["region"]
        if region == "Unknown":
            continue
        if region not in regional_data:
            regional_data[region] = []
        regional_data[region].append(inst)
    
    # Regional overview
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### Regions Covered")
        region_counts = []
        for region, insts in sorted(regional_data.items()):
            region_counts.append({
                "Region": region,
                "Institutions": len(insts)
            })
        
        region_df = pd.DataFrame(region_counts)
        st.dataframe(region_df, use_container_width=True, hide_index=True)
    
    with col2:
        # Bar chart of institutions per region
        if region_counts:
            fig = px.bar(
                pd.DataFrame(region_counts),
                x="Region",
                y="Institutions",
                color="Institutions",
                color_continuous_scale="Blues",
                title="Number of Institutions Assessed per Region"
            )
            fig.update_layout(
                height=300,
                plot_bgcolor='rgba(0,0,0,0)',
paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#1a1a1a'),
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Regional comparison across all categories
    st.markdown("### 📊 Regional Response Summary - All Categories")
    
    # Build regional summary data
    regional_summary_data = []
    for region, insts in sorted(regional_data.items()):
        total_yes = 0
        total_no = 0
        total_other = 0
        total_indicators = 0
        
        for inst in insts:
            for category, cat_data in GBV_INDICATORS.items():
                for key in cat_data["indicators"].keys():
                    value = str(inst["data"].get(key, "")).strip().lower()
                    total_indicators += 1
                    if value in ["yes", "y", "true", "1"]:
                        total_yes += 1
                    elif value in ["no", "n", "false", "0"]:
                        total_no += 1
                    elif value:
                        total_other += 1
        
        regional_summary_data.append({
            "Region": region,
            "Institutions": len(insts),
            "Yes": total_yes,
            "No": total_no,
            "Unknown": total_other,
            "Total Responses": total_yes + total_no + total_other
        })
    
    regional_summary_df = pd.DataFrame(regional_summary_data)
    
    if len(regional_summary_df) > 0:
        reg_col1, reg_col2 = st.columns(2)
        
        with reg_col1:
            # Stacked bar chart by region
            reg_stack_fig = go.Figure()
            reg_stack_fig.add_trace(go.Bar(
                name='Yes',
                x=regional_summary_df['Region'],
                y=regional_summary_df['Yes'],
                marker_color='#22c55e'
            ))
            reg_stack_fig.add_trace(go.Bar(
                name='No',
                x=regional_summary_df['Region'],
                y=regional_summary_df['No'],
                marker_color='#ef4444'
            ))
            reg_stack_fig.add_trace(go.Bar(
                name='Unknown',
                x=regional_summary_df['Region'],
                y=regional_summary_df['Unknown'],
                marker_color='#94a3b8'
            ))
            reg_stack_fig.update_layout(
                barmode='stack',
                title="Total Responses by Region",
                height=320,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#1a1a1a')
            )
            st.plotly_chart(
                reg_stack_fig, 
                use_container_width=True, 
                key="regional_stack_chart",
                config={'displayModeBar': False}
            )
        
        with reg_col2:
            # Pie chart of overall distribution
            total_yes = regional_summary_df['Yes'].sum()
            total_no = regional_summary_df['No'].sum()
            total_unknown = regional_summary_df['Unknown'].sum()
            
            if total_yes + total_no + total_unknown > 0:
                reg_pie_fig = go.Figure(data=[go.Pie(
                    labels=['Yes', 'No', 'Unknown/Other'],
                    values=[total_yes, total_no, total_unknown],
                    hole=.4,
                    marker_colors=['#22c55e', '#ef4444', '#94a3b8']
                )])
                reg_pie_fig.update_layout(
                    title="Overall Response Distribution (All Regions)",
                    height=320,
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#1a1a1a')
                )
                st.plotly_chart(reg_pie_fig, use_container_width=True, key="regional_pie_chart")
        
        # Regional comparison by category
        st.markdown("### 📈 Regional Comparison by Category")
        
        # Calculate category-level data per region
        region_category_data = []
        for region, insts in sorted(regional_data.items()):
            for cat_name, cat_info in GBV_INDICATORS.items():
                cat_yes = 0
                cat_total = 0
                for inst in insts:
                    for key in cat_info["indicators"].keys():
                        value = str(inst["data"].get(key, "")).strip().lower()
                        if value:
                            cat_total += 1
                            if value in ["yes", "y", "true", "1"]:
                                cat_yes += 1
                
                yes_pct = round(cat_yes / cat_total * 100, 1) if cat_total > 0 else 0
                region_category_data.append({
                    "Region": region,
                    "Category": cat_name.split(" & ")[0][:20],
                    "Yes_Count": cat_yes,
                    "Total": cat_total,
                    "Yes_Pct": yes_pct
                })
        
        region_cat_df = pd.DataFrame(region_category_data)
        
        if len(region_cat_df) > 0:
            # Grouped bar chart
            group_fig = px.bar(
                region_cat_df,
                x="Category",
                y="Yes_Count",
                color="Region",
                barmode="group",
                title="'Yes' Responses by Category and Region"
            )
            group_fig.update_layout(
                height=340,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#1a1a1a'),
                xaxis_tickangle=45
            )
            st.plotly_chart(group_fig, use_container_width=True, key="regional_group_chart")
    
    # Heatmap of regions vs categories
    if len(region_cat_df) > 0:
        try:
            pivot_df = region_cat_df.pivot(index='Region', columns='Category', values='Yes_Pct')
            
            heatmap_fig = px.imshow(
                pivot_df,
                labels=dict(x="Category", y="Region", color="Yes %"),
                color_continuous_scale=['#ef4444', '#f97316', '#eab308', '#22c55e'],
                title="Regional Response Heatmap (% Yes Responses)",
                aspect="auto"
            )
            heatmap_fig.update_layout(
                height=320,
paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#1a1a1a')
            )
            st.plotly_chart(heatmap_fig, use_container_width=True, key="regional_heatmap")
        except Exception as e:
            st.warning(f"Could not generate heatmap: {e}")
    
    # Regional indicator breakdown
    st.markdown("### Regional Indicator Summary")
    
    selected_region = st.selectbox(
        "Select Region",
        options=sorted(regional_data.keys()),
        key="region_selector"
    )
    
    if selected_region and selected_region in regional_data:
        region_insts = regional_data[selected_region]
        
        st.markdown(f"**{selected_region}** - {len(region_insts)} institution(s) assessed")
        
        sel_col1, sel_col2 = st.columns([1, 2])
        
        with sel_col1:
            # List institutions in this region
            st.markdown("**Institutions in this region:**")
            for inst in region_insts:
                st.markdown(f"- {inst['name']}")
        
        with sel_col2:
            # Region summary pie chart
            region_yes = 0
            region_no = 0
            region_other = 0
            for inst in region_insts:
                for cat_name, cat_info in GBV_INDICATORS.items():
                    for key in cat_info["indicators"].keys():
                        value = str(inst["data"].get(key, "")).strip().lower()
                        if value in ["yes", "y", "true", "1"]:
                            region_yes += 1
                        elif value in ["no", "n", "false", "0"]:
                            region_no += 1
                        elif value:
                            region_other += 1
            
            if region_yes + region_no + region_other > 0:
                sel_region_pie = go.Figure(data=[go.Pie(
                    labels=['Yes', 'No', 'Unknown'],
                    values=[region_yes, region_no, region_other],
                    hole=.4,
                    marker_colors=['#22c55e', '#ef4444', '#94a3b8']
                )])
                sel_region_pie.update_layout(
                    title=f"{selected_region} - Overall Responses",
                    height=280,
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#1a1a1a'),
                    margin=dict(l=20, r=20, t=40, b=20),
                    hoverlabel=dict(bgcolor="white", font_size=12, font_color="#1a1a1a", bordercolor="#d1d5db")
                )
                apply_light_theme_to_chart(sel_region_pie)
                st.plotly_chart(sel_region_pie, use_container_width=True, key=f"sel_region_pie_{selected_region}")
        
        st.markdown("---")
        
        # Regional indicator summary by category
        regional_category_tabs = st.tabs(list(GBV_INDICATORS.keys()))
        
        for idx, (category, cat_data) in enumerate(GBV_INDICATORS.items()):
            with regional_category_tabs[idx]:
                st.markdown(f"*{cat_data['description']}*")
                
                # Aggregate responses for this region
                indicator_summary = []
                for key, label in cat_data["indicators"].items():
                    yes_count = 0
                    no_count = 0
                    dk_count = 0
                    total = 0
                    
                    for inst in region_insts:
                        value = inst["data"].get(key, "")
                        if value:
                            total += 1
                            val_str = str(value).strip().lower()
                            if val_str in ["yes", "y", "true", "1"]:
                                yes_count += 1
                            elif val_str in ["no", "n", "false", "0"]:
                                no_count += 1
                            else:
                                dk_count += 1
                    
                    indicator_summary.append({
                        "Indicator": label,
                        "Yes": yes_count,
                        "No": no_count,
                        "Unknown/Other": dk_count,
                        "Total Responses": total
                    })
                
                summary_df = pd.DataFrame(indicator_summary)
                st.dataframe(summary_df, use_container_width=True, hide_index=True)
                
                # Visual chart for this category
                if not summary_df.empty and len(summary_df) > 0:
                    cat_region_fig = go.Figure()
                    
                    cat_region_fig.add_trace(go.Bar(
                        name='Yes',
                        x=summary_df['Indicator'],
                        y=summary_df['Yes'],
                        marker_color='#22c55e'
                    ))
                    cat_region_fig.add_trace(go.Bar(
                        name='No',
                        x=summary_df['Indicator'],
                        y=summary_df['No'],
                        marker_color='#ef4444'
                    ))
                    cat_region_fig.add_trace(go.Bar(
                        name='Unknown/Other',
                        x=summary_df['Indicator'],
                        y=summary_df['Unknown/Other'],
                        marker_color='#94a3b8'
                    ))
                    
                    cat_region_fig.update_layout(
                        barmode='stack',
                        title=f"{selected_region} - {category}",
                        xaxis_title="",
                        yaxis_title="Number of Institutions",
                        height=320,
                        plot_bgcolor='rgba(0,0,0,0)',
paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#1a1a1a'),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    cat_region_fig.update_xaxes(tickangle=45)
                    st.plotly_chart(cat_region_fig, use_container_width=True, key=f"cat_region_{category}_{selected_region}")
    
    # ==========================================
    # SECTION 3: COMPLETE INDICATOR LIST
    # ==========================================
    st.markdown("""
    <div class="section-divider" style="background: linear-gradient(135deg, #8b5cf6 0%, #a78bfa 100%); border-left: 4px solid #7c3aed;">
        <h3 style="color: white;">📋 Complete Indicator Reference</h3>
        <p style="color: rgba(255,255,255,0.8);">All GBV ICT Readiness indicators by category</p>
    </div>
    """, unsafe_allow_html=True)
    
    all_indicators = get_all_indicators_flat()
    
    ref_col1, ref_col2 = st.columns([3, 1])
    
    with ref_col1:
        # Full indicator list
        indicator_list_df = pd.DataFrame([
            {"#": i+1, "Category": ind["category"], "Indicator": ind["label"], "Form Field": ind["key"]}
            for i, ind in enumerate(all_indicators)
        ])
        st.dataframe(indicator_list_df, use_container_width=True, hide_index=True)
    
    with ref_col2:
        st.markdown("### Summary")
        st.metric("Total Indicators", len(all_indicators))
        st.metric("Categories", len(GBV_INDICATORS))
        st.metric("Institutions Assessed", len(submissions))
        st.metric("Regions Covered", len(regional_data))
    
    # ==========================================
    # SECTION 4: EXPORT DATA
    # ==========================================
    st.markdown("---")
    st.markdown("### 📥 Export Data")
    
    # Excel exports row
    st.markdown("#### 📊 Excel Exports")
    export_col1, export_col2 = st.columns(2)
    
    with export_col1:
        if st.button("📊 Download Full Institutional Data (Excel)", key="export_institutional"):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Sheet 1: All institutions with all indicators
                inst_rows = []
                for inst in institutions:
                    row = {
                        "Institution": inst["name"],
                        "Region": inst["region"]
                    }
                    for category, cat_data in GBV_INDICATORS.items():
                        for key, label in cat_data["indicators"].items():
                            value = inst["data"].get(key, "")
                            row[label] = str(value) if value else ""
                    inst_rows.append(row)
                
                pd.DataFrame(inst_rows).to_excel(writer, sheet_name='Institutional Data', index=False)
                
                # Sheet 2: Indicator reference
                indicator_list_df.to_excel(writer, sheet_name='Indicator Reference', index=False)
            
            output.seek(0)
            st.download_button(
                "💾 Download Excel",
                data=output.getvalue(),
                file_name="gbv_institutional_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    with export_col2:
        if st.button("📊 Download Regional Summary (Excel)", key="export_regional"):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Create regional summary sheets
                for region, insts in regional_data.items():
                    region_rows = []
                    for inst in insts:
                        row = {"Institution": inst["name"]}
                        for category, cat_data in GBV_INDICATORS.items():
                            for key, label in cat_data["indicators"].items():
                                value = inst["data"].get(key, "")
                                row[label] = str(value) if value else ""
                        region_rows.append(row)
                    
                    # Truncate sheet name to 31 chars (Excel limit)
                    sheet_name = region[:31]
                    pd.DataFrame(region_rows).to_excel(writer, sheet_name=sheet_name, index=False)
            
            output.seek(0)
            st.download_button(
                "💾 Download Excel",
                data=output.getvalue(),
                file_name="gbv_regional_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    # PDF and Summary exports row
    st.markdown("---")
    st.markdown("#### 📄 Charts & Analysis Reports")
    
    # Calculate summary statistics for PDF report
    total_yes = sum(regional_summary_df['Yes']) if 'Yes' in regional_summary_df.columns else 0
    total_no = sum(regional_summary_df['No']) if 'No' in regional_summary_df.columns else 0
    total_unknown = sum(regional_summary_df['Unknown']) if 'Unknown' in regional_summary_df.columns else 0
    total_responses = total_yes + total_no + total_unknown
    
    # Generate comprehensive summary text
    comprehensive_summary = f"""
GBV ICT READINESS ASSESSMENT - COMPREHENSIVE ANALYSIS REPORT
{'='*60}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Namibia Statistics Agency

EXECUTIVE SUMMARY
-----------------
This report presents the findings from the GBV ICT Readiness Assessment conducted across 
{len(regional_data)} regions in Namibia, covering {len(institutions)} institutions.

KEY FINDINGS
------------

1. OVERALL RESPONSE DISTRIBUTION
   - Total Indicator Responses: {total_responses:,}
   - Positive Responses (Yes): {total_yes:,} ({(total_yes/total_responses*100) if total_responses > 0 else 0:.1f}%)
   - Negative Responses (No): {total_no:,} ({(total_no/total_responses*100) if total_responses > 0 else 0:.1f}%)
   - Unknown/Other: {total_unknown:,} ({(total_unknown/total_responses*100) if total_responses > 0 else 0:.1f}%)

2. REGIONAL COVERAGE
"""
    
    for region, insts in sorted(regional_data.items()):
        comprehensive_summary += f"   - {region}: {len(insts)} institution(s)\n"
    
    comprehensive_summary += f"""
3. INDICATOR CATEGORIES ASSESSED
   The assessment covered {len(GBV_INDICATORS)} major indicator categories:
"""
    
    for idx, (cat_name, cat_info) in enumerate(GBV_INDICATORS.items(), 1):
        comprehensive_summary += f"   {idx}. {cat_name} ({len(cat_info['indicators'])} indicators)\n"
        comprehensive_summary += f"      {cat_info['description']}\n"
    
    comprehensive_summary += f"""
4. REGIONAL PERFORMANCE ANALYSIS
"""
    
    if len(regional_summary_df) > 0:
        for _, row in regional_summary_df.iterrows():
            region_total = row['Yes'] + row['No'] + row['Unknown']
            yes_pct = (row['Yes'] / region_total * 100) if region_total > 0 else 0
            comprehensive_summary += f"""
   {row['Region']}:
   - Institutions Assessed: {row['Institutions']}
   - Total Responses: {region_total}
   - Positive Rate: {yes_pct:.1f}%
"""
    
    comprehensive_summary += f"""
5. RECOMMENDATIONS
   Based on the assessment findings:
   - Regions with lower positive response rates should be prioritized for capacity building
   - Focus areas include: Policy & Legal Framework, Data Management & Security
   - Continued monitoring and follow-up assessments recommended

---
Report generated by Namibia Statistics Agency
GBV ICT Readiness Assessment Dashboard
"""
    
    pdf_col1, pdf_col2, pdf_col3 = st.columns(3)
    
    with pdf_col1:
        st.download_button(
            label="📄 Download Full Analysis Report (TXT)",
            data=comprehensive_summary,
            file_name=f"gbv_analysis_report_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            key="full_analysis_txt",
            use_container_width=True
        )
    
    with pdf_col2:
        # Create comprehensive PDF with charts and summaries
        charts_for_pdf = []
        
        # 1. Regional Response Distribution Chart
        if len(regional_summary_df) > 0:
            reg_stack_fig_export = go.Figure()
            reg_stack_fig_export.add_trace(go.Bar(name='Yes', x=regional_summary_df['Region'], y=regional_summary_df['Yes'], marker_color='#22c55e'))
            reg_stack_fig_export.add_trace(go.Bar(name='No', x=regional_summary_df['Region'], y=regional_summary_df['No'], marker_color='#ef4444'))
            reg_stack_fig_export.add_trace(go.Bar(name='Unknown', x=regional_summary_df['Region'], y=regional_summary_df['Unknown'], marker_color='#94a3b8'))
            reg_stack_fig_export.update_layout(
                barmode='stack', 
                title=dict(text="Total Responses by Region", font=dict(size=18, color='#1e4a8a')),
                height=450, 
                paper_bgcolor='white', 
                plot_bgcolor='#f8f9fa',
                xaxis=dict(title=dict(text="Region", font=dict(size=12, color='black')), tickangle=45, tickfont=dict(size=10, color='black'), showgrid=True, gridcolor='#e0e0e0'),
                yaxis=dict(title=dict(text="Number of Responses", font=dict(size=12, color='black')), tickfont=dict(size=10, color='black'), showgrid=True, gridcolor='#e0e0e0'),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
                margin=dict(l=60, r=40, t=80, b=100)
            )
            
            # Find best and worst performing regions
            regional_summary_df['Yes_Pct'] = regional_summary_df.apply(
                lambda r: (r['Yes'] / (r['Yes'] + r['No'] + r['Unknown']) * 100) if (r['Yes'] + r['No'] + r['Unknown']) > 0 else 0, axis=1
            )
            best_region = regional_summary_df.loc[regional_summary_df['Yes_Pct'].idxmax()] if len(regional_summary_df) > 0 else None
            worst_region = regional_summary_df.loc[regional_summary_df['Yes_Pct'].idxmin()] if len(regional_summary_df) > 0 else None
            
            best_info = f"{best_region['Region']} ({best_region['Yes_Pct']:.1f}% positive)" if best_region is not None else "N/A"
            worst_info = f"{worst_region['Region']} ({worst_region['Yes_Pct']:.1f}% positive)" if worst_region is not None else "N/A"
            yes_pct = (total_yes/total_responses*100) if total_responses > 0 else 0
            no_pct = (total_no/total_responses*100) if total_responses > 0 else 0
            unk_pct = (total_unknown/total_responses*100) if total_responses > 0 else 0
            
            charts_for_pdf.append({
                'fig': reg_stack_fig_export,
                'title': '1. Regional Response Distribution',
                'summary': f"""This chart shows the distribution of Yes, No, and Unknown responses across all {len(regional_data)} assessed regions in Namibia.

KEY FINDINGS:
- Total Responses Analyzed: {total_responses:,}
- Positive Responses (Yes): {total_yes:,} ({yes_pct:.1f}%)
- Negative Responses (No): {total_no:,} ({no_pct:.1f}%)
- Unknown/Other: {total_unknown:,} ({unk_pct:.1f}%)

REGIONAL PERFORMANCE:
- Best Performing: {best_info}
- Needs Improvement: {worst_info}

INTERPRETATION:
The stacked bars represent the total indicator responses per region. Green indicates positive ICT readiness, red indicates gaps, and gray represents data that needs verification."""
            })
            
            # 2. Institutions per Region Chart
            inst_fig = go.Figure(data=[
                go.Bar(x=regional_summary_df['Region'], y=regional_summary_df['Institutions'], marker_color='#3b82f6',
                       text=regional_summary_df['Institutions'], textposition='outside', textfont=dict(size=10, color='black'))
            ])
            inst_fig.update_layout(
                title=dict(text="Institutions Assessed per Region", font=dict(size=18, color='#1e4a8a')),
                height=450, 
                paper_bgcolor='white', 
                plot_bgcolor='#f8f9fa',
                xaxis=dict(title=dict(text="Region", font=dict(size=12, color='black')), tickangle=45, tickfont=dict(size=10, color='black'), showgrid=True, gridcolor='#e0e0e0'),
                yaxis=dict(title=dict(text="Number of Institutions", font=dict(size=12, color='black')), tickfont=dict(size=10, color='black'), showgrid=True, gridcolor='#e0e0e0'),
                margin=dict(l=60, r=40, t=80, b=100)
            )
            
            avg_inst = len(institutions)/len(regional_data) if len(regional_data) > 0 else 0
            region_list = "\n".join([f"- {row['Region']}: {row['Institutions']} institutions" for _, row in regional_summary_df.iterrows()])
            
            charts_for_pdf.append({
                'fig': inst_fig,
                'title': '2. Institutions Assessed per Region',
                'summary': f"""This chart displays the number of institutions that completed the GBV ICT Readiness assessment in each region.

KEY STATISTICS:
- Total Institutions Assessed: {len(institutions)}
- Number of Regions Covered: {len(regional_data)}
- Average Institutions per Region: {avg_inst:.1f}

DISTRIBUTION ANALYSIS:
{region_list}

INTERPRETATION:
This distribution helps identify which regions have greater institutional coverage and where additional assessment efforts may be needed."""
            })
            
            # 3. Regional Positive Response Rate Chart
            rate_fig = go.Figure(data=[
                go.Bar(x=regional_summary_df['Region'], y=regional_summary_df['Yes_Pct'], marker_color='#10b981',
                       text=[f"{v:.1f}%" for v in regional_summary_df['Yes_Pct']], textposition='outside', textfont=dict(size=9, color='black'))
            ])
            rate_fig.update_layout(
                title=dict(text="Positive Response Rate by Region (%)", font=dict(size=18, color='#1e4a8a')),
                height=450, 
                paper_bgcolor='white', 
                plot_bgcolor='#f8f9fa',
                xaxis=dict(title=dict(text="Region", font=dict(size=12, color='black')), tickangle=45, tickfont=dict(size=10, color='black'), showgrid=True, gridcolor='#e0e0e0'),
                yaxis=dict(title=dict(text="Positive Rate (%)", font=dict(size=12, color='black')), tickfont=dict(size=10, color='black'), showgrid=True, gridcolor='#e0e0e0', range=[0, 100]),
                margin=dict(l=60, r=40, t=80, b=100)
            )
            
            readiness_list = "\n".join([f"- {row['Region']}: {row['Yes_Pct']:.1f}% readiness" for _, row in regional_summary_df.sort_values('Yes_Pct', ascending=False).iterrows()])
            
            charts_for_pdf.append({
                'fig': rate_fig,
                'title': '3. Regional ICT Readiness Rates',
                'summary': f"""This chart compares the positive response rates (percentage of Yes answers) across all assessed regions.

READINESS LEVELS:
{readiness_list}

INTERPRETATION:
- Regions above 60%: Strong ICT readiness for GBV response
- Regions 40-60%: Moderate readiness, some improvements needed
- Regions below 40%: Priority areas requiring capacity building

RECOMMENDATIONS:
Lower-performing regions should receive targeted support in areas such as infrastructure, training, and policy implementation."""
            })
        
        # Try to generate PDF
        pdf_bytes = generate_chart_pdf(charts_for_pdf, "GBV ICT Readiness Assessment Report - Namibia")
        if pdf_bytes:
            st.download_button(
                label="📄 Download Full Report (PDF)",
                data=pdf_bytes,
                file_name=f"gbv_full_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                key="charts_pdf",
                use_container_width=True
            )
        else:
            st.info("📦 Install 'reportlab' for PDF exports")
    
    with pdf_col3:
        # Quick summary card
        st.download_button(
            label="📊 Download Summary Statistics",
            data=f"""GBV ICT Readiness - Quick Statistics
====================================
Date: {datetime.now().strftime('%Y-%m-%d')}

Regions Assessed: {len(regional_data)}
Institutions Covered: {len(institutions)}
Total Indicators: {len(all_indicators)}
Total Responses: {total_responses:,}

Response Breakdown:
- Yes: {total_yes:,} ({(total_yes/total_responses*100) if total_responses > 0 else 0:.1f}%)
- No: {total_no:,} ({(total_no/total_responses*100) if total_responses > 0 else 0:.1f}%)
- Unknown: {total_unknown:,} ({(total_unknown/total_responses*100) if total_responses > 0 else 0:.1f}%)
""",
            file_name="gbv_quick_stats.txt",
            mime="text/plain",
            key="quick_stats",
            use_container_width=True
        )


def show_daily_progress():
    """Display daily progress tracking and trends."""
    st.markdown('<h2 class="section-header">Progress Tracking</h2>', unsafe_allow_html=True)
    
    # Use cached data
    all_data = get_all_data()
    if not all_data["summary"]:
        st.error("Unable to fetch survey data")
        return
    
    by_date = all_data["by_date"]
    
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
            height=320,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#1a1a1a')
        )
        fig.update_xaxes(showgrid=True, gridcolor='lightgray')
        fig.update_yaxes(showgrid=True, gridcolor='lightgray')
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
            height=320,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#1a1a1a')
        )
        fig.update_xaxes(showgrid=True, gridcolor='lightgray')
        fig.update_yaxes(showgrid=True, gridcolor='lightgray')
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
        fig.update_layout(
            height=320,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#1a1a1a')
        )
        fig.update_xaxes(showgrid=True, gridcolor='lightgray')
        fig.update_yaxes(showgrid=True, gridcolor='lightgray')
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

    # --- EXPORT INDICATORS TO EXCEL ---
    with st.expander("Export Indicators to Excel"):
        submissions_data = fetch_json("/api/kobo/submissions")
        raw_submissions = submissions_data.get("submissions", []) if isinstance(submissions_data, dict) else (submissions_data or [])
        if not raw_submissions:
            st.info("No submissions to export")
        else:
            st.markdown("Select options for the indicators workbook:")
            scope = st.radio("Scope", ["All", "By Region", "By Institution"], horizontal=True)
            if scope == "By Region":
                # gather regions
                regions = sorted(list({(s.get('grp_login/resp_region_display') or s.get('resp_region_display') or s.get('region') or '').strip() for s in raw_submissions if (s.get('grp_login/resp_region_display') or s.get('resp_region_display') or s.get('region'))}))
                selected_region = st.selectbox("Select region", [r for r in regions if r])
            elif scope == "By Institution":
                insts = sorted(list({(s.get('grp_login/institution_name') or s.get('institution_name') or s.get('institution') or '').strip() for s in raw_submissions if (s.get('grp_login/institution_name') or s.get('institution_name') or s.get('institution'))}))
                selected_inst = st.selectbox("Select institution", [i for i in insts if i])

            if st.button("Generate Indicators Workbook"):
                with st.spinner("Computing indicators and building workbook..."):
                    # filter if needed
                    subs_for_export = raw_submissions
                    if scope == "By Region" and selected_region:
                        def _map_region_val(rv):
                            if not rv: return None
                            rl = rv.lower()
                            if "kavango" in rl: return "kavango"
                            if "hardap" in rl: return "hardap"
                            if "erongo" in rl: return "erongo"
                            if "ohangwena" in rl: return "ohangwena"
                            if "omaheke" in rl: return "omaheke"
                            return rl
                        subs_for_export = [s for s in raw_submissions if _map_region_val(s.get('grp_login/resp_region_display') or s.get('resp_region_display') or s.get('region')) == (selected_region or '').lower()]
                    if scope == "By Institution" and selected_inst:
                        subs_for_export = [s for s in raw_submissions if (selected_inst or '').lower() in ((s.get('grp_login/institution_name') or s.get('institution_name') or s.get('institution') or '').lower())]

                    include_sanitized = st.checkbox("Include sanitized submissions sheet (no PII)", value=False)
                    excel_bytes = build_indicators_excel(subs_for_export, include_sanitized=include_sanitized)
                    st.download_button(
                        "Download Indicators Workbook",
                        data=excel_bytes,
                        file_name="indicators_report.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    st.markdown("---")
                    # Consolidated long report exports
                    if st.button("📊 Generate Consolidated Excel (All Regions)"):
                        with st.spinner("Building consolidated workbook..."):
                            long_bytes = build_indicators_excel(subs_for_export, include_sanitized=include_sanitized, include_long=True)
                            st.download_button("Download Consolidated Workbook", data=long_bytes, file_name="long_indicators_report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                    if st.button("📄 Generate Consolidated PDF (All Regions)"):
                        try:
                            with st.spinner("Rendering consolidated PDF..."):
                                # Generate PDF using the built-in function
                                charts_data = [{
                                    'fig': None,
                                    'title': 'Consolidated Report',
                                    'summary': f'Report covers {len(subs_for_export)} submissions.'
                                }]
                                pdf_bytes = generate_chart_pdf(charts_data, "Consolidated GBV Report")
                                if pdf_bytes:
                                    st.download_button("Download Consolidated PDF", data=pdf_bytes, file_name="consolidated_report.pdf", mime="application/pdf")
                                else:
                                    st.info("PDF generation requires 'reportlab' package")
                        except Exception as e:
                            st.error(f"Unable to generate PDF: {e}")



# --- Helper functions: inference, aggregation, excel builder, plot rendering ---
import io
from collections import Counter
import numpy as np


def infer_question_types(submissions: List[Dict[str, Any]], sample_size: int = 500, cat_threshold: int = 30) -> Dict[str, Dict[str, Any]]:
    """Infer types for each question from a sample of submissions."""
    sample = submissions[:sample_size]
    keys = set().union(*(s.keys() for s in sample)) if sample else set()
    types = {}
    for k in sorted(keys):
        if k.startswith("_"):
            continue
        vals = [s.get(k) for s in sample if s.get(k) is not None]
        if not vals:
            types[k] = {"type": "unknown", "unique": 0}
            continue
        # flatten lists
        flat = []
        for v in vals:
            if isinstance(v, list):
                flat.extend([x for x in v if x is not None])
            else:
                flat.append(v)
        if not flat:
            types[k] = {"type": "unknown", "unique": 0}
            continue
        # numeric heuristic
        num_ok = 0
        for v in flat:
            try:
                float(str(v))
                num_ok += 1
            except:
                pass
        if num_ok / max(1, len(flat)) >= 0.8:
            types[k] = {"type": "numeric", "unique": len(set(flat))}
            continue
        # boolean heuristic
        lowered = [str(v).strip().lower() for v in flat if v is not None]
        if lowered and all(x in ("true", "false", "yes", "no", "y", "n", "1", "0") for x in lowered):
            types[k] = {"type": "boolean", "unique": len(set(lowered))}
            continue
        # multi-select
        if any(isinstance(v, list) for v in vals):
            opt_counts = Counter([str(x) for x in flat])
            types[k] = {"type": "multi-select", "unique": len(opt_counts), "top": opt_counts.most_common(5)}
            continue
        unique_vals = set(map(str, flat))
        if len(unique_vals) <= cat_threshold:
            types[k] = {"type": "categorical", "unique": len(unique_vals), "top": Counter(flat).most_common(5)}
        else:
            types[k] = {"type": "text", "unique": len(unique_vals)}
    return types


def compute_group_indicators(submissions: List[Dict[str, Any]], group_keys: List[str]) -> pd.DataFrame:
    """Compute indicators grouped by group_keys (institution or region)."""
    if not submissions:
        return pd.DataFrame()
    qtypes = infer_question_types(submissions)
    records = []
    for s in submissions:
        # get group value
        g = "Unknown"
        for k in group_keys:
            v = s.get(k)
            if v and str(v).strip():
                g = str(v).strip()
                break
        rec = {"Group": g}
        for q in qtypes.keys():
            rec[q] = s.get(q)
        records.append(rec)
    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame()
    grouped = df.groupby("Group")
    out_rows = []
    for name, group in grouped:
        row = {"Group": name, "Submissions": len(group)}
        for q, meta in qtypes.items():
            series = group[q]
            valid = series.dropna()
            if meta["type"] == "numeric":
                nums = pd.to_numeric(valid, errors='coerce').dropna()
                row[f"{q}__count"] = int(nums.count())
                row[f"{q}__mean"] = float(nums.mean()) if not nums.empty else None
                row[f"{q}__median"] = float(nums.median()) if not nums.empty else None
                row[f"{q}__min"] = float(nums.min()) if not nums.empty else None
                row[f"{q}__max"] = float(nums.max()) if not nums.empty else None
                row[f"{q}__sum"] = float(nums.sum()) if not nums.empty else None
            elif meta["type"] == "boolean":
                vals = [1 if str(x).strip().lower() in ("true","yes","1","y") else 0 for x in valid if pd.notna(x)]
                row[f"{q}__count"] = int(len(vals))
                row[f"{q}__percent_true"] = float(np.mean(vals) * 100) if vals else None
            elif meta["type"] == "categorical":
                vc = Counter([str(x) for x in valid if pd.notna(x)])
                if vc:
                    top, top_count = vc.most_common(1)[0]
                    row[f"{q}__count"] = int(sum(vc.values()))
                    row[f"{q}__top_value"] = top
                    row[f"{q}__top_pct"] = float(top_count / sum(vc.values()) * 100)
                else:
                    row[f"{q}__count"] = 0
                    row[f"{q}__top_value"] = None
                    row[f"{q}__top_pct"] = None
            elif meta["type"] == "multi-select":
                flat = []
                for v in valid:
                    if isinstance(v, list):
                        flat.extend([str(x) for x in v if x is not None])
                vc = Counter(flat)
                for opt, cnt in vc.most_common(10):
                    row[f"{q}__opt__{opt}"] = int(cnt)
            else:  # text
                non_empty = sum(1 for x in valid if str(x).strip())
                row[f"{q}__count"] = int(len(valid))
                row[f"{q}__non_empty"] = int(non_empty)
        out_rows.append(row)
    out_df = pd.DataFrame(out_rows)
    # ensure Submissions column present
    if "Submissions" not in out_df.columns:
        out_df["Submissions"] = 0
    return out_df


def _sanitize_submissions_for_export(submissions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove PII and unnecessary metadata from submissions for safe export.
    Keeps institution, region, submission date and response fields only.
    """
    pii_patterns = ["email", "phone", "name", "first_name", "last_name", "address", "gps", "id", "id_number", "idcard", "personal", "username"]
    sanitized = []
    for s in submissions:
        clean = {}
        # Keep institution/region/submission time
        keys_to_keep = ["grp_login/institution_name", "institution_name", "institution", "grp_login/resp_region_display", "resp_region_display", "region", "_submission_time"]
        for k, v in s.items():
            kl = k.lower()
            if kl in keys_to_keep:
                clean[k] = v
                continue
            # drop system/meta and PII
            if kl.startswith("meta") or kl.startswith("_meta"):
                continue
            if any(p in kl for p in pii_patterns):
                continue
            # otherwise include (assumed to be form answers)
            clean[k] = v
        # normalize submission time to date string only
        if "_submission_time" in clean:
            ts = clean.get("_submission_time")
            dt = clean_timestamp(ts)
            clean["submission_date"] = dt.strftime('%Y-%m-%d') if dt else None
            try:
                del clean["_submission_time"]
            except KeyError:
                pass
        sanitized.append(clean)
    return sanitized


def _compute_readiness_score_for_institution(filtered: List[Dict[str, Any]], readiness_keywords: List[str] = None) -> float:
    """Compute a simple readiness score (0-100) based on boolean indicators that match readiness keywords."""
    if readiness_keywords is None:
        readiness_keywords = ["internet", "power", "backup", "trained", "device", "computer", "laptop", "phone", "network", "wifi", "electric", "solar", "connect", "connectivity", "server", "data"]
    if not filtered:
        return None
    keys = set().union(*(s.keys() for s in filtered))
    indicator_keys = [k for k in keys if any(pk in k.lower() for pk in readiness_keywords)]
    if not indicator_keys:
        return None
    per_key_scores = []
    for k in indicator_keys:
        vals = [s.get(k) for s in filtered if s.get(k) is not None]
        if not vals:
            continue
        truthy = 0
        total = 0
        for v in vals:
            sv = str(v).strip().lower()
            if sv in ("true", "yes", "1", "y", "available", "present"):
                truthy += 1
            total += 1
        if total > 0:
            per_key_scores.append(truthy / total)
    if not per_key_scores:
        return None
    score = float(sum(per_key_scores) / len(per_key_scores) * 100)
    return round(score, 1)


def _classify_readiness(score: float) -> str:
    if score is None:
        return "Unknown"
    if score >= 80:
        return "High"
    if score >= 50:
        return "Medium"
    return "Low"


def _fig_to_png_bytes(fig) -> bytes:
    """Render a Plotly figure to PNG bytes using kaleido."""
    return fig.to_image(format='png', engine='kaleido')


def _generate_region_report(region_name: str, submissions: List[Dict[str, Any]]) -> bytes:
    """Generate a PDF for a single region."""
    if not region_name:
        return b''
    
    def _map_region_val(rv):
        if not rv: return None
        rl = rv.lower()
        if "kavango" in rl:
            return "kavango"
        if "hardap" in rl:
            return "hardap"
        if "erongo" in rl:
            return "erongo"
        if "ohangwena" in rl:
            return "ohangwena"
        if "omaheke" in rl:
            return "omaheke"
        return rl
    
    subs_for_region = [s for s in submissions if _map_region_val(s.get('grp_login/resp_region_display') or s.get('resp_region_display') or s.get('region')) == (region_name or '').lower()]
    
    try:
        charts_data = [{
            'fig': None,
            'title': f'{region_name} Region Report',
            'summary': f'This report covers {len(subs_for_region)} institutions in the {region_name} region.'
        }]
        pdf_bytes = generate_chart_pdf(charts_data, f"GBV Report - {region_name} Region")
        return pdf_bytes if pdf_bytes else b''
    except Exception:
        return b''


def build_indicators_excel(submissions: List[Dict[str, Any]], include_sanitized: bool = False, include_long: bool = False) -> bytes:
    """Build an Excel workbook with indicator data from submissions."""
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Sheet 1: Summary by indicator
        if submissions:
            # Get all unique keys from submissions
            all_keys = set()
            for s in submissions:
                all_keys.update(s.keys())
            
            # Filter to indicator keys (exclude metadata)
            indicator_keys = [k for k in sorted(all_keys) if not k.startswith('_') and not k.startswith('meta')]
            
            # Build summary data
            summary_rows = []
            for key in indicator_keys[:50]:  # Limit to first 50 indicators
                values = [s.get(key, '') for s in submissions]
                non_empty = [v for v in values if v]
                yes_count = sum(1 for v in non_empty if str(v).lower().strip() in ['yes', 'y', 'true', '1'])
                no_count = sum(1 for v in non_empty if str(v).lower().strip() in ['no', 'n', 'false', '0'])
                
                summary_rows.append({
                    'Indicator': key,
                    'Total Responses': len(non_empty),
                    'Yes': yes_count,
                    'No': no_count,
                    'Other': len(non_empty) - yes_count - no_count,
                    'Yes %': round(yes_count / len(non_empty) * 100, 1) if non_empty else 0
                })
            
            pd.DataFrame(summary_rows).to_excel(writer, sheet_name='Indicator Summary', index=False)
        
        # Sheet 2: Raw data (sanitized if requested)
        if include_sanitized and submissions:
            sanitized = _sanitize_submissions_for_export(submissions)
            if sanitized:
                df = pd.DataFrame(sanitized)
                # Limit columns
                cols = [c for c in df.columns if not c.startswith('_')][:30]
                df[cols].to_excel(writer, sheet_name='Submissions', index=False)
        
        # Sheet 3: Regional breakdown
        if submissions:
            regional_counts = {}
            for s in submissions:
                region = s.get('grp_login/resp_region_display') or s.get('resp_region_display') or s.get('region') or 'Unknown'
                regional_counts[region] = regional_counts.get(region, 0) + 1
            
            regional_df = pd.DataFrame([
                {'Region': k, 'Count': v} for k, v in sorted(regional_counts.items())
            ])
            regional_df.to_excel(writer, sheet_name='By Region', index=False)
    
    output.seek(0)
    return output.getvalue()


def show_raw_submissions():
    """Display recent submissions in a sanitized form (no PII)."""
    st.subheader(" Recent Submissions (Sanitized)")

    summary_data = fetch_json("/api/kobo/summary")

    if not summary_data:
        st.warning("No submission data available")
        return

    recent_submissions = summary_data.get("recent_submissions", [])

    if not recent_submissions:
        st.info("No submissions found")
        return

    # Sanitize submissions and show a compact preview (institution, region, date, core answers)
    sanitized = _sanitize_submissions_for_export(recent_submissions)
    if not sanitized:
        st.info("No sanitized submissions to display")
        return

    df = pd.DataFrame(sanitized)

    # Keep institution, region, submission_date and up to 6 answer columns
    cols = []
    for c in df.columns:
        if c in ["grp_login/institution_name", "institution_name", "institution", "grp_login/resp_region_display", "resp_region_display", "region", "submission_date"]:
            cols.append(c)
    # add other answer columns (exclude meta/PII and long text)
    answer_cols = [c for c in df.columns if c not in cols and not c.startswith("_")][:6]
    cols.extend(answer_cols)

    display_df = df[cols]
    display_df = display_df.rename(columns={
        'grp_login/institution_name': 'Institution',
        'institution_name': 'Institution',
        'institution': 'Institution',
        'grp_login/resp_region_display': 'Region',
        'resp_region_display': 'Region'
    })

    st.write(f"**Showing {len(display_df)} recent sanitized submissions (no PII)**")
    st.dataframe(display_df, use_container_width=True)





def main():
    st.set_page_config(
        page_title="GBV Readiness Survey Progress Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Auto-login with admin credentials if not already authenticated
    if not auth_manager.is_authenticated():
        # Silently log in with admin credentials
        auth_manager.login("admin", "Amazing@2001")
    
    # Show authentication status in sidebar
    auth_manager.show_user_info()
    
    # Modern NSA design system
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* GLOBAL FONT SETTING - All text uses Inter font */
    * {
        font-family: 'Inter', sans-serif;
    }
    
    /* COMPREHENSIVE WHITE BACKGROUND - Override all Streamlit defaults */
    html, body, [data-testid="stAppViewContainer"], 
    [data-testid="stApp"], [data-testid="stDecoration"],
    [data-testid="stToolbar"], [data-testid="stHeader"],
    .main, .block-container, section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        background: #ffffff !important;
    }
    
    /* FORCE ALL TEXT TO BE DARK - Override any theme that makes text white */
    html, body, .main, .stMarkdown, .stText, p, span, div, label, 
    [data-testid="stMarkdownContainer"], [data-testid="stText"] {
        color: #1a1a1a !important;
    }
    
    /* Sidebar text */
    section[data-testid="stSidebar"], 
    section[data-testid="stSidebar"] *, 
    section[data-testid="stSidebar"] .stMarkdown {
        color: #1a1a1a !important;
    }
    
    /* Button text */
    .stButton button {
        color: #1a1a1a !important;
    }
    
    /* Select box text */
    .stSelectbox, .stSelectbox label, .stSelectbox div {
        color: #1a1a1a !important;
    }
    
    /* Ensure expander headers are visible */
    .streamlit-expanderHeader {
        color: #1a1a1a !important;
    }
    
    /* Main content area pure white */
    .main {
        background: #ffffff !important;
        color: #0f172a;
        padding-top: 0.5rem;
    }
    
    /* Ensure all containers are white */
    .stApp, [data-testid="stAppViewContainer"] > div,
    .main > div, [class*="css"] {
        background: #ffffff !important;
    }

    /* MAIN CONTAINER - Use white content area with subtle border */
    .main > div {
        background: #ffffff !important;
        border-radius: 16px 16px 0 0;
        padding: 1rem;
        min-height: calc(100vh - 1rem);
        box-shadow: none;
        border: none;
    }

    /* HEADER CONTAINER - Keep white box containing logo and main title */
    .main-header {
        background: #ffffff;
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
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
        color: #374151; /* darker subtitle for white background */
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
        margin-top: 2rem;
        margin-bottom: 2rem;
        padding-top: 1rem;
        text-align: left;
        clear: both;
        position: relative;
        z-index: 100;
    }
    
    /* All markdown headings should have proper spacing */
    .main h1, .main h2, .main h3, .main h4 {
        margin-top: 2.5rem !important;
        margin-bottom: 1.5rem !important;
        padding-top: 1rem !important;
        clear: both !important;
        position: relative !important;
        z-index: 100 !important;
    }
    
    /* Subheadings within sections */
    .main h3 {
        font-size: 1.4rem;
        font-weight: 600;
        color: #374151;
    }
    
    .main h4 {
        font-size: 1.1rem;
        font-weight: 600;
        color: #4b5563;
    }
    
    /* DATA TABLES - Styling for pandas dataframes (Regional Progress table, etc.) */
    .stDataFrame {
        background: white !important;
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border: 1px solid #e5e7eb;
    }
    
    /* Force table backgrounds and text to be light theme */
    .stDataFrame, .stDataFrame table, .stDataFrame tbody, .stDataFrame tr, .stDataFrame td, .stDataFrame th {
        background-color: white !important;
        color: #1a1a1a !important;
    }
    
    /* Table headers */
    .stDataFrame thead th {
        background-color: #f8f9fa !important;
        color: #1a1a1a !important;
        font-weight: 600 !important;
    }
    
    /* Table cell text */
    .stDataFrame td {
        color: #1a1a1a !important;
    }
    
    /* Table borders */
    .stDataFrame table {
        border-color: #e5e7eb !important;
    }
    
    /* CHART CONTAINERS - White boxes around plotly charts */
    .chart-container {
        background: white;
        padding: 1rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    
    /* PLOTLY CHART STYLING - Transparent background to match white UI */
    .js-plotly-plot .plotly .main-svg {
        background: transparent !important;
    }
    
    .js-plotly-plot .plotly .bg {
        fill: transparent !important;
    }
    
    .js-plotly-plot .plotly text {
        fill: #1a1a1a !important;
        color: #1a1a1a !important;
    }
    
    .js-plotly-plot .plotly .xtick text,
    .js-plotly-plot .plotly .ytick text {
        fill: #1a1a1a !important;
        color: #1a1a1a !important;
    }
    
    .js-plotly-plot .plotly .legend text {
        fill: #1a1a1a !important;
        color: #1a1a1a !important;
    }
    
    .js-plotly-plot .plotly .title text {
        fill: #1a1a1a !important;
        color: #1a1a1a !important;
    }
    
    /* PLOTLY HOVER TOOLTIPS - Light background, dark text */
    .js-plotly-plot .hovertext path {
        fill: #ffffff !important;
        stroke: #d1d5db !important;
    }
    
    .js-plotly-plot .hovertext text {
        fill: #1a1a1a !important;
        color: #1a1a1a !important;
    }
    
    .js-plotly-plot .hoverlayer .hovertext {
        background: white !important;
    }
    
    .js-plotly-plot .hoverlayer rect {
        fill: white !important;
    }
    
    .js-plotly-plot .hoverlayer text {
        fill: #1a1a1a !important;
    }
    
    /* Chart container with no background */
    .js-plotly-plot {
        background: transparent !important;
        border: none !important;
        border-radius: 0px !important;
        padding: 0px !important;
    }
    
    .js-plotly-plot .plotly .bg rect {
        fill: transparent !important;
    }
    
    /* Ensure gridlines are visible */
    .js-plotly-plot .plotly .gridlayer line {
        stroke: #d1d5db !important;
    }
    
    /* Ensure axis lines are visible */
    .js-plotly-plot .plotly .zerolinelayer line {
        stroke: #9ca3af !important;
    }
    
    /* CHART CONTAINERS - Base styles (final overrides at end of CSS) */
    /* Keep Plotly internals transparent so card container shows through */
    [data-testid="stPlotlyChart"] .js-plotly-plot,
    [data-testid="stPlotlyChart"] .plot-container,
    [data-testid="stPlotlyChart"] .svg-container,
    [data-testid="stPlotlyChart"] svg,
    [data-testid="stPlotlyChart"] .user-select-none {
        background: transparent !important;
        background-color: transparent !important;
    }
    
    /* Remove pseudo-elements that might interfere */
    [data-testid="stPlotlyChart"]::before,
    [data-testid="stPlotlyChart"]::after {
        content: none !important;
        display: none !important;
    }
    
    /* SECTION DIVIDERS - White boxes with titles like "Overall Progress Gauge" */
    .section-divider {
        background: white;
        padding: 1rem;
        border-radius: 12px;
        margin: 2.5rem 0 1.5rem 0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        clear: both;
        position: relative;
        z-index: 50;
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
    
    /* Ensure Streamlit columns don't overflow */
    [data-testid="column"] {
        overflow: visible !important;
        position: relative !important;
    }
    
    /* Better spacing for content sections */
    .stMarkdown {
        margin-bottom: 1rem !important;
    }
    
    /* Ensure horizontal rules (separators) have proper spacing */
    hr {
        margin: 3rem 0 !important;
        border: none !important;
        border-top: 1px solid #e5e7eb !important;
        clear: both !important;
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

    /* ==========================================================
       FINAL OVERRIDES: CHART CARDS - Modern dashboard style
       Matches clean card design with header area, white bg, shadow
       ========================================================== */

    /* Each Plotly chart gets a clean card container */
    [data-testid="stPlotlyChart"] {
        background: #ffffff !important;
        border: 1px solid #d1d5db !important;
        border-radius: 8px !important;
        padding: 0 !important;
        margin: 16px 0 24px 0 !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04) !important;
        overflow: hidden !important;
        clear: both !important;
        position: relative !important;
    }

    /* Inner padding for chart content */
    [data-testid="stPlotlyChart"] > div {
        padding: 12px 16px 16px 16px !important;
    }

    /* Keep Plotly itself transparent so the card is the container */
    [data-testid="stPlotlyChart"] .js-plotly-plot,
    [data-testid="stPlotlyChart"] .plot-container,
    [data-testid="stPlotlyChart"] .svg-container,
    [data-testid="stPlotlyChart"] svg {
        background: transparent !important;
        background-color: transparent !important;
    }

    /* Modebar styled like reference image - top right icons */
    [data-testid="stPlotlyChart"] .modebar-container {
        position: absolute !important;
        top: 8px !important;
        right: 8px !important;
        width: auto !important;
        z-index: 10 !important;
        background: rgba(255, 255, 255, 0.9) !important;
        border-radius: 6px !important;
        padding: 4px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1) !important;
    }

    [data-testid="stPlotlyChart"] .modebar-group {
        padding: 0 4px !important;
    }

    [data-testid="stPlotlyChart"] .modebar-btn {
        color: #6b7280 !important;
    }

    [data-testid="stPlotlyChart"] .modebar-btn:hover {
        color: #3b82f6 !important;
    }

    /* Chart title styling inside Plotly */
    [data-testid="stPlotlyChart"] .g-gtitle {
        font-family: 'Inter', -apple-system, sans-serif !important;
    }

    /* Headings above charts - clean spacing */
    .main h2, .main h3, .main h4 {
        scroll-margin-top: 90px;
        clear: both !important;
        position: relative !important;
        z-index: 10 !important;
    }

    /* Section dividers get proper spacing before charts */
    .section-divider + [data-testid="stPlotlyChart"] {
        margin-top: 20px !important;
    }

    /* Headings after charts need breathing room */
    [data-testid="stPlotlyChart"] + .stMarkdown h2,
    [data-testid="stPlotlyChart"] + .stMarkdown h3,
    [data-testid="stPlotlyChart"] + .stMarkdown h4 {
        margin-top: 28px !important;
    }

    /* First chart in a column gets a small top margin */
    [data-testid="column"] > div > [data-testid="stPlotlyChart"]:first-child {
        margin-top: 8px !important;
    }
    
    /* Charts in columns should have consistent sizing */
    [data-testid="column"] [data-testid="stPlotlyChart"] {
        margin: 8px 0 16px 0 !important;
    }
    
    /* Side-by-side charts get equal height appearance */
    [data-testid="stHorizontalBlock"] [data-testid="stPlotlyChart"] {
        min-height: auto !important;
    }
    
    /* ==========================================================
       ABSOLUTE FINAL: FORCE LIGHT THEME ON EVERYTHING
       ========================================================== */
    
    /* Override any dark theme that browser might apply */
    * {
        color-scheme: light !important;
    }
    
    /* Ensure all text elements are dark */
    .stMarkdown, .stText, .stCaption, .stCode, p, span, div, label {
        color: #1a1a1a !important;
    }
    
    /* Metric labels and values */
    [data-testid="stMetricLabel"], [data-testid="stMetricValue"] {
        color: #1a1a1a !important;
    }
    
    /* Info boxes */
    .stAlert, .stInfo, .stWarning, .stSuccess, .stError {
        color: #1a1a1a !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Modern NSA header with official logo
    col_logo, col_text = st.columns([1, 4])
    
    with col_logo:
        try:
            st.image("nsa-logo.png", width=90)
        except Exception:
            # If the image file is missing (e.g., local dev), don't stop the app
            pass
    
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
        st.error("❌ Cannot connect to backend API. Make sure backend is running on http://localhost:5001")
        return
    
    # Add refresh button in sidebar
    with st.sidebar:
        st.markdown("---")
        st.markdown("### ⚡ Data Controls")
        if st.button("🔄 Refresh Data", use_container_width=True, help="Clear cache and reload all data"):
            st.cache_data.clear()
            st.rerun()
        st.caption(f"Data cached for {CACHE_TTL} seconds")
    
    # Pre-load all data with a spinner (only on first load)
    with st.spinner("Loading data..."):
        all_data = get_all_data()
    
    if not all_data["submissions"]:
        st.warning("⚠️ No data available. Please check KoBoToolbox connection.")
    
    # Professional tab layout with Reports
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 National Overview", 
        "🗺️ Regional Analysis", 
        "📈 Track Progress",
        "📋 Reports"
    ])
    
    with tab1:
        show_national_overview()
    
    with tab2:
        show_regional_breakdown()
    
    with tab3:
        show_daily_progress()
    
    with tab4:
        show_reports_page()


if __name__ == "__main__":
    main()