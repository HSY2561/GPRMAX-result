"""Plot and quantify the X/Ex versus Y/Ey single-trace diagnostic."""
from __future__ import annotations

import json
from pathlib import Path

import h5py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "simulation" / "polarization_check"
OUT = ROOT / "simulation" / "results" / "polarization_check"


def read_trace(name: str, component: str) -> tuple[np.ndarray, float]:
    with h5py.File(SRC / name, "r") as h5:
        return np.asarray(h5["rxs"]["rx1"][component][:], dtype=float), float(h5.attrs["dt"])


def window_metrics(signal: np.ndarray, time_ns: np.ndarray) -> dict:
    result = {"max_abs": float(np.max(np.abs(signal))), "rms": float(np.sqrt(np.mean(signal * signal))), "windows_ns": {}}
    for name, lo, hi in (("0_1ns", 0, 1), ("1_3ns", 1, 3), ("3_8ns", 3, 8), ("8_15ns", 8, 15)):
        mask = (time_ns >= lo) & (time_ns < hi)
        result["windows_ns"][name] = {"max_abs": float(np.max(np.abs(signal[mask]))), "rms": float(np.sqrt(np.mean(signal[mask] * signal[mask])))}
    return result


def main() -> None:
    x, dt = read_trace("x_polarization_5mm.h5", "Ex")
    y, _ = read_trace("y_polarization_5mm.h5", "Ey")
    time_ns = np.arange(x.size) * dt * 1e9
    OUT.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(12, 6), dpi=180)
    ax.plot(time_ns, x, label="X-polarized / Ex", linewidth=1.0)
    ax.plot(time_ns, y, label="Y-polarized / Ey", linewidth=1.0)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Field amplitude")
    ax.set_title("5 mm single A-scan polarization comparison, Tx/Rx=46 mm")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "polarization_comparison_linear.jpg", dpi=200, format="jpg", pil_kwargs={"quality": 95})
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 6), dpi=180)
    ax.plot(time_ns, x / (np.max(np.abs(x)) or 1), label="X/Ex normalized", linewidth=1.0)
    ax.plot(time_ns, y / (np.max(np.abs(y)) or 1), label="Y/Ey normalized", linewidth=1.0)
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Normalized amplitude")
    ax.set_title("Normalized polarization comparison")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "polarization_comparison_normalized.jpg", dpi=200, format="jpg", pil_kwargs={"quality": 95})
    plt.close(fig)

    metrics = {
        "X_Ex": window_metrics(x, time_ns),
        "Y_Ey": window_metrics(y, time_ns),
        "grid": "5mm",
        "tx_m": [1.55, 1.1, 0.55],
        "rx_m": [1.504, 1.1, 0.55],
        "tx_rx_separation_m": 0.046,
        "frequency_hz": 2.5e9,
        "time_window_s": float(time_ns[-1] * 1e-9),
        "interpretation": "X/Ex and Y/Ey are diagnostic ideal-polarization comparisons; actual CK-2500 polarization remains to be calibrated.",
    }
    (OUT / "polarization_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
