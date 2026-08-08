[CmdletBinding()]
param(
    [Parameter(Mandatory)][string] $MatrixPath,
    [Parameter(Mandatory)][string] $EvidenceDir,
    [string] $WebSocketUri = 'ws://127.0.0.1:4455',
    [string] $Password,
    [string] $PasswordFile,
    [string] $MainSource,
    [string] $VerticalSource,
    [int] $AitumWidth = 1440,
    [int] $AitumHeight = 2560,
    [int] $ObservationSeconds = 3,
    [switch] $CaptureScreenshots,
    [switch] $ExerciseButtons,
    [switch] $ExerciseOutputs,
    [switch] $Apply
)

$ErrorActionPreference = 'Stop'

function ConvertTo-HashtableDeep($Value) {
    if ($null -eq $Value) { return $null }
    if ($Value -is [string] -or $Value.GetType().IsPrimitive -or $Value -is [decimal]) { return $Value }
    if ($Value -is [Collections.IDictionary]) {
        $copy = [ordered]@{}
        foreach ($key in $Value.Keys) { $copy[$key] = ConvertTo-HashtableDeep $Value[$key] }
        return $copy
    }
    if ($Value -is [pscustomobject]) {
        $copy = [ordered]@{}
        foreach ($property in $Value.PSObject.Properties) { $copy[$property.Name] = ConvertTo-HashtableDeep $property.Value }
        return $copy
    }
    if ($Value -is [Collections.IEnumerable] -and $Value -isnot [string]) {
        return @($Value | ForEach-Object { ConvertTo-HashtableDeep $_ })
    }
    return $Value
}

function Get-Sha256Text([string] $Text) {
    $bytes = [Text.Encoding]::UTF8.GetBytes($Text)
    $hash = [Security.Cryptography.SHA256]::Create().ComputeHash($bytes)
    return ([BitConverter]::ToString($hash) -replace '-', '').ToLowerInvariant()
}

function Get-ObsAuth([string] $Secret, [string] $Salt, [string] $Challenge) {
    $sha = [Security.Cryptography.SHA256]::Create()
    $secretHash = $sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($Secret + $Salt))
    $secret = [Convert]::ToBase64String($secretHash)
    $authHash = $sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($secret + $Challenge))
    return [Convert]::ToBase64String($authHash)
}

function Receive-ObsMessage([Net.WebSockets.ClientWebSocket] $Socket) {
    $buffer = [byte[]]::new(65536)
    $stream = [IO.MemoryStream]::new()
    do {
        $segment = [ArraySegment[byte]]::new($buffer)
        $result = $Socket.ReceiveAsync($segment, [Threading.CancellationToken]::None).GetAwaiter().GetResult()
        if ($result.MessageType -eq [Net.WebSockets.WebSocketMessageType]::Close) { throw 'OBS WebSocket closed the connection.' }
        $stream.Write($buffer, 0, $result.Count)
    } until ($result.EndOfMessage)
    return [Text.Encoding]::UTF8.GetString($stream.ToArray()) | ConvertFrom-Json
}

function Send-ObsMessage([Net.WebSockets.ClientWebSocket] $Socket, [hashtable] $Message) {
    $json = $Message | ConvertTo-Json -Depth 20 -Compress
    $bytes = [Text.Encoding]::UTF8.GetBytes($json)
    $Socket.SendAsync([ArraySegment[byte]]::new($bytes), [Net.WebSockets.WebSocketMessageType]::Text, $true,
        [Threading.CancellationToken]::None).GetAwaiter().GetResult() | Out-Null
}

function Invoke-ObsRequest([Net.WebSockets.ClientWebSocket] $Socket, [string] $Type, [hashtable] $Data = @{}) {
    $id = [Guid]::NewGuid().ToString('n')
    Send-ObsMessage $Socket @{ op = 6; d = @{ requestType = $Type; requestId = $id; requestData = $Data } }
    while ($true) {
        $message = Receive-ObsMessage $Socket
        if ($message.op -ne 7 -or $message.d.requestId -ne $id) { continue }
        if (-not $message.d.requestStatus.result) {
            throw "OBS request '$Type' failed ($($message.d.requestStatus.code)): $($message.d.requestStatus.comment)"
        }
        return ConvertTo-HashtableDeep $message.d.responseData
    }
}

function Set-Case([hashtable] $Matrix, [string] $Id, [string] $Status, [hashtable] $Measurements, [string[]] $Evidence) {
    $case = @($Matrix.cases | Where-Object { $_.id -eq $Id })
    if ($case.Count -ne 1) { throw "Matrix must contain exactly one '$Id' case." }
    $case[0].status = $Status
    $case[0].observed_at = [DateTime]::UtcNow.ToString('o')
    $case[0].measurements = $Measurements
    $case[0].evidence = @($Evidence)
}

