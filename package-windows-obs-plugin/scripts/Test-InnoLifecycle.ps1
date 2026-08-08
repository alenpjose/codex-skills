[CmdletBinding()]
param(
    [Parameter(Mandatory)][string] $Installer,
    [Parameter(Mandatory)][string] $PackageRoot,
    [Parameter(Mandatory)][string] $TestRoot,
    [switch] $Apply
)
$ErrorActionPreference = 'Stop'
function Get-RelativePath([string] $BasePath, [string] $FullPath) {
    $base = [Uri]([IO.Path]::GetFullPath($BasePath).TrimEnd('\') + '\')
    $target = [Uri][IO.Path]::GetFullPath($FullPath)
    return [Uri]::UnescapeDataString($base.MakeRelativeUri($target).ToString()).Replace('/','\')
}
$installerPath = (Resolve-Path -LiteralPath $Installer).Path
$packagePath = (Resolve-Path -LiteralPath $PackageRoot).Path
$target = [IO.Path]::GetFullPath($TestRoot)
if ($target -eq [IO.Path]::GetPathRoot($target) -or $target -eq $packagePath) { throw 'TestRoot must be a distinct, non-root disposable path.' }
$plan = [ordered]@{ installer=$installerPath; package_root=$packagePath; test_root=$target; apply=[bool]$Apply }
if (-not $Apply) { $plan | ConvertTo-Json; exit 0 }
if (Get-Process obs64 -ErrorAction SilentlyContinue) { throw 'Close OBS before testing installation.' }
if (Test-Path -LiteralPath $target) { throw "TestRoot already exists: $target" }
New-Item -ItemType Directory -Path (Split-Path $target) -Force | Out-Null
$installLog = "$target-install.log"
$install = Start-Process -FilePath $installerPath -ArgumentList @('/CURRENTUSER','/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',"/DIR=$target","/LOG=$installLog") -Wait -PassThru
if ($install.ExitCode -ne 0) { throw "Installer exited $($install.ExitCode); inspect $installLog" }
$packageFiles = @(Get-ChildItem -LiteralPath $packagePath -Recurse -File)
foreach ($source in $packageFiles) {
    $relative = Get-RelativePath $packagePath $source.FullName
    $installed = Join-Path $target $relative
    if (-not (Test-Path -LiteralPath $installed -PathType Leaf)) { throw "Installer omitted $relative" }
    if ((Get-FileHash $source.FullName -Algorithm SHA256).Hash -ne (Get-FileHash $installed -Algorithm SHA256).Hash) { throw "Installed file differs: $relative" }
}
$uninstaller = Join-Path $target 'unins000.exe'
if (-not (Test-Path -LiteralPath $uninstaller)) { throw 'Generated uninstaller is missing.' }
$uninstallLog = "$target-uninstall.log"
$uninstall = Start-Process -FilePath $uninstaller -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',"/LOG=$uninstallLog") -Wait -PassThru
if ($uninstall.ExitCode -ne 0) { throw "Uninstaller exited $($uninstall.ExitCode); inspect $uninstallLog" }
$leftovers = @($packageFiles | Where-Object { Test-Path -LiteralPath (Join-Path $target (Get-RelativePath $packagePath $_.FullName)) })
$result = [ordered]@{ installer_exit=$install.ExitCode; uninstaller_exit=$uninstall.ExitCode; files_verified=$packageFiles.Count; runtime_leftovers=$leftovers.Count; passed=($leftovers.Count -eq 0); install_log=$installLog; uninstall_log=$uninstallLog }
$result | ConvertTo-Json
if (-not $result.passed) { exit 1 }
