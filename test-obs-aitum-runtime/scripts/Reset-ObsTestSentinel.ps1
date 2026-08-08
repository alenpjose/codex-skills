[CmdletBinding()]
param(
    [Parameter(Mandatory)][string] $TestRoot,
    [switch] $Apply
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath $TestRoot).Path
if ($root -eq [IO.Path]::GetPathRoot($root)) { throw 'TestRoot cannot be a filesystem root.' }
$sentinel = [IO.Path]::GetFullPath((Join-Path $root 'config\obs-studio\.sentinel'))
$rootPrefix = $root.TrimEnd('\') + '\'
if (-not $sentinel.StartsWith($rootPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Resolved sentinel path escapes TestRoot.'
}
$running = @(Get-Process obs64 -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -and $_.Path.StartsWith($rootPrefix, [StringComparison]::OrdinalIgnoreCase)
})
if ($running.Count) { throw "OBS is still running from TestRoot (PID $($running.Id -join ', '))." }
$exists = Test-Path -LiteralPath $sentinel -PathType Leaf
$backup = if ($exists) { $sentinel + '.unclean-' + [DateTime]::UtcNow.ToString('yyyyMMddHHmmss') } else { $null }
$result = [ordered]@{ apply=[bool]$Apply; test_root=$root; sentinel=$sentinel; exists=$exists; backup=$backup }
if (-not $Apply -or -not $exists) { $result | ConvertTo-Json; exit 0 }
Move-Item -LiteralPath $sentinel -Destination $backup
$result.moved = $true
$result | ConvertTo-Json
