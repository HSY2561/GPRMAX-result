param([int]$RepairRunnerPid = 5328)
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
while (Get-Process -Id $RepairRunnerPid -ErrorAction SilentlyContinue) { Start-Sleep -Seconds 30 }
$testLog = Join-Path $repo 'simulation/raster_scan/global_20mm_reference/validation.log'
cmd /d /c "simulation\run_gpu.cmd simulation\raster_scan\global_20mm_reference\line_001\input.in -n 1 -gpu 0 --allow-underresolved" *> $testLog
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Get-ChildItem -LiteralPath (Join-Path $repo 'simulation/raster_scan/global_20mm_reference') -Filter 'input*.h5' -Recurse -ErrorAction SilentlyContinue | Remove-Item -Force
$runnerLog = Join-Path $repo 'simulation/raster_scan/global_20mm_reference/runner.log'
$runnerErr = Join-Path $repo 'simulation/raster_scan/global_20mm_reference/runner.err.log'
$runner = Start-Process -FilePath 'C:\env\gprmax_v4\Scripts\python.exe' -ArgumentList @('simulation/scripts/run_raster_scan.py','--grid','global_20mm_reference','--ntraces','151','--skip-complete') -WorkingDirectory $repo -RedirectStandardOutput $runnerLog -RedirectStandardError $runnerErr -WindowStyle Hidden -PassThru
$collectorLog = Join-Path $repo 'simulation/results/global_20mm_reference/collector.log'
$collectorErr = Join-Path $repo 'simulation/results/global_20mm_reference/collector.err.log'
New-Item -ItemType Directory -Force -Path (Split-Path $collectorLog) | Out-Null
Start-Process -FilePath 'C:\env\gprmax_v4\Scripts\python.exe' -ArgumentList @('simulation/scripts/collect_scan_results.py','--grid','global_20mm_reference','--outdir','simulation/results/global_20mm_reference','--ntraces','151','--dx','0.02','--time-window-ns','10','--y0','0.2','--z','0.72','--line-count','21','--interval','60') -WorkingDirectory $repo -RedirectStandardOutput $collectorLog -RedirectStandardError $collectorErr -WindowStyle Hidden | Out-Null
Set-Content -LiteralPath (Join-Path $repo 'simulation/raster_scan/global_20mm_reference/chain_started.txt') -Value "runner_pid=$($runner.Id)"
