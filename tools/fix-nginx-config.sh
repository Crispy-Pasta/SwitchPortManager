#!/bin/bash

# Fix nginx configuration for Dell Port Tracer
# This script fixes the port mismatch in nginx configuration

echo "🔧 Fixing nginx configuration for Dell Port Tracer..."

# Backup original configuration
echo "📦 Creating backup of original configuration..."
sudo cp /etc/nginx/sites-enabled/kmc-port-tracer.conf /etc/nginx/sites-enabled/kmc-port-tracer.conf.backup

# Replace port 8443 with 5000 in nginx configuration
echo "🔄 Updating proxy port from 8443 to 5000..."
sudo sed -i 's/8443/5000/g' /etc/nginx/sites-enabled/kmc-port-tracer.conf

# Test nginx configuration
echo "🧪 Testing nginx configuration..."
if sudo nginx -t; then
    echo "✅ Nginx configuration is valid"
    
    # Reload nginx
    echo "🔄 Reloading nginx..."
    sudo nginx -s reload
    
    echo "✅ Fix completed successfully!"
    echo "🌐 The Dell Port Tracer should now be accessible via nginx"
    echo ""
    echo "📊 You can test by visiting:"
    echo "   https://kmc-port-tracer"
    echo "   https://10.50.0.225"
    echo ""
    echo "🔍 Check status with:"
    echo "   curl -k https://localhost/health"
    
else
    echo "❌ Nginx configuration test failed"
    echo "📦 Restoring backup..."
    sudo cp /etc/nginx/sites-enabled/kmc-port-tracer.conf.backup /etc/nginx/sites-enabled/kmc-port-tracer.conf
    echo "❌ Fix failed - original configuration restored"
    exit 1
fi
