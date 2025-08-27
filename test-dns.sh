#!/bin/bash
# DNS Test Script for Let's Encrypt Setup

DOMAIN="porttracer.kmc.int"
EXPECTED_IP="103.141.203.170"

echo "🌐 Testing DNS resolution for $DOMAIN"
echo "Expected IP: $EXPECTED_IP"
echo "=========================================="

# Test DNS resolution
echo "🔍 Checking DNS resolution..."
RESOLVED_IP=$(nslookup $DOMAIN 8.8.8.8 | grep -A1 "Name:" | grep "Address:" | awk '{print $2}' | head -1)

if [ -z "$RESOLVED_IP" ]; then
    echo "❌ DNS resolution failed!"
    echo "📋 Please create DNS A record:"
    echo "   Name: porttracer"
    echo "   Domain: kmc.int" 
    echo "   Value: $EXPECTED_IP"
    exit 1
elif [ "$RESOLVED_IP" = "$EXPECTED_IP" ]; then
    echo "✅ DNS resolution successful!"
    echo "   $DOMAIN → $RESOLVED_IP"
    echo ""
    echo "🚀 Ready for Let's Encrypt certificate generation!"
    exit 0
else
    echo "⚠️  DNS resolved to wrong IP:"
    echo "   Expected: $EXPECTED_IP"
    echo "   Got: $RESOLVED_IP"
    echo ""
    echo "📋 Please update your DNS A record to point to: $EXPECTED_IP"
    exit 1
fi
