[CmdletBinding()]
param(
    [Parameter(Mandatory)][string] $PluginName,
    [string] $MainSource = 'Plugin Landscape Test',
    [string] $VerticalSource = 'Plugin Vertical Test',
    [string] $AitumOutput = 'Test Vertical Output',
    [string] $CommitSha,
    [string] $PluginDll,
    [string] $ObsVersion,
    [string] $AitumMultistreamVersion,
    [string] $AitumVerticalVersion,
    [string] $OutputPath
)
$ErrorActionPreference = 'Stop'
function New-TestCase([string] $Id, [string] $Action, [string] $Expected) {
    return [ordered]@{ id=$Id; action=$Action; expected=$Expected; status='not_run'; observed_at=$null; measurements=[ordered]@{}; evidence=@() }
}
$cases = @(
    (New-TestCase 'network-isolation' 'verify-listeners' 'websocket-authenticated-and-all-listeners-loopback-only'),
    (New-TestCase 'installation' 'install-disposable-package' 'exact-runtime-files-and-generated-uninstaller'),
    (New-TestCase 'module-load' 'start-obs' 'plugin-and-aitum-modules-loaded'),
    (New-TestCase 'source-isolation-landscape' 'edit-landscape' 'vertical-unchanged'),
    (New-TestCase 'source-isolation-vertical' 'edit-vertical' 'landscape-unchanged'),
    (New-TestCase 'main-output-start' 'start-main-output' 'landscape-advances-vertical-holds'),
    (New-TestCase 'main-output-stop' 'stop-main-output' 'landscape-stops-per-documented-behavior'),
    (New-TestCase 'vertical-output-start' 'start-aitum-output' 'vertical-advances-landscape-holds'),
    (New-TestCase 'aitum-output-missing' 'select-missing-output' 'rendering-continues-timer-unbound'),
    (New-TestCase 'manual-controls' 'start-pause-reset' 'target-source-only'),
    (New-TestCase 'source-hotkeys' 'trigger-source-hotkeys' 'target-source-only'),
    (New-TestCase 'restart-persistence' 'restart-obs' 'settings-hotkeys-and-documented-timer-state-persist'),
    (New-TestCase 'layout' 'render-supported-canvases' 'no-clipping-and-legible-branding'),
    (New-TestCase 'uninstall' 'uninstall-with-obs-closed' 'runtime-files-removed-source-unavailable')
)
$dllIdentity = $null
if ($PluginDll) {
    $resolvedDll = (Resolve-Path -LiteralPath $PluginDll).Path
    $item = Get-Item -LiteralPath $resolvedDll
    $dllIdentity = [ordered]@{ path=$resolvedDll; sha256=(Get-FileHash -LiteralPath $resolvedDll -Algorithm SHA256).Hash.ToLowerInvariant(); last_write_utc=$item.LastWriteTimeUtc.ToString('o') }
}
$result = [ordered]@{ schema_version=1; generated_at_utc=[DateTime]::UtcNow.ToString('o'); plugin=$PluginName; release_identity=[ordered]@{ commit=$CommitSha; dll=$dllIdentity }; versions=[ordered]@{ obs=$ObsVersion; aitum_multistream=$AitumMultistreamVersion; aitum_vertical=$AitumVerticalVersion }; main_source=[ordered]@{ name=$MainSource; uuid=$null; canvas=@(2560,1440) }; vertical_source=[ordered]@{ name=$VerticalSource; uuid=$null; canvas=@(1440,2560) }; aitum_output=$AitumOutput; listeners=@(); network_policy='verify-loopback-before-start'; cases=$cases }
$json = $result | ConvertTo-Json -Depth 6
if ($OutputPath) { $json | Set-Content -LiteralPath $OutputPath -Encoding UTF8 } else { $json }
