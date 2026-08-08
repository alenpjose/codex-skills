[CmdletBinding()]
param([Parameter(Mandatory)][string] $Path, [Parameter(Mandatory)][string] $PluginName, [switch] $Json)
$ErrorActionPreference = 'Stop'
function Get-RelativePath([string] $BasePath, [string] $FullPath) {
    $base = [Uri]([IO.Path]::GetFullPath($BasePath).TrimEnd('\') + '\')
    $target = [Uri][IO.Path]::GetFullPath($FullPath)
    return [Uri]::UnescapeDataString($base.MakeRelativeUri($target).ToString()).Replace('/','\')
}
$resolved = (Resolve-Path -LiteralPath $Path).Path
$temp = $null
try {
    if ([IO.Path]::GetExtension($resolved) -ieq '.zip') {
        $temp = Join-Path ([IO.Path]::GetTempPath()) ("obs-package-" + [guid]::NewGuid().ToString('N'))
        Expand-Archive -LiteralPath $resolved -DestinationPath $temp
        $root = $temp
    } else { $root = $resolved }
    if (-not (Test-Path -LiteralPath (Join-Path $root 'bin'))) {
        $dirs = @(Get-ChildItem -LiteralPath $root -Directory)
        if ($dirs.Count -eq 1) { $root = $dirs[0].FullName }
    }
    $files = @(Get-ChildItem -LiteralPath $root -Recurse -File)
    $relative = @($files | ForEach-Object { (Get-RelativePath $root $_.FullName).Replace('\','/') })
    $dll = "bin/64bit/$PluginName.dll"
    $errors = @()
    if ($relative -notcontains $dll) { $errors += "missing $dll" }
    if (-not ($relative | Where-Object { $_ -like 'data/*' })) { $errors += 'missing data runtime tree' }
    if (-not ($relative | Where-Object { [IO.Path]::GetFileName($_) -match '^LICENSE(?:\..*)?$' })) { $errors += 'missing LICENSE file' }
    if (-not ($relative | Where-Object { [IO.Path]::GetFileName($_) -match 'NOTICE' })) { $errors += 'missing notice or third-party acknowledgement file' }
    if (-not ($relative | Where-Object { [IO.Path]::GetFileName($_) -match '^README(?:\..*)?$' })) { $errors += 'missing minimal README file' }
    $forbidden = @($relative | Where-Object { $_ -match '(^|/)(\.git|\.github|tests?|coverage|node_modules|__pycache__|build[^/]*)(/|$)|\.(pdb|pyc|obj|lib|exp|pem|p12|key)$|(^|/)\.env' })
    if ($forbidden) { $errors += "forbidden files: $($forbidden -join ', ')" }
    $result = [ordered]@{ path=$resolved; root=$root; plugin=$PluginName; file_count=$files.Count; files=$relative; errors=$errors; passed=($errors.Count -eq 0) }
    if ($Json) { $result | ConvertTo-Json -Depth 5 } else { "package {0}: {1} files; {2}" -f $(if($result.passed){'passed'}else{'failed'}),$files.Count,($errors -join '; ') }
    if (-not $result.passed) { exit 1 }
} finally { if ($temp -and (Test-Path -LiteralPath $temp)) { Remove-Item -LiteralPath $temp -Recurse -Force } }
