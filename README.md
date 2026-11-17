# Dongzhi-Nan gprMax results

## Model sections and publication grayscale radargrams — 21 horizontal lines

The latest figures are regenerated directly from gprMax Ex/Ey/Ez numerical arrays, rather than recolored purple pictures.

- [21-line grayscale gallery](simulation/results/latest_dynamic_21line/paper_grayscale/preview_gallery.md)
- [600 dpi PNG, PDF and JPG files](simulation/results/latest_dynamic_21line/paper_grayscale/)
- [Rendering method, common scales and gain documentation](simulation/results/latest_dynamic_21line/paper_grayscale/README.md)
- [Section and B-scan renderer](scripts/render_sections_and_bscans.py)
- [Signed-Ex and late-detail renderer](scripts/render_paper_grayscale.py)

Each main figure now places the true model section above the Ex/Ey/Ez vector-magnitude B-scan, with the same distance axis. Standalone **Raw Ex** and **Ex/Ey/Ez magnitude** figures are updated in their original paths. Signed Ex (negative black, zero mid-gray, positive white) and a 5–10 ns detail view remain available. The synthetic display uses the documented bandpass and late gain; Raw Ex is unfiltered and ungained. All 21 lines share a common scale within each figure product. The original numerical data are preserved locally in `C:\gprmax_latest\results`.

Existing vertical-scan comparison results remain under `simulation/results/竖向测线/`. These belong to a separate set from the 21 horizontal lines.

Purple raster previews have been removed. Use the complete grayscale gallery linked above.
