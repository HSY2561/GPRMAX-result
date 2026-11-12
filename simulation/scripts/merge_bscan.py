from __future__ import annotations

import argparse
import json
from pathlib import Path

import h5py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", type=Path, required=True)
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--ntraces", type=int, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--output-stem", default="current_model_20mm_bscan")
    args = ap.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    traces = []
    dt = None
    for i in range(1, args.ntraces + 1):
        path = args.input_dir / f"{args.prefix}{i}.h5"
        with h5py.File(path, "r") as h5:
            traces.append(np.asarray(h5["rxs"]["rx1"]["Ez"][:], dtype=np.float32))
            if dt is None:
                dt = float(h5.attrs["dt"])
    data = np.column_stack(traces)
    np.savez_compressed(args.output_dir / f"{args.output_stem}_Ez.npz", Ez=data, dt_s=dt)
    scale = float(np.max(np.abs(data))) or 1.0
    png = args.output_dir / f"{args.output_stem}_Ez.png"
    plt.figure(figsize=(12, 5), facecolor="white")
    plt.imshow(data, extent=[0, data.shape[1] - 1, data.shape[0] * dt * 1e9, 0], aspect="auto", interpolation="nearest", cmap="seismic", vmin=-scale, vmax=scale)
    plt.xlabel("Trace index (100 mm step)")
    plt.ylabel("Time (ns)")
    plt.colorbar(label="Ez")
    plt.tight_layout()
    plt.savefig(png, dpi=180)
    plt.close()
    metadata = {
        "component": "Ez",
        "ntraces": args.ntraces,
        "trace_spacing_m": 0.1,
        "source_start_x_m": 0.3,
        "receiver_start_x_m": 0.34,
        "scan_direction": "X / slab length",
        "dt_s": dt,
        "samples_per_trace": int(data.shape[0]),
        "time_window_s": float(data.shape[0] * dt),
        "source_files": [f"{args.prefix}{i}.h5" for i in range(1, args.ntraces + 1)],
        "grid_warning": "Run used --allow-underresolved because the finite-conductivity steel approximation is formally under-resolved; review before quantitative use.",
    }
    (args.output_dir / f"{args.output_stem}_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"shape": list(data.shape), "dt_s": dt, "png": str(png)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
