"""Process completed global Ex radargrams.

Pipeline order: dewow -> Butterworth bandpass -> background removal ->
moderate time gain.  The script keeps the raw numbered NPZ files unchanged and
writes processed matrices and radargrams under results/global_10mm/processed.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import uniform_filter1d
from scipy.signal import butter, sosfiltfilt


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "simulation" / "results" / "global_10mm"
OUT = RESULTS / "processed"
TIME_WINDOW_NS = 10.0
REFERENCE_BAND_GHZ = (0.25, 2.60)
FFT_BAND_GHZ = (2.40, 6.60)  # rounded 5-95% power band measured from current data
GAIN_END = 2.5  # gain at 10 ns; moderate quadratic gain


def load_current() -> np.ndarray:
    paths = sorted(RESULTS.glob("line_*_Ex.npz"))
    if not paths:
        raise SystemExit("no completed global_10mm NPZ results found")
    return np.concatenate([np.load(p)["Ex"].astype(np.float64) for p in paths], axis=0)


def sampling(data: np.ndarray) -> tuple[float, np.ndarray]:
    dt = TIME_WINDOW_NS * 1e-9 / max(data.shape[1] - 1, 1)
    return dt, np.arange(data.shape[1], dtype=np.float64) * dt * 1e9


def dewow(data: np.ndarray, window_ns: float, dt: float) -> np.ndarray:
    size = max(3, int(round(window_ns * 1e-9 / dt)))
    if size % 2 == 0:
        size += 1
    return data - uniform_filter1d(data, size=size, axis=1, mode="nearest")


def bandpass(data: np.ndarray, band_ghz: tuple[float, float], dt: float) -> np.ndarray:
    fs = 1.0 / dt
    wn = [band_ghz[0] * 1e9 / (fs / 2), band_ghz[1] * 1e9 / (fs / 2)]
    sos = butter(4, wn, btype="bandpass", output="sos")
    return sosfiltfilt(sos, data, axis=1)


def remove_background(data: np.ndarray, method: str) -> np.ndarray:
    if method == "mean":
        background = np.mean(data, axis=0, keepdims=True)
    elif method == "median":
        background = np.median(data, axis=0, keepdims=True)
    else:
        raise ValueError(method)
    return data - background


def time_gain(data: np.ndarray, time_ns: np.ndarray) -> np.ndarray:
    u = np.clip(time_ns / TIME_WINDOW_NS, 0.0, 1.0)
    gain = 1.0 + (GAIN_END - 1.0) * u * u
    return data * gain[None, :]


def radargram(ax, data: np.ndarray, title: str, time_max: float = TIME_WINDOW_NS) -> None:
    vmax = float(np.percentile(np.abs(data), 99.5)) or 1.0
    ax.imshow(data.T, aspect="auto", cmap="seismic", vmin=-vmax, vmax=vmax,
              extent=[0, 3, time_max, 0], origin="upper")
    ax.set_xlabel("Scan distance from right start (m)")
    ax.set_ylabel("Time (ns)")
    ax.set_title(title, fontsize=9)


def save_panel(path: Path, items: list[tuple[str, np.ndarray]], time_max: float = TIME_WINDOW_NS) -> None:
    fig, axes = plt.subplots(1, len(items), figsize=(5.4 * len(items), 6.2), dpi=150, squeeze=False)
    for ax, (title, data) in zip(axes[0], items):
        radargram(ax, data, title, time_max)
    fig.tight_layout()
    fig.savefig(path, pil_kwargs={"quality": 92})
    plt.close(fig)


def fft_summary(data: np.ndarray, dt: float) -> dict:
    n = data.shape[1]
    freq = np.fft.rfftfreq(n, dt)
    tapered = (data - data.mean(axis=1, keepdims=True)) * np.hanning(n)[None, :]
    spectrum = np.abs(np.fft.rfft(tapered, axis=1)).mean(axis=0)
    smooth = np.convolve(spectrum, np.ones(7) / 7, mode="same")
    power = smooth * smooth
    cumulative = np.cumsum(power) / np.sum(power)
    p05 = float(freq[np.searchsorted(cumulative, 0.05)] / 1e9)
    p95 = float(freq[np.searchsorted(cumulative, 0.95)] / 1e9)
    mask = (freq >= 0.1e9) & (freq <= 10e9)
    peak = float(freq[mask][np.argmax(smooth[mask])] / 1e9)
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=150)
    ax.plot(freq / 1e9, smooth / np.max(smooth), color="black", linewidth=1.1)
    ax.axvspan(*REFERENCE_BAND_GHZ, color="tab:blue", alpha=0.18, label="reference 0.25–2.60 GHz")
    ax.axvspan(*FFT_BAND_GHZ, color="tab:orange", alpha=0.18, label="FFT-derived 2.40–6.60 GHz")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("Frequency (GHz)")
    ax.set_ylabel("Normalized mean amplitude")
    ax.set_title(f"Current Ex FFT spectrum | peak {peak:.2f} GHz | 5–95% power: {p05:.2f}–{p95:.2f} GHz")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(OUT / "current_Ex_fft_spectrum.jpg", pil_kwargs={"quality": 92})
    plt.close(fig)
    return {"peak_frequency_GHz": peak, "power_05_GHz": p05, "power_95_GHz": p95,
            "sample_count": n, "dt_s": dt}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    paths = sorted(RESULTS.glob("line_*_Ex.npz"))
    all_data = load_current()
    dt, time_ns = sampling(all_data)
    fft = fft_summary(all_data, dt)

    final_manifest = {"processing": {"dewow_windows_ns": [1.0, 1.5, 2.0],
                                      "reference_band_GHz": REFERENCE_BAND_GHZ,
                                      "fft_derived_band_GHz": FFT_BAND_GHZ,
                                      "background_methods": ["mean", "median"],
                                      "gain": "1 + 1.5*(t/10ns)^2", "order": "dewow -> bandpass -> background -> gain"},
                      "fft_summary": fft, "processed_lines": []}

    for path in paths:
        line_no = int(path.stem.split("_")[1])
        raw = np.load(path)["Ex"].astype(np.float64)
        ref = bandpass(dewow(raw, 1.5, dt), REFERENCE_BAND_GHZ, dt)
        adjusted = bandpass(dewow(raw, 1.5, dt), FFT_BAND_GHZ, dt)
        mean_bg = time_gain(remove_background(adjusted, "mean"), time_ns)
        median_bg = time_gain(remove_background(adjusted, "median"), time_ns)
        final = median_bg

        np.savez_compressed(OUT / f"line_{line_no:03d}_processed_Ex.npz", Ex=final,
                            time_ns=time_ns, scan_distance_m=np.arange(raw.shape[0]) * 0.01,
                            y_m=np.float32(0.1 + (line_no - 1) * 0.1),
                            dewow_window_ns=1.5, band_low_GHz=FFT_BAND_GHZ[0],
                            band_high_GHz=FFT_BAND_GHZ[1], background_method="median",
                            gain_end=np.float32(GAIN_END))
        fig, ax = plt.subplots(figsize=(12, 7), dpi=150)
        radargram(ax, final, f"Processed line {line_no:03d} | 1.5 ns | {FFT_BAND_GHZ[0]:.2f}–{FFT_BAND_GHZ[1]:.2f} GHz | median background | gain")
        fig.tight_layout(); fig.savefig(OUT / f"line_{line_no:03d}_processed_Ex.jpg", pil_kwargs={"quality": 92}); plt.close(fig)

        if line_no == 1:
            dewow_items = []
            for w in (1.0, 1.5, 2.0):
                d = time_gain(remove_background(bandpass(dewow(raw, w, dt), FFT_BAND_GHZ, dt), "median"), time_ns)
                dewow_items.append((f"Dewow {w:.1f} ns", d))
            save_panel(OUT / "line_001_dewow_compare.jpg", dewow_items)
            save_panel(OUT / "line_001_band_compare.jpg", [("Reference 0.25–2.60 GHz", time_gain(remove_background(ref, "median"), time_ns)),
                                                               (f"FFT-derived {FFT_BAND_GHZ[0]:.2f}–{FFT_BAND_GHZ[1]:.2f} GHz", final)])
            save_panel(OUT / "line_001_background_compare.jpg", [("Mean background", mean_bg), ("Median background", median_bg)])
        final_manifest["processed_lines"].append(line_no)

    (OUT / "processing_manifest.json").write_text(json.dumps(final_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(final_manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
