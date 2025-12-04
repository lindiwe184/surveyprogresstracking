#!/bin/bash

# GBV Dashboard Deployment Script for Linux Server
# This script automates the deployment process

set -e

echo "🚀 GBV Readiness Survey Dashboard Deployment Script"
echo "=================================================="

# Configuration
APP_USER="gbvapp"
APP_DIR="/home/$APP_USER/surveyprogresstracking"
DOMAIN=""
EMAIL=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root for security reasons"
   exit 1
fi

# Get domain and email from user
read -p "Enter your domain name (e.g., dashboard.nsa.gov.na): " DOMAIN
read -p "Enter your email for SSL certificate: " EMAIL

if [[ -z "$DOMAIN" || -z "$EMAIL" ]]; then
    print_error "Domain and email are required"
    exit 1
fi

print_status "Deploying GBV Dashboard for domain: $DOMAIN"

# Update system
print_status "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required packages
print_status "Installing required packages..."
sudo apt install -y python3 python3-pip python3-venv nginx supervisor git curl ufw

# Create application user if it doesn't exist
if ! id "$APP_USER" &>/dev/null; then
    print_status "Creating application user: $APP_USER"
    sudo useradd -m -s /bin/bash $APP_USER
fi

# Clone or update repository
print_status "Setting up application code..."
if [[ -d "$APP_DIR" ]]; then
    print_warning "Application directory exists. Updating..."
    cd $APP_DIR
    git pull origin main
else
    print_status "Cloning repository..."
    sudo -u $APP_USER git clone https://github.com/lindiwe184/surveyprogresstracking.git $APP_DIR
fi

cd $APP_DIR

# Create virtual environment
print_status "Setting up Python virtual environment..."
sudo -u $APP_USER python3 -m venv venv
sudo -u $APP_USER bash -c "source venv/bin/activate && pip install --upgrade pip"

# Install dependencies
print_status "Installing Python dependencies..."
sudo -u $APP_USER bash -c "source venv/bin/activate && pip install -r backend/requirements.txt"
sudo -u $APP_USER bash -c "source venv/bin/activate && pip install -r frontend/requirements.txt"
sudo -u $APP_USER bash -c "source venv/bin/activate && pip install gunicorn"

# Set up environment file
print_status "Setting up environment configuration..."
if [[ ! -f "backend/.env" ]]; then
    sudo -u $APP_USER cp backend/env.template backend/.env
    print_warning "Please edit backend/.env with your KoboToolbox credentials:"
    print_warning "sudo -u $APP_USER nano $APP_DIR/backend/.env"
    read -p "Press enter when you've configured the .env file..."
fi

# Create supervisor configuration for backend
print_status "Configuring backend service..."
sudo tee /etc/supervisor/conf.d/gbv-backend.conf > /dev/null <<EOF
[program:gbv-backend]
command=$APP_DIR/venv/bin/gunicorn -w 4 -b 127.0.0.1:5002 --timeout 120 kobo_app:app
directory=$APP_DIR/backend
user=$APP_USER
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/gbv-backend.log
environment=PATH="$APP_DIR/venv/bin"
EOF

# Create supervisor configuration for frontend
print_status "Configuring frontend service..."
sudo tee /etc/supervisor/conf.d/gbv-frontend.conf > /dev/null <<EOF
[program:gbv-frontend]
command=$APP_DIR/venv/bin/streamlit run kobo_dashboard.py --server.port 8501 --server.address 127.0.0.1 --server.headless true
directory=$APP_DIR/frontend
user=$APP_USER
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/gbv-frontend.log
environment=PATH="$APP_DIR/venv/bin"
EOF

# Create Nginx configuration
print_status "Configuring Nginx..."
sudo tee /etc/nginx/sites-available/gbv-dashboard > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        proxy_read_timeout 86400;
    }

    location /api {
        proxy_pass http://127.0.0.1:5002;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable Nginx site
sudo ln -sf /etc/nginx/sites-available/gbv-dashboard /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
print_status "Testing Nginx configuration..."
sudo nginx -t

# Configure firewall
print_status "Configuring firewall..."
sudo ufw --force enable
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'

# Start services
print_status "Starting services..."
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start gbv-backend
sudo supervisorctl start gbv-frontend
sudo systemctl restart nginx

# Install SSL certificate
print_status "Installing SSL certificate..."
sudo snap install core; sudo snap refresh core
sudo snap install --classic certbot
sudo ln -sf /snap/bin/certbot /usr/bin/certbot

# Get SSL certificate
sudo certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email $EMAIL

# Set up automatic renewal
echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -

# Create backup script
print_status "Setting up backup script..."
sudo tee /usr/local/bin/gbv-backup.sh > /dev/null <<EOF
#!/bin/bash
BACKUP_DIR="/backup/gbv-dashboard"
DATE=\$(date +%Y%m%d_%H%M%S)

mkdir -p \$BACKUP_DIR
tar -czf \$BACKUP_DIR/gbv-app-\$DATE.tar.gz -C /home/$APP_USER surveyprogresstracking

# Keep only last 7 days of backups
find \$BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
EOF

sudo chmod +x /usr/local/bin/gbv-backup.sh

# Set up daily backup
echo "0 2 * * * /usr/local/bin/gbv-backup.sh" | sudo crontab -

# Final status check
print_status "Checking service status..."
sleep 5

if curl -s http://localhost:5002/api/health > /dev/null; then
    print_status "✅ Backend service is running"
else
    print_error "❌ Backend service failed to start"
fi

if curl -s http://localhost:8501/_stcore/health > /dev/null; then
    print_status "✅ Frontend service is running"
else
    print_error "❌ Frontend service failed to start"
fi

print_status "🎉 Deployment completed!"
print_status "Your GBV Dashboard should be accessible at: https://$DOMAIN"
print_status ""
print_status "Useful commands:"
print_status "  - Check services: sudo supervisorctl status"
print_status "  - View logs: sudo tail -f /var/log/gbv-backend.log"
print_status "  - Restart services: sudo supervisorctl restart gbv-backend gbv-frontend"
print_status ""
print_warning "Don't forget to:"
print_warning "1. Configure your KoboToolbox credentials in $APP_DIR/backend/.env"
print_warning "2. Set up DNS records for your domain"
print_warning "3. Test the application thoroughly"