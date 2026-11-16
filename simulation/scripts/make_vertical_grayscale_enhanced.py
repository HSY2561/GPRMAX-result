"""Generate grayscale enhanced component radargrams for completed vertical lines.

The raw Ex/Ey/Ez and Esynthetic NPZ files are retained.  This creates a
comparison display using robust median-background removal, a 1.5 ns dewow,
and an additional quadratic late-time gain to make lower reinforcement and
void echoes easier to inspect.  It does not alter the forward results.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import uniform_filter1d

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "simulation" / "results" / "竖向测线" / "radar_profiles"
OUT = ROOT / "simulation" / "results" / "竖向测线" / "grayscale_enhanced"
N = 30
TIME_WINDOW_NS = 10.0
DEWOW_NS = 1.5


def process(data: np.ndarray, time_ns: np.ndarray) -> np.ndarray:
    data = np.asarray(data, dtype=np.float64)
    # Remove each time sample's median across the 401 trace positions.
    bg_removed = data - np.median(data, axis=0, keepdims=True)
    dt_ns = float(np.median(np.diff(time_ns)))
    size = max(3, int(round(DEWOW_NS / dt_ns)))
    if size % 2 == 0:
        size += 1
    dewow = bg_removed - uniform_filter1d(bg_removed, size=size, axis=1, mode="nearest")
    # Moderate quadratic gain, with an extra continuous late-time boost.
    u = np.clip(time_ns / TIME_WINDOW_NS, 0.0, 1.0)
    gain = 1.0 + 2.5 * u * u
    late = np.ones_like(gain)
    mid = (time_ns >= 5.0) & (time_ns <= 8.0)
    late[mid] = 1.0 + 0.8 * ((time_ns[mid] - 5.0) / 3.0)
    late[time_ns > 8.0] = 1.8
    return np.abs(dewow) * gain[None, :] * late[None, :]


def save_image(arr: np.ndarray, time_ns: np.ndarray, dist: np.ndarray, path: Path, title: str) -> None:
    p_low = float(np.percentile(arr, 1.0))
    p_high = float(np.percentile(arr, 99.5))
    if p_high <= p_low:
        p_low, p_high = 0.0, 1.0
    fig, ax = plt.subplots(figsize=(12, 6), dpi=160)
    ax.imshow(arr.T, origin="upper", aspect="auto", cmap="gray",
              vmin=p_low, vmax=p_high,
              extent=[float(dist[0]), float(dist[-1]), float(time_ns[-1]), float(time_ns[0])],
              interpolation="nearest")
    ax.set_xlabel("Distance along Y (m)")
    ax.set_ylabel("Time (ns)")
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=160, pil_kwargs={"quality": 95})
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    completed = []
    for p in sorted(SRC.glob("line_*_components.npz")):
        try:
            number = int(p.stem.split("_")[1])
        except (IndexError, ValueError):
            continue
        z = np.load(p)
        t = np.asarray(z["time_ns"], dtype=np.float64)
        dist = np.asarray(z["scan_distance_m"], dtype=np.float64)
        raw_syn = np.asarray(z["Esynthetic"], dtype=np.float64) if "Esynthetic" in z else np.sqrt(sum(np.asarray(z[k], dtype=np.float64)**2 for k in ("Ex", "Ey", "Ez")))
        arrays = {"Ex": np.asarray(z["Ex"], dtype=np.float64),
                  "Ey": np.asarray(z["Ey"], dtype=np.float64),
                  "Ez": np.asarray(z["Ez"], dtype=np.float64),
                  "Esynthetic": raw_syn}
        for comp, raw in arrays.items():
            if comp == "Esynthetic":
                disp = process(raw, t)
            else:
                disp = process(raw, t)
            save_image(disp, t, dist, OUT / f"line_{number:02d}_{comp}_gray_enhanced.jpg",
                       f"V{number:02d} | {comp} | grayscale enhanced")
        completed.append(number)
    manifest = {
        "line_count": N,
        "completed_lines": completed,
        "components": ["Ex", "Ey", "Ez", "Esynthetic"],
        "display": "grayscale absolute amplitude",
        "processing": "median background removal -> 1.5 ns dewow -> quadratic time gain -> continuous 5-8 ns late boost -> absolute amplitude",
        "dewow_window_ns": DEWOW_NS,
        "time_window_ns": TIME_WINDOW_NS,
        "source": "radar_profiles/line_##_components.npz",
        "preserves_original_purple": True,
    }
    (OUT / "grayscale_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "README.md").write_text(
        "保留原始紫色合成图；本目录新增 Ex/Ey/Ez/Esynthetic 灰度增强图。\n"
        "处理链：中值背景道去除、1.5 ns 去沃、适度二次时间增益、5–8 ns 晚时增强，最后显示绝对幅值。\n",
        encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
