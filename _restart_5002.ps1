$pids = (Get-NetTCPConnection -LocalPort 5002 -State Listen -ErrorAction SilentlyContinue).OwningProcess
if ($pids) {
    foreach ($procId in $pids) {
        Write-Output ("killing PID " + $procId)
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
} else {
    Write-Output "no listener on 5002"
}
Start-Sleep -Seconds 2
$still = (Get-NetTCPConnection -LocalPort 5002 -State Listen -ErrorAction SilentlyContinue).OwningProcess
if ($still) { Write-Output ("STILL_LISTENING " + ($still -join ',')) } else { Write-Output "PORT_FREE" }
