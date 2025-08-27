#!/bin/bash
# Let's Encrypt Setup Script for Dell Port Tracer
# Requirements: Public domain name pointing to this server

# Configuration - UPDATE THESE VALUES
DOMAIN="porttracer.kmc.int"  # Using your kmc.int domain
EMAIL="admin@kmc.int"        # Replace with your actual email

echo "🔒 Setting up Let's Encrypt SSL for $DOMAIN"
echo "================================================"

# Install Certbot
echo "📦 Installing Certbot..."
sudo apt update
sudo apt install -y certbot

# Stop Nginx temporarily for certificate generation
echo "⏹️ Stopping Nginx temporarily..."
cd /opt/dell-port-tracer/app
docker-compose -f docker-compose.prod.yml stop nginx

# Generate Let's Encrypt certificate
echo "🔐 Generating Let's Encrypt certificate..."
sudo certbot certonly --standalone \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    --domains "$DOMAIN"

# Copy certificates to our SSL directory
echo "📁 Copying certificates..."
sudo cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" /opt/dell-port-tracer/ssl/
sudo cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" /opt/dell-port-tracer/ssl/
sudo chown janzen:janzen /opt/dell-port-tracer/ssl/*.pem

# Update Nginx configuration for the domain
echo "🔧 Updating Nginx configuration..."
sed -i "s/server_name kmc-port-tracer 10.50.0.225 localhost;/server_name $DOMAIN;/g" /opt/dell-port-tracer/config/nginx.conf

# Restart services
echo "🚀 Restarting services..."
docker-compose -f docker-compose.prod.yml up -d

# Set up auto-renewal
echo "🔄 Setting up auto-renewal..."
sudo crontab -l > /tmp/crontab.bak 2>/dev/null || true
echo "0 12 * * * /usr/bin/certbot renew --quiet && cd /opt/dell-port-tracer/app && docker-compose -f docker-compose.prod.yml restart nginx" | sudo tee -a /tmp/crontab.bak
sudo crontab /tmp/crontab.bak

echo ""
echo "✅ Let's Encrypt setup complete!"
echo "🌐 Your site is now available at: https://$DOMAIN"
echo "🔄 Certificate will auto-renew every 90 days"
echo ""
echo "⚠️  Make sure your domain DNS points to this server's public IP!"
