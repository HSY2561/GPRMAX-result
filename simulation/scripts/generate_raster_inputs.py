"""Generate line-by-line gprMax inputs for a raster scan on face A."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def write_inputs(grid_name: str, dx: float, y_start: float, y_stop: float, *, lines_dir: Path) -> dict:
    y_values = [round(y_start + i * 0.1, 6) for i in range(int(round((y_stop - y_start) / 0.1)) + 1)]
    lines_dir.mkdir(parents=True, exist_ok=True)
    geometry = f"simulation/geometry_{grid_name}/geometry.h5"
    inputs = []
    for line_no, y in enumerate(y_values, start=1):
        line_dir = lines_dir / f"line_{line_no:03d}"
        line_dir.mkdir(parents=True, exist_ok=True)
        text = f"""#title: Dongzhi-Nan raster line {line_no:03d} ({grid_name})\n#domain: 3.400 2.400 0.800\n#dx_dy_dz: {dx:.3f} {dx:.3f} {dx:.3f}\n#time_window: 15e-9\n\n#waveform: ricker 1 2.5e9 radar_pulse\n#hertzian_dipole: x 3.100 {y:.3f} 0.550 radar_pulse\n#rx: 3.054 {y:.3f} 0.550\n#src_steps: -0.100 0 0\n#rx_steps: -0.100 0 0\n\n#geometry_objects_read: 0.100 0.100 0.100 {geometry} materials y\n"""
        input_path = line_dir / "input.in"
        input_path.write_text(text, encoding="ascii")
        inputs.append({"line": line_no, "y_m": y, "input": str(input_path.relative_to(ROOT))})
    manifest = {
        "grid": grid_name,
        "dx_m": dx,
        "surface": "A face",
        "coordinate_system": {"X": "length", "Y": "bottom-to-top line direction", "Z": "thickness"},
        "geometry_insert_p1_m": [0.1, 0.1, 0.1],
        "antenna_height_above_A_m": 0.05,
        "polarisation": "x (tangential to A face; Z is propagation/depth direction)",
        "tx_rx_separation_m": 0.046,
        "trace_spacing_m": 0.1,
        "traces_per_line": 31,
        "tx_start_m": [3.10, y_start, 0.55],
        "rx_start_m": [3.054, y_start, 0.55],
        "x_step_m": -0.1,
        "line_step_y_m": 0.1,
        "path_order": "right-to-left along X, then bottom-to-top along Y",
        "lines": inputs,
    }
    (lines_dir / "raster_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return manifest


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", choices=["5mm", "20mm"], required=True)
    ap.add_argument("--y-start", type=float, required=True)
    ap.add_argument("--y-stop", type=float, required=True)
    args = ap.parse_args()
    dx = 0.005 if args.grid == "5mm" else 0.02
    write_inputs(args.grid, dx, args.y_start, args.y_stop, lines_dir=ROOT / "simulation" / "raster_scan" / args.grid)
