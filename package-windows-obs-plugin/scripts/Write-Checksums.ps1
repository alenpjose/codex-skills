[CmdletBinding()]
param([Parameter(Mandatory)][string[]] $Path, [string] $OutputPath, [switch] $Apply, [switch] $Json)
$ErrorActionPreference = 'Stop'
$files = foreach ($item in $Path) { Get-ChildItem -Path $item -File }
$rows = @($files | Sort-Object FullName -Unique | ForEach-Object { [ordered]@{ name=$_.Name; path=$_.FullName; sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant() } })
if ($OutputPath -and -not $Apply) { throw 'Pass -Apply to write OutputPath; omit OutputPath for a read-only preview.' }
if ($OutputPath) { $rows | ForEach-Object { '{0} *{1}' -f $_.sha256,$_.name } | Set-Content -LiteralPath $OutputPath -Encoding ascii }
if ($Json) { $rows | ConvertTo-Json } else { $rows | ForEach-Object { '{0} *{1}' -f $_.sha256,$_.name } }
