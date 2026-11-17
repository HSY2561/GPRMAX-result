"""Reproducible publication radargrams from the completed 21-line arrays.

No simulation arrays are changed. Signed Ex and vector magnitude are distinct
products. Every line shares one scale per product; no trace normalization,
gap filling, or additional spatial smoothing is applied here.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from scipy.signal import butter, sosfiltfilt

REPO = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPO / "simulation/results/latest_dynamic_21line"
DEFAULT_OUT = DEFAULT_SOURCE / "paper_grayscale"
PRODUCTS = ("raw_Ex", "grayscale_Ex_late_gain", "synthetic_magnitude_gray", "late_window_Ex")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_line(source: Path, number: int) -> dict:
    raw_path = source / f"line_{number:03d}_components.npz"
    proc_path = source / "processed" / f"line_{number:03d}" / "synthetic_amplitude.npz"
    with np.load(raw_path) as r, np.load(proc_path) as p:
        t = r["time_ns"].astype(np.float64)
        distance = r["scan_distance_m"].astype(np.float64)
        raw = r["Ex"].astype(np.float64)
        dt_seconds = float(np.median(np.diff(t))) * 1e-9
        sos = butter(4, [0.25e9, 2.60e9], btype="bandpass", fs=1 / dt_seconds, output="sos")
        # Reprocess the original gprMax component arrays. No rendered image
        # is ever read as an input, and no polarity is inferred from |E|.
        filtered = {}
        for component in ("Ex", "Ey", "Ez"):
            field = r[component].astype(np.float64)
            filtered[component] = sosfiltfilt(sos, field - field.mean(axis=1, keepdims=True), axis=1)
        ex = filtered["Ex"]
        gain = 1 + 5 * np.clip((t - 5) / 3, 0, 1) ** 2
        magnitude = np.sqrt(sum(np.square(filtered[c]) for c in filtered))
        assert raw.shape == ex.shape == magnitude.shape == (601, 521)
        assert np.isfinite(raw).all() and np.isfinite(ex).all() and np.isfinite(magnitude).all()
        assert np.all(np.diff(t) > 0) and np.all(np.diff(distance) > 0)
        return dict(number=number, time=t, distance=distance, y=float(r["y_m"]) - 0.1,
                    raw_Ex=raw, grayscale_Ex_late_gain=ex * gain[None, :],
                    synthetic_magnitude_gray=magnitude * gain[None, :],
                    late_window_Ex=ex * gain[None, :],
                    source_hashes={str(raw_path.relative_to(source)): sha256(raw_path),
                                   str(proc_path.relative_to(source)): sha256(proc_path)})


def limit_for(lines: list[dict], product: str) -> float:
    arrays = []
    for row in lines:
        values = row[product]
        if product == "late_window_Ex":
            values = values[:, (row["time"] >= 5) & (row["time"] <= 10)]
        elif product != "raw_Ex":
            # Exclude the strong direct wave only when estimating the display
            # clip. No time samples are deleted from the plotted data.
            values = values[:, (row["time"] >= 1.2) & (row["time"] <= 10)]
        arrays.append(np.abs(values).ravel())
    return float(np.percentile(np.concatenate(arrays), 99.5)) or 1.0


def plot(ax, row: dict, product: str, limit: float, crop=False):
    t, d = row["time"], row["distance"]
    dt, dd = np.median(np.diff(t)), np.median(np.diff(d))
    signed = product != "synthetic_magnitude_gray"
    im = ax.imshow(row[product].T / limit, origin="upper", aspect="auto", cmap="gray",
                   vmin=-1 if signed else 0, vmax=1, interpolation="none", rasterized=True,
                   extent=[d[0]-dd/2, d[-1]+dd/2, t[-1]+dt/2, t[0]-dt/2])
    ax.set_xlim(0, 3)
    ax.set_ylim(10, 5 if crop else 0)
    ax.set_xticks(np.arange(0, 3.01, .5))
    ax.set_yticks(np.arange(5, 10.01, 1) if crop else np.arange(0, 10.01, 2))
    ax.set_xlabel("Scan distance from right start (m)")
    ax.set_ylabel("Time (ns)")
    ax.tick_params(direction="out", width=.6, length=3)
    for spine in ax.spines.values():
        spine.set_linewidth(.6)
    return im


def save_figure(fig, stem: Path):
    stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(stem.with_suffix(".png"), dpi=600, facecolor="white")
    fig.savefig(stem.with_suffix(".pdf"), dpi=600, facecolor="white",
                metadata={"Creator": "Matplotlib; render_paper_grayscale.py"})
    # Actual single-channel PNG/JPG avoids incidental RGB colour in exports.
    with Image.open(stem.with_suffix(".png")) as png:
        gray = png.convert("L")
    gray.save(stem.with_suffix(".png"), dpi=(600, 600), optimize=True)
    preview = gray.resize((gray.width // 2, gray.height // 2), Image.Resampling.LANCZOS)
    preview.save(stem.with_suffix(".jpg"), quality=96, dpi=(300, 300))
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--only", type=int, help="Render one line using all-line scales for review")
    args = ap.parse_args()
    source, out = args.source.resolve(), args.out.resolve()
    rows = [load_line(source, i) for i in range(1, 22)]
    limits = {p: limit_for(rows, p) for p in PRODUCTS}
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                         "axes.titlesize": 9, "axes.labelsize": 9,
                         "xtick.labelsize": 8, "ytick.labelsize": 8,
                         "pdf.fonttype": 42, "ps.fonttype": 42,
                         "figure.facecolor": "white", "savefig.facecolor": "white"})
    captions = {"raw_Ex": "Raw signed Ex",
                "grayscale_Ex_late_gain": "Bandpass signed Ex | late-time gain",
                "synthetic_magnitude_gray": "Vector magnitude | late-time gain",
                "late_window_Ex": "Signed Ex | late-time detail (independent scale)"}
    selected = [r for r in rows if args.only is None or r["number"] == args.only]
    for row in selected:
        for product in PRODUCTS:
            fig, ax = plt.subplots(figsize=(7.2, 3.8), layout="constrained")
            im = plot(ax, row, product, limits[product], product == "late_window_Ex")
            ax.set_title(f"Line {row['number']:03d} (y = {row['y']:.2f} m) | {captions[product]}")
            cb = fig.colorbar(im, ax=ax, pad=.018, fraction=.035, aspect=25)
            cb.set_ticks([-1, 0, 1] if product != "synthetic_magnitude_gray" else [0, .5, 1])
            cb.set_label("Display amplitude / common clip level")
            cb.outline.set_linewidth(.5)
            save_figure(fig, out / f"line_{row['number']:03d}" / product)
        print(f"Rendered line {row['number']:03d}", flush=True)
    if args.only:
        return
    # A compact, consistently scaled figure for comparison across typical lines.
    fig, axes = plt.subplots(3, 2, figsize=(7.2, 8.4), layout="constrained")
    for label, no, ax in zip("abcdef", (3, 5, 8, 10, 15, 19), axes.ravel()):
        im = plot(ax, rows[no-1], "grayscale_Ex_late_gain", limits["grayscale_Ex_late_gain"])
        ax.set_title(f"({label}) Line {no:03d}, y = {rows[no-1]['y']:.2f} m")
        ax.set_xlabel("Distance (m)")
    cb = fig.colorbar(im, ax=axes.ravel().tolist(), pad=.015, fraction=.025, aspect=35)
    cb.set_label("Signed display amplitude / common clip level")
    cb.set_ticks([-1, 0, 1])
    save_figure(fig, out / "selected_lines_comparison")
    source_hashes = {k: v for row in rows for k, v in row["source_hashes"].items()}
    manifest = {"line_count": len(rows), "trace_count_per_line": 601,
                "samples_per_trace": 521, "source_hashes": source_hashes,
                "format": {"PNG": "600 dpi, 8-bit grayscale", "PDF": "vector text plus raster radar data",
                           "JPG": "300 dpi, 8-bit grayscale", "size_inches": [7.2, 3.8]},
                "primary_product": "grayscale_Ex_late_gain",
                "signed_products": "negative black; zero mid-gray; positive white",
                "magnitude_product": "sqrt(Ex^2+Ey^2+Ez^2), black zero to white maximum; no polarity",
                "clip": {"percentile": 99.5, "scope": "all 21 lines share one limit per product; raw uses full window, processed full-window displays estimate clip from 1.2-10 ns to prevent direct-wave domination, late detail uses 5-10 ns",
                         "absolute_limits": limits, "colorbar": "data divided by product clip limit; saturated beyond +/-1"},
                "gain": "saved gain: 1x before 5 ns; quadratic rise to 6x from 5 to 8 ns; 6x thereafter",
                "time_ns": [0, 10], "late_crop_ns": [5, 10], "distance_m": [0, 3],
                "time_sample_end_ns": float(rows[0]["time"][-1]),
                "data_policy": "raw/processed NPZ unchanged; no new per-trace normalization, smoothing or gap interpolation",
                "input_policy": "Original gprMax Ex/Ey/Ez arrays in line_###_components.npz; no JPG, PNG, or PDF is read as plotting input",
                "filter": "recomputed from original component fields: trace mean removed then 4th-order zero-phase Butterworth 0.25-2.60 GHz; no 1.5 ns Dewow applied",
                "late_window_scale": "independent common clip estimated only from 5-10 ns; not directly comparable to full-window shades"}
    (out / "render_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    with (out / "figure_index.csv").open("w", newline="", encoding="utf-8") as fp:
        w = csv.writer(fp)
        w.writerow(["line", "y_m", "main_JPG", "raw_JPG", "magnitude_JPG", "late_detail_JPG"])
        for row in rows:
            n = row["number"]
            w.writerow([n, f"{row['y']:.2f}", *[f"line_{n:03d}/{p}.jpg" for p in
                                                ("grayscale_Ex_late_gain", "raw_Ex", "synthetic_magnitude_gray", "late_window_Ex")]])
    # Check unchanged arrays before claiming a display-only conversion.
    for path, digest in source_hashes.items():
        assert sha256(source / path) == digest, f"Source changed during rendering: {path}"
    print(json.dumps({"lines": len(rows), "figures": 4*len(rows)+1, "limits": limits,
                      "source_arrays_unchanged": True}), flush=True)


if __name__ == "__main__":
    main()
