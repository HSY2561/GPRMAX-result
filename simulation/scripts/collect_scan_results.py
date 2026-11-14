"""Collect completed numbered gprMax scan lines into compact results."""
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def collect_line(grid: str, outdir: Path, line_no: int, ntraces: int, dx: float,
                 time_window_ns: float, y0: float, z: float, delete_h5: bool) -> bool:
    line_dir = ROOT / "simulation" / "raster_scan" / grid / f"line_{line_no:03d}"
    paths = [line_dir / f"input{i}.h5" for i in range(1, ntraces + 1)]
    if not all(p.exists() for p in paths):
        return False
    outdir.mkdir(parents=True, exist_ok=True)
    target = outdir / f"line_{line_no:03d}_Ex.npz"
    if target.exists():
        return True
    traces = []
    for path in paths:
        with h5py.File(path, "r") as h5:
            traces.append(np.asarray(h5["rxs"]["rx1"]["Ex"], dtype=np.float32))
    data = np.stack(traces, axis=0)
    time_ns = np.linspace(0.0, time_window_ns, data.shape[1], dtype=np.float32)
    distance = np.arange(ntraces, dtype=np.float32) * dx
    y = y0 + (line_no - 1) * 0.1
    np.savez_compressed(target, Ex=data, time_ns=time_ns, scan_distance_m=distance,
                        y_m=np.float32(y), z_m=np.float32(z),
                        trace_count=np.int32(ntraces), trace_spacing_m=np.float32(dx))
    vmax = float(np.percentile(np.abs(data), 99.5)) or 1.0
    fig, ax = plt.subplots(figsize=(12, 7), dpi=150)
    ax.imshow(data.T, aspect="auto", cmap="seismic", vmin=-vmax, vmax=vmax,
              extent=[0.0, ntraces * dx, time_window_ns, 0.0], origin="upper")
    ax.set_xlabel("Distance along scan (m; right-to-left)")
    ax.set_ylabel("Time (ns)")
    ax.set_title(f"{grid} line {line_no:03d} | Y={y:.3f} m | raw Ex")
    fig.tight_layout()
    fig.savefig(outdir / f"line_{line_no:03d}_Ex.jpg", pil_kwargs={"quality": 92})
    plt.close(fig)
    with (outdir / f"line_{line_no:03d}_trace_coordinates.csv").open("w", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp)
        writer.writerow(["line_no", "trace_no", "tx_x_m", "rx_x_m", "y_m", "z_m"])
        for i in range(ntraces):
            tx = 3.1 - i * dx + (0.1 if "20mm" in grid else 0.0)
            writer.writerow([line_no, i + 1, f"{tx:.6f}", f"{tx - 0.046:.6f}", f"{y:.6f}", f"{z:.6f}"])
    if delete_h5:
        for path in [line_dir / "input.h5", *paths]:
            path.unlink(missing_ok=True)
    return True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--ntraces", type=int, required=True)
    ap.add_argument("--dx", type=float, required=True)
    ap.add_argument("--time-window-ns", type=float, default=10.0)
    ap.add_argument("--y0", type=float, required=True)
    ap.add_argument("--z", type=float, required=True)
    ap.add_argument("--line-count", type=int, default=21)
    ap.add_argument("--interval", type=int, default=60)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--keep-h5", action="store_true")
    args = ap.parse_args()
    outdir = ROOT / args.outdir
    while True:
        completed = []
        for line_no in range(1, args.line_count + 1):
            if collect_line(args.grid, outdir, line_no, args.ntraces, args.dx,
                            args.time_window_ns, args.y0, args.z, not args.keep_h5):
                completed.append(line_no)
        manifest = {
            "grid": args.grid, "line_count_expected": args.line_count,
            "traces_per_line": args.ntraces, "trace_spacing_m": args.dx,
            "time_window_ns": args.time_window_ns, "completed_lines": completed,
            "completed_line_count": len(completed),
            "axis_convention": "distance horizontal; time vertical, increasing downward",
            "raw_trace_h5_policy": "deleted after successful line aggregation",
        }
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "results_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(manifest, ensure_ascii=False), flush=True)
        if args.once or len(completed) == args.line_count:
            return
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
