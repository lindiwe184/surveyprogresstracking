#!/bin/bash

# Enhanced Security Setup Script for GBV Dashboard
echo "🛡️  Configuring Enhanced Security..."

# 1. Update system packages
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# 2. Install fail2ban for intrusion prevention
echo "🚫 Installing Fail2ban..."
sudo apt install fail2ban -y

# 3. Configure fail2ban for Nginx
sudo tee /etc/fail2ban/jail.local > /dev/null << EOF
[DEFAULT]
bantime = 1800
findtime = 300
maxretry = 3

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 3
bantime = 3600

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 5
bantime = 3600
EOF

# 4. Create stronger password file
echo "🔐 Creating stronger authentication..."
sudo htpasswd -c /etc/nginx/.htpasswd admin

# 5. Set up UFW firewall
echo "🔥 Configuring firewall..."
sudo ufw --force enable
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 5000/tcp  # Flask API (internal)
sudo ufw allow 8501/tcp  # Streamlit (internal)

# 6. Configure log monitoring
echo "📊 Setting up log monitoring..."
sudo mkdir -p /var/log/gbv-dashboard
sudo chown www-data:www-data /var/log/gbv-dashboard

# 7. Update Nginx configuration with security enhancements
echo "⚙️  Updating Nginx configuration..."
sudo cp nginx-secure.conf /etc/nginx/sites-available/gbv-dashboard
sudo ln -sf /etc/nginx/sites-available/gbv-dashboard /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# 8. Test and reload Nginx
sudo nginx -t && sudo systemctl reload nginx

# 9. Start fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# 10. Set up automatic security updates
echo "🔄 Enabling automatic security updates..."
sudo apt install unattended-upgrades -y
sudo dpkg-reconfigure -plow unattended-upgrades

echo "✅ Enhanced security configuration complete!"
echo ""
echo "🔒 Security Features Enabled:"
echo "   • HSTS (HTTP Strict Transport Security)"
echo "   • Content Security Policy (CSP)"
echo "   • XSS Protection"
echo "   • Rate Limiting"
echo "   • Intrusion Detection (Fail2ban)"
echo "   • Firewall (UFW)"
echo "   • Enhanced SSL/TLS"
echo "   • Automatic Security Updates"
echo ""
echo "⚠️  Certificate Warning Fix Options:"
echo "   1. Click 'Advanced' → 'Proceed' (safe for internal use)"
echo "   2. Get proper SSL certificate from IT department"
echo "   3. Add certificate to trusted store on client machines"