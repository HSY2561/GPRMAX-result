$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$python = 'C:\env\gprmax_v4\Scripts\python.exe'
function Wait-Complete($manifestPath) {
    while ($true) {
        if (Test-Path $manifestPath) {
            try { $m = Get-Content $manifestPath -Raw | ConvertFrom-Json; if ($m.completed_line_count -ge 21) { return } } catch {}
        }
        Start-Sleep -Seconds 60
    }
}
Wait-Complete (Join-Path $repo 'simulation/results/global_10mm_fixed520/results_manifest.json')
Wait-Complete (Join-Path $repo 'simulation/results/global_20mm_reference/results_manifest.json')
$log = Join-Path $repo 'simulation/results/processing_pipeline.log'
& $python simulation/scripts/process_scan_results.py --results simulation/results/global_10mm_fixed520 --outdir simulation/results/global_10mm_fixed520/processed *>> $log
& $python simulation/scripts/process_scan_results.py --results simulation/results/global_20mm_reference --outdir simulation/results/global_20mm_reference/processed *>> $log
