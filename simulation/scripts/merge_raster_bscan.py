"""Merge line-by-line raster outputs into a 2-D Ez/Ex B-scan matrix."""
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
    ap.add_argument("--raster-dir", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--component", default="Ex")
    ap.add_argument("--ntraces", type=int, default=31)
    args = ap.parse_args()
    manifest = json.loads((args.raster_dir / "raster_manifest.json").read_text(encoding="utf-8"))
    line_dirs = sorted(args.raster_dir.glob("line_*"))
    matrices = []
    coordinates = []
    dt = None
    for line_dir in line_dirs:
        traces = []
        for i in range(1, args.ntraces + 1):
            path = line_dir / f"input{i}.h5"
            with h5py.File(path, "r") as h5:
                traces.append(np.asarray(h5["rxs"]["rx1"][args.component][:], dtype=np.float32))
                if dt is None:
                    dt = float(h5.attrs["dt"])
        # Columns are the right-to-left traces within one line.
        matrices.append(np.column_stack(traces))
        line_y = float(next(item["y_m"] for item in manifest["lines"] if item["line"] == int(line_dir.name.split("_")[-1])))
        for trace_index in range(args.ntraces):
            tx_x = 3.1 - trace_index * 0.1
            coordinates.append({"line": int(line_dir.name.split("_")[-1]), "y_m": line_y, "trace_in_line": trace_index + 1, "tx_x_m": tx_x, "rx_x_m": tx_x - manifest["tx_rx_separation_m"], "tx_y_m": line_y, "rx_y_m": line_y, "z_m": 0.55})
    if not matrices:
        raise RuntimeError(f"No line output found below {args.raster_dir}")
    data = np.column_stack(matrices)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"raster_{manifest['grid']}_{args.component}"
    np.savez_compressed(args.output_dir / f"{stem}.npz", data=data, dt_s=dt, line_y_m=np.asarray([x["y_m"] for x in manifest["lines"]]))
    scale = float(np.max(np.abs(data))) or 1.0
    fig, ax = plt.subplots(figsize=(13, 7), dpi=180)
    extent = [0, data.shape[1] - 1, data.shape[0] * dt * 1e9, 0]
    im = ax.imshow(data, extent=extent, aspect="auto", interpolation="nearest", cmap="seismic", vmin=-scale, vmax=scale)
    ax.set_title(f"Raster scan {manifest['grid']} ({args.component})")
    ax.set_xlabel("Raster trace index (line 1 right-to-left, then line 2 upward)")
    ax.set_ylabel("Time (ns)")
    fig.colorbar(im, ax=ax, label=args.component)
    fig.tight_layout()
    fig.savefig(args.output_dir / f"{stem}.png", dpi=180)
    plt.close(fig)
    (args.output_dir / f"{stem}_metadata.json").write_text(json.dumps({"manifest": str(args.raster_dir / 'raster_manifest.json'), "component": args.component, "line_count": len(line_dirs), "traces_per_line": args.ntraces, "trace_spacing_m": 0.1, "dt_s": dt, "path_order": manifest["path_order"], "trace_order": "each line right-to-left; lines bottom-to-top"}, ensure_ascii=False, indent=2), encoding="utf-8")
    with (args.output_dir / f"{stem}_trace_coordinates.csv").open("w", encoding="utf-8-sig") as f:
        f.write("line,y_m,trace_in_line,tx_x_m,rx_x_m,tx_y_m,rx_y_m,z_m\n")
        for row in coordinates:
            f.write(",".join(str(row[key]) for key in ["line", "y_m", "trace_in_line", "tx_x_m", "rx_x_m", "tx_y_m", "rx_y_m", "z_m"]) + "\n")
    print(json.dumps({"shape": list(data.shape), "lines": len(line_dirs), "traces_per_line": args.ntraces, "dt_s": dt}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
