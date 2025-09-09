# Simple Test for General Mode VLAN Parsing
$baseUrl = "http://127.0.0.1:5000"
$headers = @{'Content-Type' = 'application/json'}

Write-Host "Testing General Mode VLAN Parsing Fix..."
Write-Host "========================================"

# Login
Write-Host "`nStep 1: Logging in..."
$loginBody = @{
    username = 'admin'
    password = 'admin123'
} | ConvertTo-Json

try {
    $loginResponse = Invoke-WebRequest -Uri "$baseUrl/login" -Method POST -Headers $headers -Body $loginBody -SessionVariable session
    Write-Host "Login successful"
} catch {
    Write-Host "Login failed: $_"
    exit 1
}

# Test General mode port
Write-Host "`nStep 2: Testing General mode port Gi5/0/48..."
$portBody = @{
    switch_id = 1
    ports = 'gi5/0/48'
} | ConvertTo-Json

try {
    $portResponse = Invoke-WebRequest -Uri "$baseUrl/api/port/status" -Method POST -Headers $headers -Body $portBody -WebSession $session
    $portData = $portResponse.Content | ConvertFrom-Json
    
    Write-Host "Raw Response: $($portResponse.Content)"
    
    if ($portData.ports -and $portData.ports.Count -gt 0) {
        $port = $portData.ports[0]
        Write-Host "`nPort Status Results:"
        Write-Host "Port: $($port.port)"
        Write-Host "Status: $($port.status)" 
        Write-Host "Mode: $($port.mode)"
        Write-Host "Current VLAN: $($port.current_vlan)"
        
        if ($port.mode -eq "general" -and $port.current_vlan -eq "1") {
            Write-Host "`nSUCCESS: General mode port correctly shows native VLAN 1"
        } elseif ($port.current_vlan -eq "203") {
            Write-Host "`nFAILED: Port still shows VLAN 203 instead of native VLAN 1"
        } else {
            Write-Host "`nUNEXPECTED: Port shows VLAN $($port.current_vlan) (expected 1)"
        }
    } else {
        Write-Host "No port data returned"
    }
} catch {
    Write-Host "Port status request failed: $_"
}

Write-Host "`nTest Complete!"
