# GBV Survey Progress Tracking System - Deployment Guide

## Overview
This guide provides step-by-step instructions for deploying the GBV Survey Dashboard on a Linux server (Ubuntu/Debian).

## Prerequisites
- Ubuntu 20.04+ or Debian 11+ server
- Root or sudo access
- Minimum 2GB RAM, 10GB disk space
- Internet connectivity

## Quick Deployment (Automated)

### 1. Clone Repository
```bash
git clone https://github.com/lindiwe184/surveyprogresstracking.git
cd surveyprogresstracking
```

### 2. Run Automated Deployment
```bash
chmod +x deploy.sh
sudo ./deploy.sh
```

The script will automatically:
- Install Docker and Docker Compose
- Install Python, Nginx, and dependencies
- Build and start all services
- Configure reverse proxy and firewall
- Set up monitoring and log rotation

### 3. Configure Environment
```bash
# Edit environment variables
nano backend/.env

# Add your KoboToolbox credentials:
KOBO_API_URL=https://your-kobo-server.com/api/v2/
KOBO_TOKEN=your_api_token_here
DATABASE_URL=postgresql+psycopg2://survey_user:survey_password@localhost:5432/survey_tracking
```

### 4. Restart Services
```bash
docker-compose restart
```

## Manual Deployment

If you prefer manual installation or the automated script fails:

### Step 1: System Preparation
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y curl wget gnupg2 software-properties-common
```

### Step 2: Install Docker
```bash
# Remove old Docker versions
sudo apt remove docker docker-engine docker.io containerd runc

# Add Docker GPG key and repository
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Step 3: Install Docker Compose
```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### Step 4: Install Additional Dependencies
```bash
sudo apt install -y python3 python3-pip nginx supervisor
```

### Step 5: Application Setup
```bash
# Clone repository
git clone https://github.com/lindiwe184/surveyprogresstracking.git
cd surveyprogresstracking

# Set up environment
cp backend/env.template backend/.env
# Edit .env with your actual credentials

# Build and start services
docker-compose build
docker-compose up -d
```

### Step 6: Configure Nginx
```bash
# Copy Nginx configuration
sudo cp nginx.conf /etc/nginx/sites-available/gbv-dashboard
sudo ln -s /etc/nginx/sites-available/gbv-dashboard /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Test and restart Nginx
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### Step 7: Configure Firewall
```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## Configuration

### Environment Variables (backend/.env)
```bash
# KoboToolbox Configuration
KOBO_API_URL=https://kf.kobotoolbox.org/api/v2/
KOBO_TOKEN=your_actual_token_here

# Database Configuration
DATABASE_URL=postgresql+psycopg2://survey_user:survey_password@localhost:5432/survey_tracking

# Application Settings
DEBUG=False
SECRET_KEY=your_secret_key_here

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/gbv-dashboard/app.log
```

### SSL/TLS Configuration (Optional but Recommended)

#### Using Let's Encrypt (Free SSL)
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo systemctl enable certbot.timer
```

#### Using Self-Signed Certificate
```bash
# Create SSL directory
sudo mkdir -p /etc/nginx/ssl

# Generate self-signed certificate
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/gbv-dashboard.key \
    -out /etc/nginx/ssl/gbv-dashboard.crt

# Update nginx.conf to include SSL configuration
```

## Service Management

### Docker Services
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart services
docker-compose restart

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

### System Services
```bash
# Check application service
sudo systemctl status gbv-dashboard

# Start/Stop/Restart
sudo systemctl start gbv-dashboard
sudo systemctl stop gbv-dashboard
sudo systemctl restart gbv-dashboard

# Check Nginx
sudo systemctl status nginx
sudo nginx -t  # Test configuration
```

## Monitoring and Maintenance

### Log Files
- Application logs: `/var/log/gbv-dashboard/`
- Nginx logs: `/var/log/nginx/`
- Docker logs: `docker-compose logs`

### Health Checks
```bash
# Check if services are running
curl http://localhost/health

# Check Docker containers
docker-compose ps

# Check system resources
htop
df -h
```

### Backup Strategy
```bash
# Database backup (PostgreSQL)
pg_dump -U survey_user -h localhost survey_tracking > backup_$(date +%Y%m%d).sql

# Configuration backup
tar -czf config_backup_$(date +%Y%m%d).tar.gz backend/.env nginx.conf docker-compose.yml
```

### Updates
```bash
# Update application code
git pull origin main
docker-compose build
docker-compose up -d

# Update system packages
sudo apt update && sudo apt upgrade -y
```

## Troubleshooting

### Common Issues

#### Services Won't Start
```bash
# Check Docker status
sudo systemctl status docker

# Check logs
docker-compose logs

# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

#### Port Conflicts
```bash
# Check what's using ports
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :8501

# Kill conflicting processes
sudo pkill -f nginx
```

#### Permission Issues
```bash
# Fix file permissions
sudo chown -R $USER:$USER .
chmod +x deploy.sh

# Fix log directory permissions
sudo chown -R $USER:$USER /var/log/gbv-dashboard
```

#### Database Issues
```bash
# Reset database
rm database/survey_tracking.db
docker-compose restart
```

### Performance Optimization

#### Resource Limits
Edit `docker-compose.yml` to add resource limits:
```yaml
services:
  gbv-dashboard:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
```

#### Nginx Tuning
```bash
# Edit /etc/nginx/nginx.conf
worker_processes auto;
worker_connections 1024;
```

## Security Considerations

### Firewall Configuration
```bash
# Allow only necessary ports
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### Regular Updates
```bash
# Set up automatic security updates
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### Access Control
- Use strong passwords for server access
- Implement SSH key authentication
- Consider VPN access for sensitive data
- Regularly rotate API keys

## Support and Documentation

### Useful Commands
```bash
# View real-time logs
docker-compose logs -f gbv-dashboard

# Access container shell
docker-compose exec gbv-dashboard bash

# Check resource usage
docker stats

# Cleanup unused resources
docker system prune -f
```

### Additional Resources
- [Docker Documentation](https://docs.docker.com/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [KoboToolbox API Documentation](https://support.kobotoolbox.org/api.html)

---

**Note**: Always test deployments in a staging environment before production use.