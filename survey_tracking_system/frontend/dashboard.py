"""
Namibia GBV ICT Readiness Survey Tracking Dashboard

Streamlit dashboard for visualizing survey completion progress
and GBV ICT Readiness indicators across Namibia's 14 regions.
"""

import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from config import get_api_base_url

# Page configuration
st.set_page_config(
    page_title="GBV ICT Readiness Dashboard - Namibia",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS - Light Theme with White Background and Black Text
st.markdown("""
<style>
    /* Force light theme */
    .stApp {
        background-color: #ffffff;
        color: #1a1a1a;
    }
    
    /* Main content area */
    .main .block-container {
        background-color: #ffffff;
        color: #1a1a1a;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #f8f9fa;
        color: #1a1a1a;
    }
    
    [data-testid="stSidebar"] * {
        color: #1a1a1a !important;
    }
    
    /* Header styling */
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1a1a1a;
        text-align: center;
        padding: 1rem 0;
        background-color: #ffffff;
    }
    
    /* All text should be black */
    h1, h2, h3, h4, h5, h6, p, span, div, label {
        color: #1a1a1a !important;
    }
    
    /* Metric cards */
    [data-testid="stMetricValue"] {
        color: #1a1a1a !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: #333333 !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #f8f9fa;
    }
    
    .stTabs [data-baseweb="tab"] {
        color: #1a1a1a !important;
    }
    
    /* Data frames / tables */
    .stDataFrame {
        background-color: #ffffff;
    }
    
    /* Cards and containers */
    .metric-card {
        background: linear-gradient(135deg, #0066cc 0%, #004499 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
    }
    
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    
    .region-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #0066cc;
        margin: 0.5rem 0;
        color: #1a1a1a;
    }
    
    /* Badges */
    .success-badge {
        background: #28a745;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
    }
    
    .warning-badge {
        background: #ffc107;
        color: #1a1a1a;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
    }
    
    .danger-badge {
        background: #dc3545;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
    }
    
    /* Input elements */
    .stSelectbox label, .stSlider label {
        color: #1a1a1a !important;
    }
    
    /* Progress bars */
    .stProgress > div > div {
        background-color: #0066cc;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #0066cc;
        color: white;
        border: none;
    }
    
    .stButton > button:hover {
        background-color: #004499;
        color: white;
    }
    
    /* Info, warning, error boxes */
    .stAlert {
        background-color: #f8f9fa;
        color: #1a1a1a;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        color: #1a1a1a !important;
        background-color: #f8f9fa;
    }
    
    /* Caption text */
    .stCaption {
        color: #666666 !important;
    }
</style>
""", unsafe_allow_html=True)

API_BASE = get_api_base_url()


def fetch_json(endpoint: str, default=None):
    """Fetch JSON from API endpoint."""
    try:
        resp = requests.get(f"{API_BASE}{endpoint}", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return default


def post_json(endpoint: str, data: dict = None):
    """POST to API endpoint."""
    try:
        resp = requests.post(f"{API_BASE}{endpoint}", json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return None


def get_readiness_color(score):
    """Get color based on readiness score."""
    if score is None:
        return "#gray"
    if score >= 80:
        return "#28a745"
    if score >= 60:
        return "#17a2b8"
    if score >= 40:
        return "#ffc107"
    return "#dc3545"


def get_readiness_level(score):
    """Get readiness level label."""
    if score is None:
        return "Not Assessed"
    if score >= 80:
        return "High"
    if score >= 60:
        return "Moderate"
    if score >= 40:
        return "Low"
    return "Critical"


def main():
    # Header
    st.markdown('<h1 class="main-header">🇳🇦 Namibia GBV ICT Readiness Dashboard</h1>', unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.title("Navigation")
    
    # Fetch campaigns
    campaigns = fetch_json("/api/campaigns", [])
    
    if not campaigns:
        st.warning("No campaigns found. Please create a campaign first.")
        st.info("Use the API to create a campaign: POST /api/campaigns")
        return
    
    # Campaign selector
    campaign_options = {c["name"]: c["id"] for c in campaigns}
    selected_campaign_name = st.sidebar.selectbox(
        "Select Campaign",
        options=list(campaign_options.keys()),
    )
    campaign_id = campaign_options[selected_campaign_name]
    
    # Get campaign details
    campaign = next((c for c in campaigns if c["id"] == campaign_id), None)
    
    # Sidebar info
    st.sidebar.markdown("---")
    st.sidebar.subheader("Campaign Info")
    if campaign:
        st.sidebar.write(f"**Start:** {campaign['start_date']}")
        st.sidebar.write(f"**End:** {campaign['end_date']}")
        if campaign.get('target_institutions'):
            st.sidebar.write(f"**Target:** {campaign['target_institutions']} institutions")
        if campaign.get('kobo_asset_uid'):
            st.sidebar.write(f"**KoBoToolbox:** Connected")
            st.sidebar.caption(f"UID: {campaign['kobo_asset_uid'][:20]}...")
    
    # KoBoToolbox Sync Button
    st.sidebar.markdown("---")
    st.sidebar.subheader("Data Sync")
    if campaign and campaign.get('kobo_asset_uid'):
        if st.sidebar.button("🔄 Sync from KoBoToolbox", type="primary"):
            with st.spinner("Syncing data from KoBoToolbox..."):
                result = post_json(f"/api/campaigns/{campaign_id}/sync-kobo")
                if result:
                    st.sidebar.success(f"✅ Synced {result.get('new_records', 0)} new, {result.get('updated_records', 0)} updated")
                    if result.get('errors', 0) > 0:
                        st.sidebar.warning(f"⚠️ {result['errors']} errors occurred")
                    st.rerun()
    else:
        st.sidebar.info("Configure KoBoToolbox asset UID to enable sync")
    
    # Main content tabs
    tabs = st.tabs([
        "📈 Overview",
        "🗺️ Regional Analysis",
        "📊 GBV Readiness",
        "📅 Daily Progress",
        "📋 Detailed Report"
    ])
    
    # Tab 1: Overview
    with tabs[0]:
        st.subheader("National Summary")
        
        summary = fetch_json(f"/api/campaigns/{campaign_id}/national-summary", {})
        
        if summary:
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric(
                    "Target Institutions",
                    summary.get('target_institutions', 0) or summary.get('total_surveys', 0),
                )
            
            with col2:
                st.metric(
                    "Completed",
                    summary.get('completed_surveys', 0),
                    delta=None,
                )
            
            with col3:
                st.metric(
                    "In Progress",
                    summary.get('in_progress_surveys', 0),
                )
            
            with col4:
                st.metric(
                    "Pending",
                    summary.get('pending_surveys', 0),
                )
            
            with col5:
                completion_rate = summary.get('completion_rate', 0)
                st.metric(
                    "Completion Rate",
                    f"{completion_rate:.1f}%",
                )
            
            # Progress bar
            st.progress(min(completion_rate / 100, 1.0))
            
            # Readiness score if available
            avg_score = summary.get('avg_readiness_score')
            if avg_score:
                st.markdown("---")
                st.subheader("Average GBV ICT Readiness Score")
                
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.markdown(f"""
                    <div style="background: {get_readiness_color(avg_score)}; 
                                padding: 2rem; 
                                border-radius: 12px; 
                                text-align: center;
                                color: white;">
                        <div style="font-size: 3rem; font-weight: bold;">{avg_score:.1f}</div>
                        <div style="font-size: 1.2rem;">out of 100</div>
                        <div style="margin-top: 0.5rem; font-size: 1rem;">{get_readiness_level(avg_score)} Readiness</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown("**Score Interpretation:**")
                    st.markdown("- 🟢 **80-100**: High Readiness")
                    st.markdown("- 🔵 **60-79**: Moderate")
                    st.markdown("- 🟡 **40-59**: Low")
                    st.markdown("- 🔴 **0-39**: Critical")
    
    # Tab 2: Regional Analysis
    with tabs[1]:
        st.subheader("Regional Completion Status")
        
        regional = fetch_json(f"/api/campaigns/{campaign_id}/regional-summary", [])
        
        if regional:
            df = pd.DataFrame(regional)
            
            # Sort by completion rate
            df_sorted = df.sort_values('completion_rate', ascending=False)
            
            # Bar chart
            st.bar_chart(
                df_sorted.set_index('region_name')['completion_rate'],
                use_container_width=True,
            )
            
            # Table
            st.dataframe(
                df_sorted[['region_name', 'region_code', 'total_surveys', 'completed_surveys', 'completion_rate']].rename(columns={
                    'region_name': 'Region',
                    'region_code': 'Code',
                    'total_surveys': 'Total Surveys',
                    'completed_surveys': 'Completed',
                    'completion_rate': 'Completion %',
                }),
                use_container_width=True,
                hide_index=True,
            )
    
    # Tab 3: GBV Readiness
    with tabs[2]:
        st.subheader("GBV ICT Readiness Analysis")
        
        readiness = fetch_json(f"/api/campaigns/{campaign_id}/readiness-summary")
        
        if readiness and 'message' not in readiness:
            st.write(f"**Institutions Assessed:** {readiness.get('total_institutions_assessed', 0)}")
            
            # Readiness scores
            scores = readiness.get('readiness_scores', {})
            if scores:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Average Score", f"{scores.get('average', 0):.1f}")
                with col2:
                    st.metric("Minimum Score", f"{scores.get('minimum', 0):.1f}")
                with col3:
                    st.metric("Maximum Score", f"{scores.get('maximum', 0):.1f}")
            
            st.markdown("---")
            
            # Indicator breakdowns
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Policy & Governance")
                pg = readiness.get('policy_governance', {})
                st.progress(pg.get('has_gbv_policy_pct', 0) / 100)
                st.caption(f"Has GBV Policy: {pg.get('has_gbv_policy_pct', 0):.1f}%")
                st.progress(pg.get('has_action_plan_pct', 0) / 100)
                st.caption(f"Has Action Plan: {pg.get('has_action_plan_pct', 0):.1f}%")
                st.progress(pg.get('has_focal_point_pct', 0) / 100)
                st.caption(f"Has Focal Point: {pg.get('has_focal_point_pct', 0):.1f}%")
                
                st.markdown("#### Human Resources")
                hr = readiness.get('human_resources', {})
                st.progress(hr.get('has_trained_staff_pct', 0) / 100)
                st.caption(f"Has Trained Staff: {hr.get('has_trained_staff_pct', 0):.1f}%")
                st.write(f"Avg Trained Staff: {hr.get('avg_trained_staff_per_institution', 0):.1f}")
                st.progress(hr.get('has_dedicated_gbv_unit_pct', 0) / 100)
                st.caption(f"Has Dedicated GBV Unit: {hr.get('has_dedicated_gbv_unit_pct', 0):.1f}%")
            
            with col2:
                st.markdown("#### ICT Infrastructure")
                ict = readiness.get('ict_infrastructure', {})
                st.progress(ict.get('has_computers_pct', 0) / 100)
                st.caption(f"Has Computers: {ict.get('has_computers_pct', 0):.1f}%")
                st.write(f"Avg Functional Computers: {ict.get('avg_functional_computers', 0):.1f}")
                st.progress(ict.get('has_case_management_system_pct', 0) / 100)
                st.caption(f"Has Case Management System: {ict.get('has_case_management_system_pct', 0):.1f}%")
                
                st.markdown("#### Service Delivery")
                sd = readiness.get('service_delivery', {})
                st.progress(sd.get('has_referral_pathway_pct', 0) / 100)
                st.caption(f"Has Referral Pathway: {sd.get('has_referral_pathway_pct', 0):.1f}%")
                st.progress(sd.get('has_survivor_support_pct', 0) / 100)
                st.caption(f"Has Survivor Support: {sd.get('has_survivor_support_pct', 0):.1f}%")
                st.progress(sd.get('has_helpline_pct', 0) / 100)
                st.caption(f"Has Helpline: {sd.get('has_helpline_pct', 0):.1f}%")
        
        else:
            st.info("No readiness data available yet. Sync data from KoBoToolbox to populate.")
        
        # Regional readiness comparison
        st.markdown("---")
        st.subheader("Regional Readiness Comparison")
        
        regional_readiness = fetch_json(f"/api/campaigns/{campaign_id}/regional-readiness", [])
        
        if regional_readiness:
            df_rr = pd.DataFrame(regional_readiness)
            
            # Filter to regions with data
            df_with_data = df_rr[df_rr['institutions_assessed'] > 0]
            
            if not df_with_data.empty:
                # Chart
                st.bar_chart(
                    df_with_data.set_index('region_name')['avg_readiness_score'].dropna(),
                    use_container_width=True,
                )
                
                # Table
                st.dataframe(
                    df_with_data[['region_name', 'institutions_assessed', 'avg_readiness_score', 'policy_adoption_pct', 'cms_adoption_pct', 'training_pct']].rename(columns={
                        'region_name': 'Region',
                        'institutions_assessed': 'Assessed',
                        'avg_readiness_score': 'Readiness Score',
                        'policy_adoption_pct': 'Policy %',
                        'cms_adoption_pct': 'CMS %',
                        'training_pct': 'Training %',
                    }),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No regional readiness data available yet.")
    
    # Tab 4: Daily Progress
    with tabs[3]:
        st.subheader("Daily Completion Trend")
        
        days = st.slider("Days to show", 7, 90, 30)
        daily = fetch_json(f"/api/campaigns/{campaign_id}/daily-progress?days={days}", [])
        
        if daily:
            df_daily = pd.DataFrame(daily)
            df_daily['date'] = pd.to_datetime(df_daily['date'])
            df_daily = df_daily.set_index('date')
            
            # Line chart - cumulative
            st.line_chart(df_daily['cumulative_completed'], use_container_width=True)
            
            # Daily completions bar
            st.subheader("Daily Completions")
            st.bar_chart(df_daily['daily_completed'], use_container_width=True)
        else:
            st.info("No daily progress data available yet.")
    
    # Tab 5: Detailed Report
    with tabs[4]:
        st.subheader("Comprehensive Progress Report")
        
        report = fetch_json(f"/api/campaigns/{campaign_id}/progress-report", {})
        
        if report:
            # Campaign info
            st.markdown(f"### {report.get('campaign_name', 'Campaign')}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Survey Status")
                st.write(f"- **Target Institutions:** {report.get('target_institutions', 'N/A')}")
                st.write(f"- **Total Surveys:** {report.get('total_surveys', 0)}")
                st.write(f"- **Completed:** {report.get('completed', 0)}")
                st.write(f"- **In Progress:** {report.get('in_progress', 0)}")
                st.write(f"- **Pending:** {report.get('pending', 0)}")
                st.write(f"- **Completion Rate:** {report.get('completion_rate', 0):.1f}%")
            
            with col2:
                indicators = report.get('readiness_indicators')
                if indicators:
                    st.markdown("#### GBV ICT Readiness Indicators")
                    if indicators.get('avg_readiness_score'):
                        st.write(f"- **Average Readiness Score:** {indicators['avg_readiness_score']:.1f}")
                    if indicators.get('policy_adoption_rate'):
                        st.write(f"- **Policy Adoption Rate:** {indicators['policy_adoption_rate']:.1f}%")
                    if indicators.get('cms_adoption_rate'):
                        st.write(f"- **CMS Adoption Rate:** {indicators['cms_adoption_rate']:.1f}%")
                    if indicators.get('staff_training_rate'):
                        st.write(f"- **Staff Training Rate:** {indicators['staff_training_rate']:.1f}%")
                    if indicators.get('computer_access_rate'):
                        st.write(f"- **Computer Access Rate:** {indicators['computer_access_rate']:.1f}%")
                else:
                    st.info("No readiness indicators available.")
            
            # Download report
            st.markdown("---")
            st.download_button(
                label="📥 Download Report (JSON)",
                data=str(report),
                file_name=f"gbv_readiness_report_{campaign_id}_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
            )
    
    # Footer
    st.markdown("---")
    st.caption("GBV ICT Readiness Survey Tracking System | Namibia 🇳🇦")


if __name__ == "__main__":
    main()
