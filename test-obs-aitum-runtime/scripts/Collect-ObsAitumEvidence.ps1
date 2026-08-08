[CmdletBinding()]
param(
    [Parameter(Mandatory)][string] $TestRoot,
    [Parameter(Mandatory)][string] $OutputDir,
    [switch] $Apply
)
$ErrorActionPreference = 'Stop'
function Get-RelativePath([string] $BasePath, [string] $FullPath) {
    $base = [Uri]([IO.Path]::GetFullPath($BasePath).TrimEnd('\') + '\')
    $target = [Uri][IO.Path]::GetFullPath($FullPath)
    return [Uri]::UnescapeDataString($base.MakeRelativeUri($target).ToString()).Replace('/','\')
}
$root = (Resolve-Path -LiteralPath $TestRoot).Path
$output = [IO.Path]::GetFullPath($OutputDir)
$patterns = @('config\obs-studio\logs\*.txt','config\obs-studio\basic\*.ini','config\obs-studio\basic\scenes\*.json','config\obs-studio\basic\scenes\*.bak','config\obs-studio\basic\profiles\*\*.ini','config\obs-studio\basic\profiles\*\*.json','config\obs-studio\plugin_config\*\*.json','config\obs-studio\plugin_config\*\*.ini','test-results\*.png','test-results\*.json','test-results\*.log')
$files = foreach ($pattern in $patterns) { Get-ChildItem -Path (Join-Path $root $pattern) -File -ErrorAction SilentlyContinue }
$files = @($files | Sort-Object FullName -Unique)
$dllFiles = @(Get-ChildItem -LiteralPath (Join-Path $root 'obs-plugins\64bit') -Filter '*.dll' -File -ErrorAction SilentlyContinue)
$files += $dllFiles
$files = @($files | Sort-Object FullName -Unique)
$manifest = foreach ($file in $files) { [ordered]@{ source=$file.FullName; relative=(Get-RelativePath $root $file.FullName); sha256=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash } }
if (-not $Apply) { [ordered]@{ apply=$false; output=$output; files=$manifest } | ConvertTo-Json -Depth 5; exit 0 }
if ($output -eq [IO.Path]::GetPathRoot($output)) { throw 'OutputDir cannot be a filesystem root.' }
New-Item -ItemType Directory -Force -Path $output | Out-Null
foreach ($item in $manifest) { $dest=Join-Path $output $item.relative; New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null; Copy-Item -LiteralPath $item.source -Destination $dest }
[ordered]@{ apply=$true; output=$output; files=$manifest } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $output 'evidence-manifest.json') -Encoding UTF8
[ordered]@{ apply=$true; output=$output; files=$manifest } | ConvertTo-Json -Depth 5
