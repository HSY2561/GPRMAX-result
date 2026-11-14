"""Run all generated raster lines through the CUDA gprMax wrapper."""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", required=True, help="Name of a generated raster_scan subdirectory")
    ap.add_argument("--ntraces", type=int, default=301, help="Number of traces per line")
    ap.add_argument("--line-start", type=int, default=1)
    ap.add_argument("--line-end", type=int, default=21)
    ap.add_argument("--skip-complete", action="store_true")
    args = ap.parse_args()
    raster = ROOT / "simulation" / "raster_scan" / args.grid
    lines = sorted(
        p for p in raster.glob("line_*/input.in")
        if args.line_start <= int(p.parent.name.split("_")[1]) <= args.line_end
    )
    for input_path in lines:
        if args.skip_complete and all((input_path.parent / f"input{i}.h5").exists() for i in range(1, args.ntraces + 1)):
            print(f"skip complete {input_path.parent.name}", flush=True)
            continue
        command = f'simulation\\run_gpu.cmd {input_path.relative_to(ROOT)} -n {args.ntraces} -gpu 0 --allow-underresolved'
        log_path = input_path.parent / "run.log"
        print(f"running {input_path.parent.name}", flush=True)
        with log_path.open("w", encoding="utf-8", errors="replace") as log:
            result = subprocess.run(["cmd", "/d", "/c", command], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=False)
        if result.returncode != 0:
            raise SystemExit(f"raster line failed: {input_path} (exit {result.returncode}); see {log_path}")
    print(f"completed {len(lines)} raster lines for {args.grid}")


if __name__ == "__main__":
    main()
