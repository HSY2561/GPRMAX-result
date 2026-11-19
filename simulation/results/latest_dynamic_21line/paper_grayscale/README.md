# Color model sections and grayscale B-scans for 21 horizontal lines

[Open the comparisons](preview_gallery.md) or use [the line index](figure_index.csv) to find a specific line. Source fields come from the gprMax files named `line_###_components.npz`.

| File stem in each line folder | Contents |
| --- | --- |
| `section_and_synthetic` | Color model section above the Ex/Ey/Ez magnitude radargram. Both panels use distance from the right-hand start. |
| `synthetic_magnitude_gray` | The same magnitude matrix, grayscale palette and amplitude scale as the lower comparison panel. |
| `raw_Ex` | Original signed Ex at all 601 nominal trace positions, with no filtering or gain. Negative values appear black, zero gray and positive values white. |
| `grayscale_Ex_late_gain` | Signed Ex after bandpass filtering and late gain, using all 601 traces. |
| `late_window_Ex` | Signed Ex detail from 5–10 ns with a common scale specific to this time window. |

## Magnitude processing and gray levels

Each original line contains 601 traces at nominal 5 mm intervals and 521 samples per trace. Rounding antenna positions to the 10 mm simulation grid gives different realized Tx/Rx offsets among those traces. Mixing the offsets introduces abrupt trace-to-trace amplitude changes visible as vertical bands. For each magnitude radargram we select original traces 1, 3, 5, …, 601. These 301 traces all have a realized Tx/Rx separation of 50 mm. Their source positions span the full 3 m at 10 mm intervals. Every image column represents a computed trace. The retained positions and coordinates can be checked against [the acquisition table](../../../../model/section_metadata/horizontal_acquisition.csv).

Each field component is centered by subtracting its trace mean, then filtered with a fourth-order zero-phase Butterworth bandpass of 0.25–2.60 GHz. The displayed magnitude is `sqrt(Ex_filtered² + Ey_filtered² + Ez_filtered²)` multiplied by a time gain of 1 before 5 ns, rising quadratically to 6 from 5 to 8 ns, and held at 6 thereafter.

The amplitude scale is shared by all 21 magnitude panels. From all selected samples displayed in the 0–10 ns window, we take the median as the transition amplitude `k` and the 99.5th percentile as the clipping level `c`. A gain-adjusted magnitude `m` occupies the fraction `asinh(min(m,c)/k) / asinh(c/k)` of the grayscale palette. The magnitude colorbar gives gain-adjusted field values in V/m. Zero is white, clipped maxima are black, and the progression between them is monotonic.

All 45 measured GPR2 profiles supplied the same 256-level grayscale palette. The [extracted palette](../../../../model/section_metadata/gpr2_grayscale.csv) matches their file entries. The measured signal is signed and the simulated vector magnitude is nonnegative. The display uses the measured palette and sets its amplitude scale from the simulated fields, with no fit to measured absolute amplitudes.

## Section geometry and coordinates

The current slab is 3.0 × 2.0 × 0.45 m. In the upper panel, pale gray marks concrete, rust marks steel and teal marks EPS foam. The model section is drawn at its true aspect ratio. It includes the actual plane intersections with bars, spheres, cubes and plates. The simulation uses 10 mm voxels. The [geometry snapshot](../../../../model/section_metadata/) and [section manifest](section_render_manifest.json) document the model and objects cut by each plane.

Both panels span 0–3 m from the right-hand start, with `s = 3 − x_model`. The first line is at model Y = 0 m and the last at Y = 2 m, with 0.1 m line spacing. Depth in the upper panel is measured downward from A using `0.425 − z_model`. The lower panel shows simulated time increasing downward to 10 ns. Three-dimensional scattering can produce off-plane reflections even on the two boundary sections, which cut only concrete.

## Companion figures and exports

Raw Ex uses a symmetric linear scale with an absolute-amplitude clip at the 99.5th percentile over the full record. The signed filtered Ex figure uses 1.2–10 ns to set its common clip. The signed late-detail figure uses 5–10 ns. `selected_lines_comparison` shows signed filtered Ex for lines 003, 005, 008, 010, 015 and 019. See the [signed-product rendering manifest](render_manifest.json) for their scales and source hashes.

Each figure is available as a 600 dpi PNG, 300 dpi JPG and PDF with vector text. The combined exports preserve the colors of the material section and the grayscale of the B-scan. Standalone radargrams are grayscale.

## Reproduce

From the repository root, supply the local simulation results directory containing the numerical fields. Run the section renderer last to generate the final magnitude figures, index and gallery.

```powershell
C:\env\gprmax_v4\Scripts\python.exe scripts\render_paper_grayscale.py --source C:\gprmax_latest\results --out simulation\results\latest_dynamic_21line\paper_grayscale
C:\env\gprmax_v4\Scripts\python.exe scripts\render_sections_and_bscans.py --source C:\gprmax_latest\results --out simulation\results\latest_dynamic_21line\paper_grayscale
```
