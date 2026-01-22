import os
from datetime import datetime
from typing import Dict, List, Any

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager

# Load environment variables from .env file
load_dotenv()

# Import authentication components
from models import db, User, init_db
from auth import auth_bp, admin_required


def get_kobo_config():
    """Get KoboToolbox configuration from environment variables."""
    base_url = os.getenv("KOBO_BASE_URL", "https://kf.kobotoolbox.org").rstrip("/")
    token = os.getenv("KOBO_TOKEN")
    asset_id = os.getenv("KOBO_ASSET_ID")
    
    if not token or not asset_id:
        raise RuntimeError("KOBO_TOKEN and KOBO_ASSET_ID must be set in the environment")
    
    return {
        "base_url": base_url,
        "token": token,
        "asset_id": asset_id,
    }


def fetch_kobo_submissions() -> List[Dict[str, Any]]:
    """Fetch submissions directly from KoboToolbox."""
    try:
        cfg = get_kobo_config()
        url = f"{cfg['base_url']}/api/v2/assets/{cfg['asset_id']}/data/"
        headers = {
            "Authorization": f"Token {cfg['token']}",
            "Accept": "application/json",
        }
        
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])
    except Exception as e:
        print(f"Error fetching KoboToolbox data: {e}")
        return []





def analyze_submissions(submissions: List[Dict]) -> Dict[str, Any]:
    """Analyze submissions to extract summary statistics."""
    if not submissions:
        return {
            "total_submissions": 0,
            "by_region": {},
            "by_date": {},
            "form_fields": []
        }
    
    # Get form fields from first submission
    form_fields = list(submissions[0].keys()) if submissions else []
    
    # Analyze by regions (if region field exists)
    by_region = {}
    by_date = {}
    
    for submission in submissions:
        # Extract date (submission time) in Namibian timezone
        submit_time = submission.get("_submission_time", "")
        if submit_time:
            try:
                # Convert to Namibian timezone (CAT - UTC+2)
                import pytz
                date_obj = datetime.fromisoformat(submit_time.replace('Z', '+00:00'))
                namibian_tz = pytz.timezone('Africa/Windhoek')
                namibian_date = date_obj.astimezone(namibian_tz)
                date_str = namibian_date.strftime('%Y-%m-%d')
                by_date[date_str] = by_date.get(date_str, 0) + 1
            except:
                # Fallback without timezone conversion
                try:
                    date_obj = datetime.fromisoformat(submit_time.replace('Z', '+00:00'))
                    date_str = date_obj.strftime('%Y-%m-%d')
                    by_date[date_str] = by_date.get(date_str, 0) + 1
                except:
                    pass
        
        # Extract region if field exists
        region_field = None
        for field in form_fields:
            if 'region' in field.lower():
                region_field = field
                break
        
        if region_field and region_field in submission:
            region = submission[region_field]
            if region:
                by_region[region] = by_region.get(region, 0) + 1
    
    return {
        "total_submissions": len(submissions),
        "by_region": by_region,
        "by_date": by_date,
        "form_fields": form_fields,
        "recent_submissions": submissions[:10]  # Last 10 submissions
    }


def create_app():
    app = Flask(__name__)
    CORS(app)
    
    # Configure app for authentication
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql+psycopg://survey_user:Timer%402001@localhost:5432/survey_tracking')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize JWT extension
    jwt = JWTManager(app)
    
    # Initialize database
    init_db(app)
    
    # Register authentication blueprint
    app.register_blueprint(auth_bp)
    
    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "data_source": "kobotoolbox_only"})
    
    @app.get("/api/kobo/submissions")
    def get_submissions():
        """Get all submissions from KoboToolbox."""
        submissions = fetch_kobo_submissions()
        return jsonify(submissions)
    

    
    @app.get("/api/kobo/summary")
    def get_summary():
        """Get analyzed summary of submissions."""
        submissions = fetch_kobo_submissions()
        analysis = analyze_submissions(submissions)
        return jsonify(analysis)
    
    @app.get("/api/kobo/refresh")
    def refresh_data():
        """Force refresh data from KoboToolbox."""
        submissions = fetch_kobo_submissions()
        analysis = analyze_submissions(submissions)
        return jsonify({
            "message": f"Refreshed {len(submissions)} submissions",
            "analysis": analysis
        })
    
    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host="0.0.0.0", port=int(os.getenv("PORT", "5001")))