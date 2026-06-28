param(
    [string]$Port = "18792"
)

$ErrorActionPreference = "SilentlyContinue"

$procs = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -match "ttyd" -and $_.CommandLine -match $Port
}

if (-not $procs) {
    Write-Host "No ttyd process found for port $Port"
    exit 0
}

foreach ($p in $procs) {
    Write-Host "Stopping ttyd PID $($p.ProcessId)"
    Stop-Process -Id $p.ProcessId -Force
}
