[CmdletBinding()]
param(
    [Parameter(Mandatory)][int] $WebSocketPort,
    [Parameter(Mandatory)][int] $MainRtmpPort,
    [Parameter(Mandatory)][int] $VerticalRtmpPort,
    [Parameter(Mandatory)][string] $WebSocketConfig,
    [switch] $Json
)
$ErrorActionPreference = 'Stop'
$configPath = (Resolve-Path -LiteralPath $WebSocketConfig).Path
try { $config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json }
catch { Write-Error "Invalid OBS WebSocket config: $($_.Exception.Message)"; exit 2 }
$authRequired = $config.auth_required -eq $true
$serverEnabled = $config.server_enabled -eq $true
$configuredPort = [int]$config.server_port
$rows = @()
$errors = @()
$roles = [ordered]@{ websocket=$WebSocketPort; main_rtmp=$MainRtmpPort; vertical_rtmp=$VerticalRtmpPort }
if ($roles.Values | Group-Object | Where-Object Count -gt 1) { $errors += 'WebSocket, main RTMP, and vertical RTMP ports must be distinct' }
foreach ($role in $roles.GetEnumerator()) {
    $value = [int]$role.Value
    $listeners = @(Get-NetTCPConnection -State Listen -LocalPort $value -ErrorAction SilentlyContinue)
    if (-not $listeners) {
        $listeners = @([Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() |
            Where-Object Port -eq $value |
            ForEach-Object { [pscustomobject]@{ LocalAddress=$_.Address.ToString(); OwningProcess=$null } })
    }
    if (-not $listeners) { $errors += "$($role.Key) port $value has no TCP listener"; continue }
    foreach ($listener in $listeners) {
        $loopback = $listener.LocalAddress -in @('127.0.0.1','::1')
        $rows += [ordered]@{ role=$role.Key; port=$value; address=$listener.LocalAddress; process_id=$listener.OwningProcess; loopback=$loopback }
        if (-not $loopback) { $errors += "$($role.Key) port $value listens on non-loopback address $($listener.LocalAddress)" }
    }
}
if (-not $serverEnabled) { $errors += 'OBS WebSocket server is disabled' }
if (-not $authRequired) { $errors += 'OBS WebSocket authentication is disabled' }
if ($configuredPort -ne $WebSocketPort) { $errors += "OBS WebSocket config port $configuredPort does not match designated port $WebSocketPort" }
$result = [ordered]@{ passed=($errors.Count -eq 0); websocket_config=$configPath; websocket_server_enabled=$serverEnabled; websocket_auth_required=$authRequired; websocket_configured_port=$configuredPort; roles=$roles; listeners=$rows; errors=$errors }
if ($Json) { $result | ConvertTo-Json -Depth 5 } else { "{0}: {1}" -f $(if($result.passed){'passed'}else{'failed'}),($errors -join '; ') }
if (-not $result.passed) { exit 1 }
