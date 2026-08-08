[CmdletBinding()]
param([Parameter(Mandatory)][string] $Path, [switch] $Json)
$ErrorActionPreference = 'Stop'
try {
    $resolved = (Resolve-Path -LiteralPath $Path).Path
    $bytes = [IO.File]::ReadAllBytes($resolved)
    if ($bytes.Length -lt 64 -or $bytes[0] -ne 0x4D -or $bytes[1] -ne 0x5A) { throw 'File is not a valid DOS/PE image.' }
    $peOffset = [BitConverter]::ToInt32($bytes, 0x3C)
    if ($peOffset -lt 0 -or $peOffset + 6 -gt $bytes.Length) { throw 'Invalid PE header offset.' }
    if ($bytes[$peOffset] -ne 0x50 -or $bytes[$peOffset+1] -ne 0x45 -or $bytes[$peOffset+2] -ne 0 -or $bytes[$peOffset+3] -ne 0) { throw 'PE signature is missing.' }
    $machine = [BitConverter]::ToUInt16($bytes, $peOffset + 4)
    $result = [ordered]@{ path=$resolved; machine=('0x{0:X4}' -f $machine); architecture=$(if($machine -eq 0x8664){'x64'}else{'unsupported'}); sha256=(Get-FileHash -LiteralPath $resolved -Algorithm SHA256).Hash; passed=($machine -eq 0x8664); error=$null }
} catch {
    $result = [ordered]@{ path=$Path; machine=$null; architecture='invalid'; sha256=$null; passed=$false; error=$_.Exception.Message }
}
if ($Json) { $result | ConvertTo-Json } elseif ($result.passed) { "{0}: {1} ({2})" -f $result.architecture,$result.path,$result.machine } else { "failed: {0}: {1}" -f $result.path,$result.error }
if (-not $result.passed) { exit 1 }
