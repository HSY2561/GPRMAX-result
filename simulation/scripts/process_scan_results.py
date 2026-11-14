"""Generate reproducible radargram processing and hyperbola candidate reports."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import uniform_filter1d
from scipy.signal import butter, find_peaks, hilbert, sosfiltfilt

ROOT = Path(__file__).resolve().parents[2]


def dewow(x: np.ndarray, window_ns: float, time_ns: np.ndarray) -> np.ndarray:
    dt = float(np.median(np.diff(time_ns))) * 1e-9
    size = max(3, int(round(window_ns * 1e-9 / dt)))
    if size % 2 == 0:
        size += 1
    return x - uniform_filter1d(x, size=size, axis=1, mode="nearest")


def bandpass(x: np.ndarray, low: float, high: float, time_ns: np.ndarray) -> np.ndarray:
    dt = float(np.median(np.diff(time_ns))) * 1e-9
    fs = 1.0 / dt
    sos = butter(4, [low * 1e9 / (fs / 2), high * 1e9 / (fs / 2)], btype="bandpass", output="sos")
    return sosfiltfilt(sos, x, axis=1)


def remove_background(x: np.ndarray, method: str) -> np.ndarray:
    bg = np.mean(x, axis=0, keepdims=True) if method == "mean" else np.median(x, axis=0, keepdims=True)
    return x - bg


def gain(x: np.ndarray, time_ns: np.ndarray, end_gain: float = 2.5) -> np.ndarray:
    u = np.clip(time_ns / max(float(time_ns[-1]), 1e-9), 0, 1)
    return x * (1 + (end_gain - 1) * u[None, :] ** 2)


def save_radargram(path: Path, x: np.ndarray, distance: np.ndarray, time_ns: np.ndarray, title: str) -> None:
    vmax = float(np.percentile(np.abs(x), 99.5)) or 1.0
    fig, ax = plt.subplots(figsize=(12, 7), dpi=180)
    ax.imshow(x.T, aspect="auto", cmap="seismic", vmin=-vmax, vmax=vmax,
              extent=[float(distance[0]), float(distance[-1]), float(time_ns[-1]), 0], origin="upper")
    ax.set_xlabel("Distance along scan (m; right-to-left)")
    ax.set_ylabel("Time (ns)")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, pil_kwargs={"quality": 95})
    plt.close(fig)


def detect_hyperbolas(x: np.ndarray, distance: np.ndarray, time_ns: np.ndarray, outdir: Path, title: str) -> dict:
    envelope = np.abs(hilbert(x, axis=1))
    valid = (time_ns >= 0.8) & (time_ns <= time_ns[-1])
    score = np.max(envelope[:, valid], axis=1)
    smooth = uniform_filter1d(score, size=max(3, min(15, len(score) // 10)), mode="nearest")
    peaks, props = find_peaks(smooth, prominence=max(float(np.percentile(smooth, 75) - np.percentile(smooth, 25)), 1e-12), distance=max(3, len(score) // 30))
    rows = []
    for p in peaks:
        tidx = int(np.argmax(envelope[p, valid]))
        t = float(time_ns[np.flatnonzero(valid)[tidx]])
        rows.append({"trace_no": int(p + 1), "distance_m": float(distance[p]), "time_ns": t, "score": float(smooth[p])})
    with (outdir / "hyperbola_candidates.csv").open("w", newline="", encoding="utf-8") as fp:
        w = csv.DictWriter(fp, fieldnames=["trace_no", "distance_m", "time_ns", "score"]); w.writeheader(); w.writerows(rows)
    save_radargram(outdir / "hyperbola_overlay.jpg", x, distance, time_ns, title + " | candidate hyperbola centers")
    return {"candidate_count": len(rows), "candidates": rows}


def process_one(raw_path: Path, outdir: Path, line_no: int, low: float, high: float) -> dict:
    z = np.load(raw_path)
    raw = z["Ex"].astype(np.float64)
    time_ns = z["time_ns"].astype(np.float64)
    distance = z["scan_distance_m"].astype(np.float64)
    line_out = outdir / f"line_{line_no:03d}"; line_out.mkdir(parents=True, exist_ok=True)
    dw = dewow(raw, 1.5, time_ns)
    bp = bandpass(dw, low, high, time_ns)
    bg = remove_background(bp, "median")
    tg = gain(bg, time_ns)
    stages = {"raw": raw, "dewow_1p5ns": dw, "butterworth": bp, "background_removed": bg, "time_gain": tg, "final": tg}
    for name, data in stages.items():
        np.savez_compressed(line_out / f"{name}_Ex.npz", Ex=data.astype(np.float32), time_ns=time_ns.astype(np.float32), scan_distance_m=distance.astype(np.float32), y_m=z.get("y_m", np.nan), z_m=z.get("z_m", np.nan))
        save_radargram(line_out / f"{name}_Ex.jpg", data, distance, time_ns, f"Line {line_no:03d} | {name} | Ex")
    hyper = detect_hyperbolas(tg, distance, time_ns, line_out, f"Line {line_no:03d} | time gain")
    return {"line_no": line_no, "samples": int(raw.shape[1]), "traces": int(raw.shape[0]), "hyperbola": hyper}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True, help="Raw result directory relative to repository")
    ap.add_argument("--outdir", required=True, help="Processed output directory relative to repository")
    ap.add_argument("--low-ghz", type=float, default=0.25)
    ap.add_argument("--high-ghz", type=float, default=2.60)
    args = ap.parse_args()
    rawdir, outdir = ROOT / args.results, ROOT / args.outdir
    outdir.mkdir(parents=True, exist_ok=True)
    paths = sorted(rawdir.glob("line_*_Ex.npz"))
    if not paths:
        raise SystemExit(f"No raw NPZ files in {rawdir}")
    # FFT is calculated from the actual raw data, while the processing band is
    # kept at the requested CK-2500 reference band 0.25–2.60 GHz.
    all_rows, spectra = [], []
    for p in paths:
        z=np.load(p); x=z["Ex"].astype(float); t=z["time_ns"].astype(float); dt=float(np.median(np.diff(t)))*1e-9
        f=np.fft.rfftfreq(x.shape[1],dt); s=np.abs(np.fft.rfft((x-x.mean(axis=1,keepdims=True))*np.hanning(x.shape[1]),axis=1)).mean(axis=0); spectra.append(s)
    freq=f; spectrum=np.mean(np.stack(spectra),axis=0); peak=float(freq[np.argmax(spectrum)])/1e9
    fig,ax=plt.subplots(figsize=(10,5.5),dpi=180); ax.plot(freq/1e9,spectrum/(spectrum.max() or 1)); ax.axvspan(args.low_ghz,args.high_ghz,alpha=.2,color='tab:blue'); ax.set_xlim(0,10); ax.set_xlabel('Frequency (GHz)'); ax.set_ylabel('Normalized mean amplitude'); ax.set_title(f'Raw Ex FFT | peak {peak:.2f} GHz | band {args.low_ghz:.2f}–{args.high_ghz:.2f} GHz'); ax.grid(alpha=.25); fig.tight_layout(); fig.savefig(outdir/'fft_spectrum.jpg',pil_kwargs={'quality':95}); plt.close(fig)
    np.savez_compressed(outdir/'fft_spectrum.npz',frequency_Hz=freq,spectrum=spectrum,peak_frequency_GHz=np.float32(peak))
    for p in paths:
        n=int(p.stem.split('_')[1]); all_rows.append(process_one(p,outdir,n,args.low_ghz,args.high_ghz))
    manifest={'source_results':args.results,'processing_order':'raw -> dewow(1.5 ns) -> Butterworth(0.25-2.60 GHz) -> median background removal -> quadratic time gain','band_GHz':[args.low_ghz,args.high_ghz],'fft_peak_GHz':peak,'lines':all_rows}
    (outdir/'processing_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'processed_lines':len(all_rows),'fft_peak_GHz':peak},ensure_ascii=False))


if __name__ == '__main__': main()
