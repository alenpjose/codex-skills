[CmdletBinding()]
param(
    [Parameter(Mandatory)][string] $SourceObsRoot,
    [Parameter(Mandatory)][string] $PluginRoot,
    [Parameter(Mandatory)][string] $TestRoot,
    [Parameter(Mandatory)][string] $PluginName,
    [switch] $Apply
)
$ErrorActionPreference = 'Stop'
$source = (Resolve-Path -LiteralPath $SourceObsRoot).Path
$plugin = (Resolve-Path -LiteralPath $PluginRoot).Path
$target = [IO.Path]::GetFullPath($TestRoot)
if ($target -eq [IO.Path]::GetPathRoot($target) -or $target -eq $source) { throw 'TestRoot must be a distinct, non-root disposable directory.' }
$plan = [ordered]@{ source_obs_root=$source; plugin_root=$plugin; test_root=$target; plugin_name=$PluginName; apply=[bool]$Apply }
if (-not $Apply) { $plan | ConvertTo-Json; exit 0 }
if (Test-Path -LiteralPath $target) { throw "TestRoot already exists: $target" }
Copy-Item -LiteralPath $source -Destination $target -Recurse
$dllSource = Join-Path $plugin 'bin\64bit'
$dataSource = Join-Path $plugin 'data'
if (-not (Test-Path -LiteralPath $dllSource) -or -not (Test-Path -LiteralPath $dataSource)) { throw 'PluginRoot must contain bin\64bit and data.' }
$dllTarget = Join-Path $target 'obs-plugins\64bit'
$dataTarget = Join-Path $target "data\obs-plugins\$PluginName"
$targetRoot = [IO.Path]::GetFullPath($target).TrimEnd('\') + '\'
$dataTargetFull = [IO.Path]::GetFullPath($dataTarget)
if (-not $dataTargetFull.StartsWith($targetRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Resolved plugin data target escapes the disposable host.'
}
if (Test-Path -LiteralPath $dataTargetFull) {
    Remove-Item -LiteralPath $dataTargetFull -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $dllTarget,$dataTargetFull | Out-Null
Copy-Item -Path (Join-Path $dllSource '*') -Destination $dllTarget -Recurse -Force
Copy-Item -Path (Join-Path $dataSource '*') -Destination $dataTargetFull -Recurse -Force
New-Item -ItemType Directory -Force -Path (Join-Path $target 'config\obs-studio') | Out-Null
$portableMarker = Join-Path $target 'portable_mode.txt'
New-Item -ItemType File -Path $portableMarker -Force | Out-Null
$plan.launch_command = (Join-Path $target 'bin\64bit\obs64.exe') + ' --portable --disable-updater'
$plan.websocket_policy = 'Before launch, require authentication and verify the listener is bound only to 127.0.0.1 or ::1.'
$plan | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $target 'codex-test-host.json') -Encoding UTF8
$plan | ConvertTo-Json
