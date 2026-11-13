param(
    [int]$RunnerPid = 10836,
    [int]$IntervalSeconds = 60
)

$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$python = 'C:\env\gprmax_v4\Scripts\python.exe'
$collector = Join-Path $repo 'simulation\scripts\collect_global_results.py'
$log = Join-Path $repo 'simulation\results\global_5mm\collector.log'
$err = Join-Path $repo 'simulation\results\global_5mm\collector.err.log'
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null

while ($true) {
    & $python $collector --once *>> $log
    git -C $repo add simulation/results/global_5mm
    $pending = git -C $repo diff --cached --name-only
    if ($pending) {
        git -C $repo commit -m 'Add numbered completed global raster results'
        git -C $repo push origin main *>> $log
    }
    $done = (Get-ChildItem -LiteralPath (Join-Path $repo 'simulation\results\global_5mm') -Filter 'line_*_Ex.npz' -ErrorAction SilentlyContinue | Measure-Object).Count
    if ($done -ge 21) { break }
    $runner = Get-Process -Id $RunnerPid -ErrorAction SilentlyContinue
    if (-not $runner) { break }
    Start-Sleep -Seconds $IntervalSeconds
}