function Save-Matrix([hashtable] $Matrix, [string] $Path) {
    $Matrix | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $Path -Encoding UTF8
}

function Save-SourceScreenshot([Net.WebSockets.ClientWebSocket] $Socket, [string] $Source, [int] $Width, [int] $Height,
                               [string] $Path) {
    $response = Invoke-ObsRequest $Socket 'GetSourceScreenshot' @{
        sourceName = $Source; imageFormat = 'png'; imageWidth = $Width; imageHeight = $Height; imageCompressionQuality = -1
    }
    if ($response.imageData -notmatch '^data:image/png;base64,(.+)$') { throw "OBS returned an invalid PNG for '$Source'." }
    [IO.File]::WriteAllBytes($Path, [Convert]::FromBase64String($Matches[1]))
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

$matrixFile = (Resolve-Path -LiteralPath $MatrixPath).Path
$matrix = ConvertTo-HashtableDeep (Get-Content -Raw -LiteralPath $matrixFile | ConvertFrom-Json)
$output = [IO.Path]::GetFullPath($EvidenceDir)
$main = if ($MainSource) { $MainSource } else { [string]$matrix.main_source.name }
$vertical = if ($VerticalSource) { $VerticalSource } else { [string]$matrix.vertical_source.name }
$requiredCases = @('network-isolation','installation','module-load','source-isolation-landscape','source-isolation-vertical',
    'main-output-start','main-output-stop','vertical-output-start','aitum-output-missing','manual-controls',
    'source-hotkeys','restart-persistence','layout','uninstall')
$caseIds = @($matrix.cases | ForEach-Object { [string]$_.id })
$missingCases = @($requiredCases | Where-Object { $_ -notin $caseIds })
$duplicateCases = @($caseIds | Group-Object | Where-Object Count -gt 1 | ForEach-Object Name)
if ($missingCases.Count) { throw "Matrix is missing required cases: $($missingCases -join ', ')." }
if ($duplicateCases.Count) { throw "Matrix has duplicate case IDs: $($duplicateCases -join ', ')." }
if ([string]::IsNullOrWhiteSpace($main) -or [string]::IsNullOrWhiteSpace($vertical) -or $main -eq $vertical) {
    throw 'MainSource and VerticalSource must be distinct, non-empty source names.'
}
if ($ObservationSeconds -lt 1 -or $ObservationSeconds -gt 60) { throw 'ObservationSeconds must be between 1 and 60.' }

$plan = [ordered]@{
    apply = [bool]$Apply
    websocket_uri = $WebSocketUri
    matrix = $matrixFile
    evidence_dir = $output
    sources = @($main, $vertical)
    capture_screenshots = [bool]$CaptureScreenshots
    exercise_buttons = [bool]$ExerciseButtons
    exercise_outputs = [bool]$ExerciseOutputs
    mutations_restored = $true
}
if (-not $Apply) { $plan | ConvertTo-Json -Depth 5; exit 0 }

if ($Password -and $PasswordFile) { throw 'Use Password or PasswordFile, not both.' }
if ($PasswordFile) { $Password = (Get-Content -Raw -LiteralPath (Resolve-Path -LiteralPath $PasswordFile)).TrimEnd("`r", "`n") }
if ($WebSocketUri -notmatch '^wss?://(127\.0\.0\.1|localhost|\[::1\])(?::\d+)?/?$') {
    throw 'WebSocketUri must target localhost. Verify the actual listener separately with Test-LoopbackListeners.ps1.'
}
New-Item -ItemType Directory -Force -Path $output | Out-Null

$socket = [Net.WebSockets.ClientWebSocket]::new()
$original = @{}
$mainRestorePending = $false
$verticalRestorePending = $false
$mainOutputMayBeActive = $false
$verticalOutputMayBeActive = $false
try {
    $socket.ConnectAsync([Uri]$WebSocketUri, [Threading.CancellationToken]::None).GetAwaiter().GetResult()
    $hello = Receive-ObsMessage $socket
    if ($hello.op -ne 0) { throw 'Expected OBS WebSocket Hello message.' }
    $identify = @{ op = 1; d = @{ rpcVersion = 1 } }
    if ($hello.d.authentication) {
        if (-not $Password) { throw 'OBS WebSocket requires authentication; supply Password or PasswordFile.' }
        $identify.d.authentication = Get-ObsAuth $Password $hello.d.authentication.salt $hello.d.authentication.challenge
    }
    Send-ObsMessage $socket $identify
    $identified = Receive-ObsMessage $socket
    if ($identified.op -ne 2) { throw 'OBS WebSocket authentication or identification failed.' }

    $version = Invoke-ObsRequest $socket 'GetVersion'
    $aitumVersion = $null
    try { $aitumVersion = Invoke-ObsRequest $socket 'CallVendorRequest' @{ vendorName='aitum-vertical-canvas'; requestType='version'; requestData=@{} } }
    catch { $aitumVersion = @{ unavailable = $_.Exception.Message } }

    $original[$main] = Invoke-ObsRequest $socket 'GetInputSettings' @{ inputName = $main }
    $original[$vertical] = Invoke-ObsRequest $socket 'GetInputSettings' @{ inputName = $vertical }
    $snapshotPath = Join-Path $output 'source-settings-before.json'
    @{ obs=$version; aitum_vertical=$aitumVersion; main=$original[$main]; vertical=$original[$vertical] } |
        ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $snapshotPath -Encoding UTF8

    $mainSettings = ConvertTo-HashtableDeep $original[$main].inputSettings
    $verticalSettings = ConvertTo-HashtableDeep $original[$vertical].inputSettings
    $mainProbe = "runtime-isolation-main-$([Guid]::NewGuid().ToString('n').Substring(0,8))"
    $mainMutated = ConvertTo-HashtableDeep $mainSettings
    $mainMutated.session_title = $mainProbe
    $mainRestorePending = $true
    Invoke-ObsRequest $socket 'SetInputSettings' @{ inputName=$main; inputSettings=$mainMutated; overlay=$false } | Out-Null
    $mainAfter = Invoke-ObsRequest $socket 'GetInputSettings' @{ inputName=$main }
    $verticalAfterMain = Invoke-ObsRequest $socket 'GetInputSettings' @{ inputName=$vertical }
    $verticalStable = (Get-Sha256Text ($verticalSettings | ConvertTo-Json -Depth 20 -Compress)) -eq
        (Get-Sha256Text ($verticalAfterMain.inputSettings | ConvertTo-Json -Depth 20 -Compress))
    $mainChanged = $mainAfter.inputSettings.session_title -eq $mainProbe
    $mainIsolationStatus = if ($mainChanged -and $verticalStable) { 'passed' } else { 'failed' }
    Set-Case $matrix 'source-isolation-landscape' $mainIsolationStatus @{ target_changed=$mainChanged; peer_unchanged=$verticalStable } @($snapshotPath)
    Invoke-ObsRequest $socket 'SetInputSettings' @{ inputName=$main; inputSettings=$mainSettings; overlay=$false } | Out-Null
    $mainRestorePending = $false

    $verticalProbe = "runtime-isolation-vertical-$([Guid]::NewGuid().ToString('n').Substring(0,8))"
    $verticalMutated = ConvertTo-HashtableDeep $verticalSettings
    $verticalMutated.session_title = $verticalProbe
    $verticalRestorePending = $true
    Invoke-ObsRequest $socket 'SetInputSettings' @{ inputName=$vertical; inputSettings=$verticalMutated; overlay=$false } | Out-Null
    $verticalAfter = Invoke-ObsRequest $socket 'GetInputSettings' @{ inputName=$vertical }
    $mainAfterVertical = Invoke-ObsRequest $socket 'GetInputSettings' @{ inputName=$main }
    $mainStable = (Get-Sha256Text ($mainSettings | ConvertTo-Json -Depth 20 -Compress)) -eq
        (Get-Sha256Text ($mainAfterVertical.inputSettings | ConvertTo-Json -Depth 20 -Compress))
    $verticalChanged = $verticalAfter.inputSettings.session_title -eq $verticalProbe
    $verticalIsolationStatus = if ($verticalChanged -and $mainStable) { 'passed' } else { 'failed' }
    Set-Case $matrix 'source-isolation-vertical' $verticalIsolationStatus @{ target_changed=$verticalChanged; peer_unchanged=$mainStable } @($snapshotPath)
    Invoke-ObsRequest $socket 'SetInputSettings' @{ inputName=$vertical; inputSettings=$verticalSettings; overlay=$false } | Out-Null
    $verticalRestorePending = $false
    Start-Sleep -Milliseconds 300

    $shots = @()
    if ($CaptureScreenshots) {
        $mainPng = Join-Path $output 'landscape-2560x1440.png'
        $verticalPng = Join-Path $output 'vertical-1440x2560.png'
        $shots += @{ path=$mainPng; sha256=(Save-SourceScreenshot $socket $main 2560 1440 $mainPng) }
        $shots += @{ path=$verticalPng; sha256=(Save-SourceScreenshot $socket $vertical 1440 2560 $verticalPng) }
    }

    if ($ExerciseButtons) {
        foreach ($source in @($main, $vertical)) {
            Invoke-ObsRequest $socket 'PressInputPropertiesButton' @{ inputName=$source; propertyName='start_pause' } | Out-Null
            Start-Sleep -Seconds $ObservationSeconds
            Invoke-ObsRequest $socket 'PressInputPropertiesButton' @{ inputName=$source; propertyName='start_pause' } | Out-Null
            Invoke-ObsRequest $socket 'PressInputPropertiesButton' @{ inputName=$source; propertyName='reset' } | Out-Null
        }
        Set-Case $matrix 'manual-controls' 'unsupported' @{ reason='buttons-invoked-but-timer-text-requires-screenshot-or-visible-host-review' } @($shots.path)
    }

    if ($ExerciseOutputs) {
        $mainOutputMayBeActive = $true
        Invoke-ObsRequest $socket 'StartStream' | Out-Null
        Start-Sleep -Seconds $ObservationSeconds
        $mainStatus = Invoke-ObsRequest $socket 'GetStreamStatus'
        Invoke-ObsRequest $socket 'StopStream' | Out-Null
        $mainOutputMayBeActive = $false
        $mainOutputStatus = if ($mainStatus.outputActive) { 'unsupported' } else { 'failed' }
        Set-Case $matrix 'main-output-start' $mainOutputStatus @{ output_active=[bool]$mainStatus.outputActive; reason='timer-routing-needs-before-and-during-render-review' } @($shots.path)
        Set-Case $matrix 'main-output-stop' 'unsupported' @{ reason='timer-stop-needs-after-render-review' } @($shots.path)

        $verticalOutputMayBeActive = $true
        $startVertical = Invoke-ObsRequest $socket 'CallVendorRequest' @{
            vendorName='aitum-vertical-canvas'; requestType='start_streaming'; requestData=@{width=$AitumWidth;height=$AitumHeight}
        }
        Start-Sleep -Seconds $ObservationSeconds
        $verticalStatus = Invoke-ObsRequest $socket 'CallVendorRequest' @{
            vendorName='aitum-vertical-canvas'; requestType='status'; requestData=@{width=$AitumWidth;height=$AitumHeight}
        }
        Invoke-ObsRequest $socket 'CallVendorRequest' @{
            vendorName='aitum-vertical-canvas'; requestType='stop_streaming'; requestData=@{width=$AitumWidth;height=$AitumHeight}
        } | Out-Null
        $verticalOutputMayBeActive = $false
        $verticalOutputStatus = if ($verticalStatus.responseData.streaming) { 'unsupported' } else { 'failed' }
        Set-Case $matrix 'vertical-output-start' $verticalOutputStatus @{ vendor_start=$startVertical; vendor_status=$verticalStatus; reason='timer-routing-needs-before-and-during-render-review' } @($shots.path)
    }

    $runPath = Join-Path $output 'websocket-run.json'
    $plan.result = @{ obs=$version; aitum_vertical=$aitumVersion; screenshots=$shots; settings_snapshot=$snapshotPath }
    $plan | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $runPath -Encoding UTF8
    Save-Matrix $matrix $matrixFile
    $plan | ConvertTo-Json -Depth 20
}
finally {
    if ($socket.State -eq [Net.WebSockets.WebSocketState]::Open) {
        if ($mainRestorePending -and $original.Contains($main)) {
            try { Invoke-ObsRequest $socket 'SetInputSettings' @{ inputName=$main; inputSettings=$original[$main].inputSettings; overlay=$false } | Out-Null } catch { Write-Warning "Could not restore '$main': $($_.Exception.Message)" }
        }
        if ($verticalRestorePending -and $original.Contains($vertical)) {
            try { Invoke-ObsRequest $socket 'SetInputSettings' @{ inputName=$vertical; inputSettings=$original[$vertical].inputSettings; overlay=$false } | Out-Null } catch { Write-Warning "Could not restore '$vertical': $($_.Exception.Message)" }
        }
        if ($mainOutputMayBeActive) {
            try { Invoke-ObsRequest $socket 'StopStream' | Out-Null } catch { Write-Warning "Could not stop the main test stream: $($_.Exception.Message)" }
        }
        if ($verticalOutputMayBeActive) {
            try {
                Invoke-ObsRequest $socket 'CallVendorRequest' @{
                    vendorName='aitum-vertical-canvas'; requestType='stop_streaming'; requestData=@{width=$AitumWidth;height=$AitumHeight}
                } | Out-Null
            } catch { Write-Warning "Could not stop the Aitum Vertical test stream: $($_.Exception.Message)" }
        }
        $socket.CloseAsync([Net.WebSockets.WebSocketCloseStatus]::NormalClosure, 'runtime matrix complete',
            [Threading.CancellationToken]::None).GetAwaiter().GetResult()
    }
    $socket.Dispose()
}
