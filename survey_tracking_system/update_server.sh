#!/bin/bash
# Update GBV Survey Tracking System on Ubuntu Server
# This script updates the application with the latest changes

set -e  # Exit on error

echo "🔄 Starting GBV Survey System Update..."
echo "========================================="

# Get the actual user (not root if using sudo)
ACTUAL_USER=${SUDO_USER:-$USER}
ACTUAL_HOME=$(eval echo ~$ACTUAL_USER)

# 1. Get to project root (we should already be here)
PROJECT_DIR=$(pwd)
echo "📁 Current directory: $PROJECT_DIR"

# Verify we're in the right place
if [ ! -f "survey_tracking_system/backend/kobo_app.py" ]; then
    echo "❌ Error: Not in project root directory!"
    echo "   Please run this script from: ~/surveyprogresstracking"
    echo "   Current location: $PROJECT_DIR"
    exit 1
fi

# 2. Stop running services
echo "⏸️  Stopping services..."
sudo systemctl stop gbv-backend gbv-frontend 2>/dev/null || {
    echo "⚠️  Services not found in systemd, attempting to kill processes..."
    pkill -f kobo_app.py || true
    pkill -f streamlit || true
}

# 3. Backup current .env file
echo "💾 Backing up environment files..."
cp survey_tracking_system/backend/.env survey_tracking_system/backend/.env.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true

# 4. Pull latest changes
echo "📥 Pulling latest changes from GitHub..."
git stash save "Auto-stash before update $(date +%Y%m%d_%H%M%S)"
git pull origin main

# 5. Create/update virtual environment and install dependencies
echo "📦 Setting up Python virtual environment..."
cd "$PROJECT_DIR"

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    echo "   Creating new virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

echo "📦 Updating Python dependencies..."
cd survey_tracking_system/backend
pip install -r requirements.txt --upgrade

cd ../frontend
pip install -r requirements.txt --upgrade

# Deactivate for now (services will use venv path)
deactivate
cd "$PROJECT_DIR"

# 6. Update database configuration
cd "$PROJECT_DIR/survey_tracking_system/backend"
echo ""
echo "🔧 Updating database configuration..."

# Check if .env exists, if not copy from template
if [ ! -f .env ]; then
    echo "⚠️  No .env file found, copying from template..."
    cp env.template .env
fi

# Update DATABASE_URL to use new driver (psycopg instead of psycopg2)
echo "📝 Updating database URL to use postgresql+psycopg driver..."
sed -i 's/postgresql+psycopg2/postgresql+psycopg/g' .env

# 7. Grant PostgreSQL permissions
echo "🔐 Ensuring PostgreSQL permissions..."
sudo -u postgres psql -d survey_tracking << EOF
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO survey_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO survey_user;
GRANT USAGE ON SCHEMA public TO survey_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO survey_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO survey_user;
EOF

# 8. Update systemd service files to use kobo_app.py
echo "🔧 Updating systemd service files..."

# Backend service
sudo tee /etc/systemd/system/gbv-backend.service > /dev/null << BACKEND_SERVICE
[Unit]
Description=GBV Backend API
After=network.target postgresql.service

[Service]
Type=simple
User=$ACTUAL_USER
WorkingDirectory=$PROJECT_DIR/survey_tracking_system/backend
Environment="PATH=$PROJECT_DIR/venv/bin:/usr/bin:/usr/local/bin"
ExecStart=$PROJECT_DIR/venv/bin/python kobo_app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
BACKEND_SERVICE

# Frontend service
sudo tee /etc/systemd/system/gbv-frontend.service > /dev/null << FRONTEND_SERVICE
[Unit]
Description=GBV Frontend Dashboard
After=network.target gbv-backend.service

[Service]
Type=simple
User=$ACTUAL_USER
WorkingDirectory=$PROJECT_DIR/survey_tracking_system/frontend
Environment="PATH=$PROJECT_DIR/venv/bin:/usr/bin:/usr/local/bin"
ExecStart=$PROJECT_DIR/venv/bin/streamlit run kobo_dashboard.py --server.port 8501 --server.address 0.0.0.0
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
FRONTEND_SERVICE

# 9. Reload systemd and restart services
echo "🔄 Reloading systemd and restarting services..."
sudo systemctl daemon-reload
sudo systemctl enable gbv-backend gbv-frontend
sudo systemctl restart gbv-backend gbv-frontend

# 10. Wait and check status
echo "⏳ Waiting for services to start..."
sleep 5

echo ""
echo "✅ Update complete! Checking service status..."
echo "=============================================="
sudo systemctl status gbv-backend --no-pager -l
echo ""
sudo systemctl status gbv-frontend --no-pager -l

echo ""
echo "📊 Service URLs:"
echo "   - Frontend: http://$(hostname -I | awk '{print $1}'):8501"
echo "   - Backend:  http://$(hostname -I | awk '{print $1}'):5001/api/health"
echo ""
echo "📝 Logs:"
echo "   Backend:  sudo journalctl -u gbv-backend -f"
echo "   Frontend: sudo journalctl -u gbv-frontend -f"
