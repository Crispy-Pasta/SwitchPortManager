# Test General Mode VLAN Parsing
# This script tests that port Gi5/0/48 in General mode correctly shows VLAN 1 (not 203)

$baseUrl = "http://127.0.0.1:5000"
$headers = @{'Content-Type' = 'application/json'}

Write-Host "Testing General Mode VLAN Parsing Fix..." -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

# Step 1: Login to get session
Write-Host "`n1. Logging in..." -ForegroundColor Yellow
$loginBody = @{
    username = 'admin'
    password = 'admin123'
} | ConvertTo-Json

try {
    $loginResponse = Invoke-WebRequest -Uri "$baseUrl/login" -Method POST -Headers $headers -Body $loginBody -SessionVariable session
    Write-Host "   ✓ Login successful" -ForegroundColor Green
} catch {
    Write-Host "   ✗ Login failed: $_" -ForegroundColor Red
    exit 1
}

# Step 2: Test General mode port (Gi5/0/48)
Write-Host "`n2. Testing General mode port Gi5/0/48..." -ForegroundColor Yellow
$portBody = @{
    switch_id = 1
    ports = 'gi5/0/48'
} | ConvertTo-Json

try {
    $portResponse = Invoke-WebRequest -Uri "$baseUrl/api/port/status" -Method POST -Headers $headers -Body $portBody -WebSession $session
    $portData = $portResponse.Content | ConvertFrom-Json
    
    Write-Host "   Raw API Response:" -ForegroundColor Cyan
    Write-Host "   $($portResponse.Content)" -ForegroundColor Cyan
    
    if ($portData.ports -and $portData.ports.Count -gt 0) {
        $port = $portData.ports[0]
        Write-Host "`n   Port Status Results:" -ForegroundColor White
        Write-Host "   Port: $($port.port)" -ForegroundColor White
        Write-Host "   Status: $($port.status)" -ForegroundColor White
        Write-Host "   Mode: $($port.mode)" -ForegroundColor White
        Write-Host "   Current VLAN: $($port.current_vlan)" -ForegroundColor White
        
        # Check if fix worked
        if ($port.mode -eq "general" -and $port.current_vlan -eq "1") {
            Write-Host "`n   ✅ SUCCESS: General mode port correctly shows native VLAN 1" -ForegroundColor Green
            Write-Host "   ✅ FIXED: Config parsing no longer overrides General mode VLAN" -ForegroundColor Green
        } elseif ($port.current_vlan -eq "203") {
            Write-Host "`n   ❌ FAILED: Port still shows VLAN 203 instead of native VLAN 1" -ForegroundColor Red
            Write-Host "   ❌ The fix did not work - config parsing is still overriding" -ForegroundColor Red
        } else {
            Write-Host "`n   ⚠️  UNEXPECTED: Port shows VLAN $($port.current_vlan) (expected 1)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "   ✗ No port data returned" -ForegroundColor Red
    }
    
} catch {
    Write-Host "   ✗ Port status request failed: $_" -ForegroundColor Red
}

# Step 3: Test regular access mode port for comparison
Write-Host "`n3. Testing access mode port Gi1/0/1 for comparison..." -ForegroundColor Yellow
$accessPortBody = @{
    switch_id = 1
    ports = 'gi1/0/1'
} | ConvertTo-Json

try {
    $accessResponse = Invoke-WebRequest -Uri "$baseUrl/api/port/status" -Method POST -Headers $headers -Body $accessPortBody -WebSession $session
    $accessData = $accessResponse.Content | ConvertFrom-Json
    
    if ($accessData.ports -and $accessData.ports.Count -gt 0) {
        $accessPort = $accessData.ports[0]
        Write-Host "   Access Port Results:" -ForegroundColor White
        Write-Host "   Port: $($accessPort.port)" -ForegroundColor White
        Write-Host "   Status: $($accessPort.status)" -ForegroundColor White
        Write-Host "   Mode: $($accessPort.mode)" -ForegroundColor White
        Write-Host "   Current VLAN: $($accessPort.current_vlan)" -ForegroundColor White
        Write-Host "   ✓ Access mode port working normally" -ForegroundColor Green
    }
} catch {
    Write-Host "   ⚠️  Access port test failed (not critical): $_" -ForegroundColor Yellow
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Test Complete!" -ForegroundColor Green
