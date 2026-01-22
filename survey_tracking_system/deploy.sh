#!/bin/bash

# GBV Survey Dashboard - Automated Deployment Script
# This script sets up the complete application environment on Ubuntu

set -e  # Exit on any error

echo "🚀 Starting GBV Survey Dashboard Deployment..."
echo "================================================"

# Update system packages
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install essential packages
echo "🔧 Installing essential packages..."
sudo apt install -y curl wget gnupg2 software-properties-common apt-transport-https ca-certificates lsb-release

# Install Docker
echo "🐳 Installing Docker..."
if ! command -v docker &> /dev/null; then
    # Remove old Docker versions
    sudo apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
    
    # Add Docker GPG key
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # Add Docker repository
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Install Docker
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io
    
    # Add user to docker group
    sudo usermod -aG docker $USER
    
    echo "✅ Docker installed successfully"
else
    echo "✅ Docker already installed"
fi

# Install Docker Compose
echo "🔨 Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose installed successfully"
else
    echo "✅ Docker Compose already installed"
fi

# Install Python and pip
echo "🐍 Installing Python..."
sudo apt install -y python3 python3-pip python3-venv

# Install Nginx
echo "🌐 Installing Nginx..."
sudo apt install -y nginx

# Install Supervisor for process management
echo "👮 Installing Supervisor..."
sudo apt install -y supervisor

# Create application directories
echo "📁 Creating application directories..."
sudo mkdir -p /var/log/gbv-dashboard
sudo mkdir -p /etc/gbv-dashboard
sudo chown -R $USER:$USER /var/log/gbv-dashboard

# Copy environment template
echo "📋 Setting up environment configuration..."
if [ -f "backend/env.template" ]; then
    cp backend/env.template backend/.env
    echo "✅ Environment template copied to backend/.env"
    echo "⚠️  Remember to update backend/.env with your actual KoboToolbox credentials"
fi

# Build and start Docker containers
echo "🏗️  Building Docker containers..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

# Configure Nginx reverse proxy
echo "🔧 Configuring Nginx..."
sudo cp nginx.conf /etc/nginx/sites-available/gbv-dashboard
sudo ln -sf /etc/nginx/sites-available/gbv-dashboard /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx

# Configure firewall
echo "🔥 Configuring firewall..."
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# Setup log rotation
echo "📊 Setting up log rotation..."
sudo tee /etc/logrotate.d/gbv-dashboard > /dev/null <<EOF
/var/log/gbv-dashboard/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
}
EOF

# Create systemd service for auto-restart
echo "⚙️  Creating systemd service..."
sudo tee /etc/systemd/system/gbv-dashboard.service > /dev/null <<EOF
[Unit]
Description=GBV Survey Dashboard
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$(pwd)
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable gbv-dashboard.service

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 30

# Check service status
echo "🔍 Checking service status..."
docker-compose ps

# Display completion message
echo ""
echo "🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!"
echo "======================================"
echo ""
echo "📍 Your GBV Survey Dashboard is now running!"
echo ""
echo "🌐 Access URLs:"
echo "   • Main Dashboard: http://$(hostname -I | awk '{print $1}')"
echo "   • Backend API: http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "📋 Next Steps:"
echo "   1. Update backend/.env with your KoboToolbox credentials"
echo "   2. Restart services: docker-compose restart"
echo "   3. Monitor logs: docker-compose logs -f"
echo ""
echo "📊 Service Management:"
echo "   • Start: sudo systemctl start gbv-dashboard"
echo "   • Stop: sudo systemctl stop gbv-dashboard"
echo "   • Status: sudo systemctl status gbv-dashboard"
echo "   • Logs: docker-compose logs -f"
echo ""
echo "🔧 Troubleshooting:"
echo "   • Check service status: docker-compose ps"
echo "   • View logs: docker-compose logs"
echo "   • Restart services: docker-compose restart"
echo ""
echo "✅ Deployment completed at $(date)"