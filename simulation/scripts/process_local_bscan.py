"""Merge and process the local 5 mm B-scan.

Processing order: raw Ex -> 1.5 ns moving-average dewow -> 0.25-2.60 GHz
zero-phase Butterworth band-pass.
"""
from __future__ import annotations

import json
from pathlib import Path

import h5py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import uniform_filter1d
from scipy.signal import butter, sosfiltfilt


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "simulation" / "local_bscan"
OUT = ROOT / "simulation" / "results" / "local_bscan_5mm"


def load_traces() -> tuple[np.ndarray, float]:
    traces = []
    dt = None
    for i in range(1, 322):
        with h5py.File(SRC / f"local_bscan_5mm{i}.h5", "r") as h5:
            traces.append(np.asarray(h5["rxs"]["rx1"]["Ex"][:], dtype=np.float64))
            if dt is None:
                dt = float(h5.attrs["dt"])
    return np.column_stack(traces), float(dt)


def save_image(data: np.ndarray, dt: float, path: Path, title: str) -> None:
    scale = float(np.percentile(np.abs(data), 99.5)) or 1.0
    fig, ax = plt.subplots(figsize=(13, 6), dpi=180)
    extent = [0, 1.6, data.shape[0] * dt * 1e9, 0]
    im = ax.imshow(data, extent=extent, aspect="auto", interpolation="nearest", cmap="seismic", vmin=-scale, vmax=scale)
    ax.set_title(title)
    ax.set_xlabel("Local scan distance (m), right to left")
    ax.set_ylabel("Time (ns)")
    fig.colorbar(im, ax=ax, label="Ex")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200)
    fig.savefig(path.with_suffix(".jpg"), dpi=200, format="jpg", pil_kwargs={"quality": 95})
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    raw, dt = load_traces()
    fs = 1.0 / dt
    dewow_samples = max(3, int(round(1.5e-9 / dt)))
    dewow = raw - uniform_filter1d(raw, size=dewow_samples, axis=0, mode="nearest")
    sos = butter(4, [0.25e9, 2.60e9], btype="bandpass", fs=fs, output="sos")
    filtered = sosfiltfilt(sos, dewow, axis=0)
    np.savez_compressed(OUT / "local_bscan_5mm_raw_Ex.npz", Ex=raw, dt_s=dt)
    np.savez_compressed(OUT / "local_bscan_5mm_dewow_bandpass_Ex.npz", Ex=filtered, dt_s=dt)
    save_image(raw, dt, OUT / "local_bscan_5mm_raw_Ex.png", "Local B-scan 5 mm raw Ex")
    save_image(filtered, dt, OUT / "local_bscan_5mm_dewow_1p5ns_bandpass_0p25_2p60GHz_Ex.png", "Local B-scan 5 mm: dewow 1.5 ns + 0.25-2.60 GHz")
    x_tx = 2.8 - np.arange(321) * 0.005
    metadata = {
        "grid": "5mm",
        "local_region_m": {"x_min": 1.2, "x_max": 2.8, "y": 1.1, "z_surface": 0.5},
        "trace_count": 321,
        "trace_spacing_m": 0.005,
        "tx_start_m": [2.8, 1.1, 0.5],
        "rx_start_m": [2.754, 1.1, 0.5],
        "tx_rx_separation_m": 0.046,
        "x_step_m": -0.005,
        "component": "Ex",
        "dewow_window_s": 1.5e-9,
        "dewow_window_samples": dewow_samples,
        "bandpass_hz": [0.25e9, 2.60e9],
        "sampling_frequency_hz": fs,
        "time_window_s": float(raw.shape[0] * dt),
        "coordinates_tx_x_m": x_tx.tolist(),
    }
    (OUT / "local_bscan_5mm_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    np.savetxt(OUT / "local_bscan_5mm_trace_coordinates.csv", np.column_stack([np.arange(1, 322), x_tx, x_tx - 0.046, np.full(321, 1.1)]), delimiter=",", header="trace,tx_x_m,rx_x_m,y_m", comments="")
    print(json.dumps({"raw_shape": list(raw.shape), "dt_s": dt, "dewow_samples": dewow_samples, "bandpass_hz": [0.25e9, 2.60e9]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
