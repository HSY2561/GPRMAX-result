"""Export the recorded A-scan and B-scan results as organized JPG images."""
from __future__ import annotations

import json
from pathlib import Path

import h5py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "simulation" / "results"


def save_ascan(h5_path: Path, out_path: Path, title: str) -> None:
    with h5py.File(h5_path, "r") as h5:
        signal = np.asarray(h5["rxs"]["rx1"]["Ez"][:], dtype=np.float64)
        dt = float(h5.attrs["dt"])
    time_ns = np.arange(signal.size) * dt * 1e9
    fig, ax = plt.subplots(figsize=(10, 5), dpi=180)
    ax.plot(time_ns, signal, color="#123b73", linewidth=0.9)
    ax.set_title(title)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Ez")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, format="jpg", dpi=200, pil_kwargs={"quality": 95})
    plt.close(fig)


def save_bscan(npz_path: Path, out_path: Path, title: str, spacing_m: float) -> None:
    with np.load(npz_path) as z:
        data = np.asarray(z["Ez"], dtype=np.float64)
        dt = float(z["dt_s"])
    scale = float(np.max(np.abs(data))) or 1.0
    fig, ax = plt.subplots(figsize=(12, 5), dpi=180)
    extent = [0, (data.shape[1] - 1) * spacing_m, data.shape[0] * dt * 1e9, 0]
    im = ax.imshow(data, extent=extent, aspect="auto", interpolation="nearest", cmap="seismic", vmin=-scale, vmax=scale)
    ax.set_title(title)
    ax.set_xlabel(f"Scan position (m), step={spacing_m:.3f} m")
    ax.set_ylabel("Time (ns)")
    fig.colorbar(im, ax=ax, label="Ez")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, format="jpg", dpi=200, pil_kwargs={"quality": 95})
    plt.close(fig)


def main() -> None:
    jobs = [
        (RESULTS / "20mm_bscan" / "current_model_20mm_ascan.h5", RESULTS / "20mm_ascan" / "current_model_20mm_ascan_Ez.jpg", "20 mm grid A-scan (Ez)"),
        (RESULTS / "5mm_ascan" / "current_model_5mm_ascan.h5", RESULTS / "5mm_ascan" / "current_model_5mm_ascan_Ez.jpg", "5 mm grid A-scan (Ez)"),
    ]
    for h5_path, out_path, title in jobs:
        save_ascan(h5_path, out_path, title)
    save_bscan(RESULTS / "20mm_bscan" / "current_model_20mm_bscan_Ez.npz", RESULTS / "20mm_bscan" / "current_model_20mm_bscan_Ez.jpg", "20 mm grid B-scan (Ez)", 0.1)
    save_bscan(RESULTS / "5mm_bscan" / "current_model_5mm_bscan_Ez.npz", RESULTS / "5mm_bscan" / "current_model_5mm_bscan_Ez.jpg", "5 mm grid B-scan (Ez)", 0.1)
    manifest = {
        "images": [
            "20mm_ascan/current_model_20mm_ascan_Ez.jpg",
            "20mm_bscan/current_model_20mm_bscan_Ez.jpg",
            "5mm_ascan/current_model_5mm_ascan_Ez.jpg",
            "5mm_bscan/current_model_5mm_bscan_Ez.jpg",
        ],
        "component": "Ez",
        "format": "JPEG",
        "scan_spacing_m": 0.1,
    }
    (RESULTS / "JPG_RESULTS.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
