# Publication grayscale B-scans — 21 horizontal lines

These figures were plotted again from **gprMax field arrays** in `line_###_components.npz`. No purple JPG/PNG was used as an input. The original raw and processed NPZ files were not changed; SHA-256 digests are recorded in `render_manifest.json`.

## Figure products

| File stem in each `line_###` folder | Data and intended use |
| --- | --- |
| `grayscale_Ex_late_gain` | Main figure: signed Ex recomputed from original Ex, trace mean subtraction, fourth-order zero-phase 0.25–2.60 GHz Butterworth filter, then the specified late gain. Negative is black, zero is mid-gray, positive is white. |
| `raw_Ex` | Original signed Ex without filtering or gain, with a conservative full-window scale. |
| `synthetic_magnitude_gray` | Nonnegative vector magnitude of the recomputed filtered Ex/Ey/Ez, with late gain. Black denotes zero and white denotes large magnitude. This figure has no polarity. |
| `late_window_Ex` | 5–10 ns crop of signed filtered Ex with late gain. It uses a separately documented scale to inspect late reflections. |

The `selected_lines_comparison` figure uses the same main-figure scale for lines 003, 005, 008, 010, 015 and 019. `figure_index.csv` links every line and plot.

## Export and display settings

- PNG: 600 dpi, single-channel grayscale. PDF: vector text with raster radar data. JPG: 300 dpi preview.
- Single-line figure: 7.2 × 3.8 inches, readable 8–9 point labels at native size.
- Horizontal axis: 0–3 m along the right-to-left scan. Vertical axis: 0–10 ns, increasing downward.
- All 21 lines share one clip level for each product. Main and magnitude figures estimate the 99.5th percentile from 1.2–10 ns, so the strong direct wave does not determine the entire gray range. Early strong samples remain visible but may be clipped. Raw figures estimate the clip from the full window. Late-detail figures estimate their independent clip from 5–10 ns.
- The colorbar reports amplitude divided by that product's common clip level; full and cropped images with different scales must not be compared by shade alone. Physical clip values are in `render_manifest.json`.
- Late gain is 1× before 5 ns, rises quadratically to 6× at 8 ns and remains 6× afterward. The raw figure provides a gain-free reference.
- No per-trace normalization, gap interpolation or extra spatial smoothing. Existing numerical/grid artifacts are not erased for presentation. The current stored processing did not include a 1.5 ns Dewow filter.

## Reproduce

From the repository root, with the gprMax Python environment (NumPy, SciPy, Matplotlib and Pillow):

```powershell
C:\env\gprmax_v4\Scripts\python.exe scripts\render_paper_grayscale.py --source C:\gprmax_latest\results --out simulation\results\latest_dynamic_21line\paper_grayscale
```

Each line has 601 traces and 521 time samples. The recorded last time sample is about 10.0143 ns; the paper figures show the requested 0–10 ns window without altering the sampled time array.
