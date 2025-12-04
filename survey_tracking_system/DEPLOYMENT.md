# GBV Readiness Survey Dashboard - Linux Server Deployment Guide

This guide covers deploying the GBV Readiness Survey Dashboard on a Linux server with production-ready configuration.

## Server Requirements

### Minimum System Requirements
- **OS**: Ubuntu 20.04 LTS or later / CentOS 8+ / RHEL 8+
- **RAM**: 2GB minimum, 4GB recommended
- **CPU**: 2 cores minimum
- **Storage**: 20GB minimum
- **Network**: Public IP with ports 80/443 access

### Software Requirements
- Python 3.8+
- Nginx (reverse proxy)
- Supervisor (process management)
- Git
- SSL certificate (Let's Encrypt recommended)

## Deployment Methods

### Option 1: Manual Deployment (Recommended for Learning)

#### 1. Server Setup
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv nginx supervisor git curl

# Create application user
sudo useradd -m -s /bin/bash gbvapp
sudo usermod -aG sudo gbvapp
```

#### 2. Application Deployment
```bash
# Switch to application user
sudo su - gbvapp

# Clone repository
git clone https://github.com/lindiwe184/surveyprogresstracking.git
cd surveyprogresstracking

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install backend dependencies
cd backend
pip install -r requirements.txt
pip install gunicorn  # Production WSGI server

# Install frontend dependencies
cd ../frontend
pip install -r requirements.txt

# Set up environment variables
cd ../backend
cp env.template .env
# Edit .env with your production KoboToolbox credentials
nano .env
```

#### 3. Environment Configuration
```bash
# Backend .env file
KOBO_TOKEN=your_production_kobo_token
KOBO_ASSET_ID=your_survey_asset_id
KOBO_BASE_URL=https://kf.kobotoolbox.org
FLASK_PORT=5002
FLASK_ENV=production
```

### Option 2: Docker Deployment (Recommended for Production)

#### 1. Install Docker
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

## Process Management with Supervisor

### Backend Service Configuration
Create `/etc/supervisor/conf.d/gbv-backend.conf`:
```ini
[program:gbv-backend]
command=/home/gbvapp/surveyprogresstracking/venv/bin/gunicorn -w 4 -b 127.0.0.1:5002 kobo_app:app
directory=/home/gbvapp/surveyprogresstracking/backend
user=gbvapp
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/gbv-backend.log
environment=PATH="/home/gbvapp/surveyprogresstracking/venv/bin"
```

### Frontend Service Configuration
Create `/etc/supervisor/conf.d/gbv-frontend.conf`:
```ini
[program:gbv-frontend]
command=/home/gbvapp/surveyprogresstracking/venv/bin/streamlit run kobo_dashboard.py --server.port 8501 --server.address 127.0.0.1 --server.headless true
directory=/home/gbvapp/surveyprogresstracking/frontend
user=gbvapp
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/gbv-frontend.log
environment=PATH="/home/gbvapp/surveyprogresstracking/venv/bin"
```

### Start Services
```bash
# Reload supervisor configuration
sudo supervisorctl reread
sudo supervisorctl update

# Start services
sudo supervisorctl start gbv-backend
sudo supervisorctl start gbv-frontend

# Check status
sudo supervisorctl status
```

## Nginx Reverse Proxy Configuration

### Create Nginx Configuration
Create `/etc/nginx/sites-available/gbv-dashboard`:
```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    # SSL Configuration (after setting up Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

    # Frontend (Streamlit Dashboard)
    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 86400;
    }

    # Backend API
    location /api {
        proxy_pass http://127.0.0.1:5002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files (if any)
    location /static {
        alias /home/gbvapp/surveyprogresstracking/frontend/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### Enable Nginx Configuration
```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/gbv-dashboard /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

## SSL Certificate Setup (Let's Encrypt)

```bash
# Install Certbot
sudo apt install snapd
sudo snap install core; sudo snap refresh core
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot

# Obtain SSL certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Verify auto-renewal
sudo certbot renew --dry-run
```

## Firewall Configuration

```bash
# Configure UFW firewall
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw --force enable
```

## Monitoring and Maintenance

### Log Management
```bash
# View application logs
sudo tail -f /var/log/gbv-backend.log
sudo tail -f /var/log/gbv-frontend.log

# View Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# View supervisor logs
sudo supervisorctl tail gbv-backend
sudo supervisorctl tail gbv-frontend
```

### System Monitoring
```bash
# Install monitoring tools
sudo apt install htop iotop nethogs

# Monitor resources
htop                    # CPU and memory usage
iotop                   # Disk I/O
nethogs                 # Network usage per process
```

### Backup Strategy
```bash
# Create backup script
sudo nano /usr/local/bin/gbv-backup.sh

#!/bin/bash
BACKUP_DIR="/backup/gbv-dashboard"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup application code
tar -czf $BACKUP_DIR/gbv-app-$DATE.tar.gz -C /home/gbvapp surveyprogresstracking

# Backup database (if applicable)
cp /home/gbvapp/surveyprogresstracking/backend/survey_tracking.db $BACKUP_DIR/database-$DATE.db

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
find $BACKUP_DIR -name "*.db" -mtime +7 -delete

# Make executable
sudo chmod +x /usr/local/bin/gbv-backup.sh

# Add to crontab for daily backups
echo "0 2 * * * /usr/local/bin/gbv-backup.sh" | sudo crontab -
```

## Performance Optimization

### Application Level
```bash
# Backend optimization
# Use more Gunicorn workers based on CPU cores
# Workers = (2 x CPU cores) + 1

# Frontend optimization
# Configure Streamlit for production in ~/.streamlit/config.toml
mkdir -p ~/.streamlit
cat > ~/.streamlit/config.toml << EOF
[server]
headless = true
port = 8501
enableCORS = false
enableXsrfProtection = false

[browser]
gatherUsageStats = false
EOF
```

### Server Level
```bash
# Increase file descriptor limits
echo "* soft nofile 65535" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65535" | sudo tee -a /etc/security/limits.conf

# Optimize kernel parameters
sudo tee -a /etc/sysctl.conf << EOF
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.ip_local_port_range = 1024 65535
EOF

sudo sysctl -p
```

## Troubleshooting

### Common Issues
1. **Service won't start**: Check logs with `sudo supervisorctl tail servicename`
2. **502 Bad Gateway**: Verify backend is running on correct port
3. **SSL issues**: Check certificate with `sudo certbot certificates`
4. **High memory usage**: Monitor with `htop` and adjust worker counts

### Health Checks
```bash
# Check if services are running
curl http://localhost:5002/api/health    # Backend health
curl http://localhost:8501/_stcore/health  # Frontend health

# Check from outside
curl https://your-domain.com/api/health
```

## Security Best Practices

1. **Keep system updated**: `sudo apt update && sudo apt upgrade`
2. **Use strong passwords**: For all accounts
3. **Disable root SSH**: Edit `/etc/ssh/sshd_config`
4. **Regular backups**: Automated and tested
5. **Monitor logs**: Set up log monitoring/alerting
6. **Firewall rules**: Only open necessary ports
7. **SSL/TLS**: Always use HTTPS in production

## Deployment Checklist

- [ ] Server provisioned with adequate resources
- [ ] Domain name configured with DNS
- [ ] SSL certificate installed and auto-renewal configured
- [ ] Application deployed and running
- [ ] Database backed up (if applicable)
- [ ] Monitoring and logging configured
- [ ] Firewall rules applied
- [ ] Backup strategy implemented
- [ ] Performance optimization applied
- [ ] Security hardening completed

Your GBV Readiness Survey Dashboard should now be accessible at `https://your-domain.com` with production-grade reliability and security.