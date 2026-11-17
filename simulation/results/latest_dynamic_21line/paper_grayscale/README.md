# Model sections and publication grayscale B-scans — 21 horizontal lines

These figures were plotted again from **original gprMax field arrays** in `line_###_components.npz`. No existing JPG/PNG was used as an input. The original raw and processed NPZ files were not changed; SHA-256 digests are recorded in `render_manifest.json` and `section_render_manifest.json`.

## Figure products

| File stem in each `line_###` folder | Data and intended use |
| --- | --- |
| `section_and_synthetic` | Main comparison figure: top, the true model section at this line's Y coordinate; bottom, the same Ex/Ey/Ez vector-magnitude matrix and display scale as the standalone `synthetic_magnitude_gray` figure. |
| `grayscale_Ex_late_gain` | Signed Ex recomputed from original Ex, trace mean subtraction, fourth-order zero-phase 0.25–2.60 GHz Butterworth filter, then the specified late gain. Negative is black, zero is mid-gray, positive is white. |
| `raw_Ex` | Original signed Ex without filtering or gain, with a conservative full-window scale. |
| `synthetic_magnitude_gray` | Nonnegative vector magnitude of the recomputed filtered Ex/Ey/Ez, with late gain. Black denotes zero and white denotes large magnitude. This figure has no polarity. |
| `late_window_Ex` | 5–10 ns crop of signed filtered Ex with late gain. It uses a separately documented scale to inspect late reflections. |

The `selected_lines_comparison` figure uses the same main-figure scale for lines 003, 005, 008, 010, 015 and 019. `figure_index.csv` links every line and plot.

## Section geometry and alignment

- The current slab is 3.0 × 2.0 × **0.45 m**, with model Z from −0.025 to 0.425 m. Sections use the model metadata snapshot in `model/section_metadata`, verified against the latest PVSM/VTP and simulation geometry.
- Both panels use the same 0–3 m distance from the right-hand start: `s = 3 − x_model`. Line 001 is model Y = 0 m; line 021 is Y = 2 m; spacing is 0.1 m. Model Y equals the raw FDTD Y coordinate minus 0.1 m.
- The upper axis is physical depth below A, `depth = 0.425 − z_model`, increasing downward. Its geometry aspect ratio is true to scale. The lower axis is time, increasing downward. These are separate axes; no travel-time-to-depth conversion is implied.
- Black sections denote steel. White hatched sections denote EPS, a low-permittivity void surrogate. Sphere sections use the actual plane-intersection radius; cubes and plates use intersected rectangles. Flat-ended steel bars are not extended beyond their caps.
- Only targets intersecting the actual plane appear in the upper panel. The 3D electromagnetic response can contain off-plane reflections. In particular, lines 001/021 intersect the slab boundaries and no steel or EPS; targets are not projected into these sections.
- The upper diagram is an analytical model section. The FDTD geometry used 10 mm voxels, so it is not an exact drawing of every discretized voxel. Counts, section objects and metadata hashes are recorded in `section_render_manifest.json`.
- The original NPZ `z_m` contains an old antenna label; it is not used to draw the section.

The combined and standalone synthetic figures use `sqrt(Ex_filtered² + Ey_filtered² + Ez_filtered²)` multiplied by the late gain. This processed magnitude has no signed polarity. The separate **Raw Ex** figure retains the original signed, unfiltered and ungained field. Existing per-line file stems are preserved and overwritten with newly generated plots.

## Export and display settings

- PNG: 600 dpi, single-channel grayscale. PDF: vector text with raster radar data. JPG: 300 dpi preview.
- Single-line figure: 7.2 × 3.8 inches; combined section/B-scan figure: 7.2 × 5.4 inches, readable 8–9 point labels at native size.
- Horizontal axis: 0–3 m along the right-to-left scan. Vertical axis: 0–10 ns, increasing downward.
- All 21 lines share one clip level for each product. Main and magnitude figures estimate the 99.5th percentile from 1.2–10 ns, so the strong direct wave does not determine the entire gray range. Early strong samples remain visible but may be clipped. Raw figures estimate the clip from the full window. Late-detail figures estimate their independent clip from 5–10 ns.
- The colorbar reports amplitude divided by that product's common clip level; full and cropped images with different scales must not be compared by shade alone. Physical clip values are in `render_manifest.json`.
- Late gain is 1× before 5 ns, rises quadratically to 6× at 8 ns and remains 6× afterward. The raw figure provides a gain-free reference.
- No per-trace normalization, gap interpolation or extra spatial smoothing. Existing numerical/grid artifacts are not erased for presentation. The current stored processing did not include a 1.5 ns Dewow filter.

## Reproduce

From the repository root, with the gprMax Python environment (NumPy, SciPy, Matplotlib and Pillow):

```powershell
C:\env\gprmax_v4\Scripts\python.exe scripts\render_paper_grayscale.py --source C:\gprmax_latest\results --out simulation\results\latest_dynamic_21line\paper_grayscale
C:\env\gprmax_v4\Scripts\python.exe scripts\render_sections_and_bscans.py --source C:\gprmax_latest\results --out simulation\results\latest_dynamic_21line\paper_grayscale
```

Each line has 601 traces and 521 time samples. The recorded last time sample is about 10.0143 ns; the paper figures show the requested 0–10 ns window without altering the sampled time array.
