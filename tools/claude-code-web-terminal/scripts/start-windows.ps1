param(
    [string]$EnvFile = ".env"
)

$ErrorActionPreference = "Stop"

function Read-DotEnv($Path) {
    $map = @{}
    if (Test-Path $Path) {
        Get-Content $Path | ForEach-Object {
            $line = $_.Trim()
            if (-not $line -or $line.StartsWith('#')) { return }
            $idx = $line.IndexOf('=')
            if ($idx -lt 0) { return }
            $key = $line.Substring(0, $idx).Trim()
            $value = $line.Substring($idx + 1).Trim().Trim('"')
            $map[$key] = $value
        }
    }
    return $map
}

$config = Read-DotEnv $EnvFile
$projectDir = $config.PROJECT_DIR
if (-not $projectDir) { $projectDir = (Get-Location).Path }
$localHost = $config.LOCAL_HOST
if (-not $localHost) { $localHost = '127.0.0.1' }
$localPort = $config.LOCAL_PORT
if (-not $localPort) { $localPort = '18792' }
$shellCmd = $config.SHELL_CMD
if (-not $shellCmd) { $shellCmd = 'cmd.exe' }

$ttyd = (Get-Command ttyd -ErrorAction SilentlyContinue).Source
if (-not $ttyd) {
    $wingetPath = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages\tsl0922.ttyd_Microsoft.Winget.Source_8wekyb3d8bbwe\ttyd.exe'
    if (Test-Path $wingetPath) { $ttyd = $wingetPath }
}
if (-not $ttyd) {
    throw "ttyd not found. Install with: winget install --id tsl0922.ttyd"
}

Write-Host "Starting ttyd..." -ForegroundColor Green
Write-Host "  Project: $projectDir"
Write-Host "  URL:     http://${localHost}:${localPort}/"
Write-Host "  Shell:   $shellCmd"

$args = @('-i', $localHost, '-p', $localPort, '-W', '-w', $projectDir)
# Split only simple shell command; advanced users can edit this script.
$args += $shellCmd.Split(' ')

Start-Process -FilePath $ttyd -ArgumentList $args -WindowStyle Hidden
Start-Sleep -Seconds 2

try {
    $res = Invoke-WebRequest -UseBasicParsing -Uri "http://${localHost}:${localPort}/" -Method Head -TimeoutSec 5
    Write-Host "ttyd started: $($res.StatusCode)" -ForegroundColor Green
} catch {
    Write-Warning "ttyd may not have started yet: $($_.Exception.Message)"
}
