 $repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
function Wait-Complete($path) {
    while ($true) {
        if (Test-Path $path) {
            try { $m = Get-Content $path -Raw | ConvertFrom-Json; if ($m.completed_line_count -ge 21) { return } } catch {}
        }
        Start-Sleep -Seconds 60
    }
}
function Wait-Processed($path) {
    while ($true) {
        if (Test-Path $path) {
            try { $m = Get-Content $path -Raw | ConvertFrom-Json; if ($m.lines.Count -ge 21) { return } } catch {}
        }
        Start-Sleep -Seconds 60
    }
}
Wait-Complete (Join-Path $repo 'simulation/results/global_10mm_fixed520/results_manifest.json')
Wait-Complete (Join-Path $repo 'simulation/results/global_20mm_reference/results_manifest.json')
Wait-Processed (Join-Path $repo 'simulation/results/global_10mm_fixed520/processed/processing_manifest.json')
Wait-Processed (Join-Path $repo 'simulation/results/global_20mm_reference/processed/processing_manifest.json')
$archive = Join-Path $repo 'archives/Dongzhi-Nan_repaired_10mm_20mm_results_2026-11-14.zip'
& 'C:\env\gprmax_v4\Scripts\python.exe' -c @"
from pathlib import Path
import zipfile
root=Path(r'$repo')
archive=Path(r'$archive')
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for base in [root/'simulation/results/global_10mm_fixed520',root/'simulation/results/global_20mm_reference',root/'simulation/raster_scan/global_10mm_fixed520',root/'simulation/raster_scan/global_20mm_reference']:
        for p in base.rglob('*'):
            if not p.is_file() or p.name in {'collector.log','collector.err.log'}: continue
            if p.suffix == '.npz' and 'processed' in p.parts and not p.name.startswith('final_'): continue
            z.write(p,p.relative_to(root).as_posix())
    for p in [root/'reports/global_scan_repair_diagnosis.md',root/'README.md']:
        z.write(p,p.relative_to(root).as_posix())
"@
git -C $repo add simulation/results/global_10mm_fixed520 simulation/results/global_20mm_reference archives/Dongzhi-Nan_repaired_10mm_20mm_results_2026-11-14.zip reports/global_scan_repair_diagnosis.md
git -C $repo commit -m 'Publish repaired 10mm and 20mm processed results'
git -C $repo push origin main
