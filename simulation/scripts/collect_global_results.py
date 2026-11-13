"""Collect numbered global raster results and remove transient per-trace HDF5.

Each completed line becomes one compact NPZ/JPG pair.  The raw gprMax files
are intentionally transient: they are deleted only after all 601 traces for a
line have been read successfully.
"""
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
GRID = ROOT / "simulation" / "raster_scan" / "global_10mm"
OUT = ROOT / "simulation" / "results" / "global_10mm"
NTRACES = 301
NLINES = 21


def line_y(line_no: int) -> float:
    return round(0.1 + (line_no - 1) * 0.1, 3)


def read_trace(path: Path) -> np.ndarray:
    with h5py.File(path, "r") as h5:
        return np.asarray(h5["rxs"]["rx1"]["Ex"], dtype=np.float32)


def collect_line(line_no: int, delete_h5: bool = True) -> bool:
    line_dir = GRID / f"line_{line_no:03d}"
    paths = [line_dir / f"input{i}.h5" for i in range(1, NTRACES + 1)]
    if not all(p.exists() for p in paths):
        return False
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / f"line_{line_no:03d}_Ex.npz"
    if target.exists():
        return True

    traces = np.stack([read_trace(p) for p in paths], axis=0)
    x_tx = 3.1 - np.arange(NTRACES, dtype=np.float32) * 0.01
    x_rx = x_tx - 0.046
    t_ns = np.arange(traces.shape[1], dtype=np.float32)  # overwritten below if available
    # gprMax output uses the same CFL time step for every trace.  The time
    # axis is retained as sample index here; the manifest records the 10 ns
    # window and the output sample count for reproducibility.
    np.savez_compressed(target, Ex=traces, tx_x_m=x_tx, rx_x_m=x_rx,
                        y_m=np.float32(line_y(line_no)), z_m=np.float32(0.5),
                        sample_index=t_ns)

    vmax = float(np.percentile(np.abs(traces), 99.5)) or 1.0
    fig, ax = plt.subplots(figsize=(12, 7), dpi=150)
    # Radargram convention requested by the user: distance is horizontal and
    # time is vertical, increasing downward from the antenna coupling pulse.
    ax.imshow(traces.T, aspect="auto", cmap="seismic", vmin=-vmax, vmax=vmax,
              extent=[0, 3, 10, 0], origin="upper")
    ax.set_xlabel("Distance along scan (m; right-to-left)")
    ax.set_ylabel("Time (ns)")
    ax.set_title(f"Dongzhi-Nan global raster 10mm line {line_no:03d} | Y={line_y(line_no):.3f} m | Ex")
    fig.tight_layout()
    fig.savefig(OUT / f"line_{line_no:03d}_Ex.jpg", pil_kwargs={"quality": 92})
    plt.close(fig)

    with (OUT / f"line_{line_no:03d}_trace_coordinates.csv").open("w", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp)
        writer.writerow(["line_no", "trace_no", "tx_x_m", "rx_x_m", "y_m", "z_m"])
        for i, (tx, rx) in enumerate(zip(x_tx, x_rx), 1):
            writer.writerow([line_no, i, f"{tx:.6f}", f"{rx:.6f}", f"{line_y(line_no):.6f}", "0.500000"])

    if delete_h5:
        for p in [line_dir / "input.h5", *paths]:
            p.unlink(missing_ok=True)
    return True


def update_manifest() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    completed = sorted(p.stem.split("_")[1] for p in OUT.glob("line_*_Ex.npz"))
    data = {
        "name": "Dongzhi-Nan global raster 10mm numbered results",
        "line_count_expected": NLINES,
        "traces_per_line": NTRACES,
        "line_spacing_m": 0.1,
        "trace_spacing_m": 0.01,
        "tx_rx_spacing_m": 0.046,
        "scan_direction": "right-to-left, bottom-to-top in A-face view",
        "completed_lines": [int(x) for x in completed],
        "completed_line_count": len(completed),
        "raw_trace_h5_policy": "deleted locally after successful line aggregation",
    }
    (OUT / "results_manifest.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--keep-h5", action="store_true")
    ap.add_argument("--interval", type=int, default=60)
    args = ap.parse_args()
    while True:
        made = 0
        for line_no in range(1, NLINES + 1):
            if collect_line(line_no, delete_h5=not args.keep_h5):
                made += 1
        manifest = update_manifest()
        print(json.dumps({"new_or_existing": made, **manifest}, ensure_ascii=False), flush=True)
        if args.once or manifest["completed_line_count"] == NLINES:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
