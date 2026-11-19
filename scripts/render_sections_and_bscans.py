"""Align true model sections and 21 horizontal radargrams from original fields.

Never reads an existing picture as data. Existing raw_Ex and
synthetic_magnitude_gray stems are updated; section_and_synthetic is added.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import render_paper_grayscale as base
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Patch, Rectangle
from matplotlib.colors import FuncNorm, ListedColormap
import numpy as np


METADATA = base.REPO / "model/section_metadata"
EPS = 1e-9
CONCRETE = "#e5eced"
STEEL = "#984725"
FOAM = "#399fb0"


def magnitude_display(rows, metadata):
    """Build a common-offset gather and a common light-background amplitude scale."""
    locations = np.genfromtxt(metadata / "horizontal_acquisition.csv", delimiter=",", names=True, dtype=int)
    indices = np.arange(0, 601, 2)
    if not (np.array_equal(locations["trace_no"], np.arange(1, 602))
            and np.array_equal(locations["tx_mm"][indices], np.arange(3100, 99, -10))
            and np.all(locations["tx_mm"][indices] - locations["rx_mm"][indices] == 50)):
        raise ValueError("Expected a complete 0–3 m gather at 50 mm realized offset")
    palette = np.genfromtxt(metadata / "gpr2_grayscale.csv", delimiter=",", names=True, dtype=int)
    if not np.array_equal(palette["gray"], np.arange(255, -1, -1)):
        raise ValueError("Unexpected GPR2 palette")
    metrics = []
    for row in rows:
        all_magnitude = row["synthetic_magnitude_gray"]
        if not np.allclose(row["distance"][indices], (3100-locations["tx_mm"][indices])/1000, atol=3e-7):
            raise ValueError("Distance axis and realized source coordinates disagree")
        row["display_distance"] = row["distance"][indices]
        row["display_magnitude"] = all_magnitude[indices]
        gate = (row["time"] >= .15) & (row["time"] <= 1.2)
        def jump(field):
            rms = np.sqrt(np.mean(field[:, gate]**2, axis=1))
            return float(np.median(2*np.abs(np.diff(rms))/(rms[:-1]+rms[1:])))
        metrics.append(dict(line=row["number"], all_traces=jump(all_magnitude),
                            common_offset=jump(row["display_magnitude"])))
    pooled = np.concatenate([row["display_magnitude"][:, row["time"] <= 10].ravel() for row in rows])
    knee, clip = np.percentile(pooled, [50, 99.5]).tolist()
    norm = FuncNorm((lambda x: np.arcsinh(x/knee), lambda x: knee*np.sinh(x)), 0., clip, clip=True)
    lut = ListedColormap(np.repeat(palette["gray"][:, None], 3, axis=1)/255, name="GPR2")
    return dict(norm=norm, cmap=lut, knee=knee, clip=clip, metrics=metrics)


def plot_magnitude(ax, row, display):
    # Each column is a computed trace. Keep its native 10 mm footprint.
    field = dict(row, distance=row["display_distance"], synthetic_magnitude_gray=row["display_magnitude"])
    im = base.plot(ax, field, "synthetic_magnitude_gray", 1.)
    im.set_cmap(display["cmap"])
    im.set_norm(display["norm"])
    return im


def magnitude_bar(cb, display):
    ticks = [v for v in (0, 2, 5, 10, 25, 50, 100) if v < .85*display["clip"]]
    cb.set_ticks(ticks + [display["clip"]], labels=[str(v) for v in ticks] + [f'{display["clip"]:.0f}'])
    cb.set_label("Gain-adjusted |E| (V/m)", labelpad=5)
    cb.outline.set_linewidth(.5)


def read_model(directory: Path) -> dict:
    names = ("model_metadata", "foam_defects_metadata", "foam_plates_metadata",
             "additional_rebars_metadata", "edge_rebars_metadata")
    source = {n: json.loads((directory / f"{n}.json").read_text(encoding="utf-8-sig"))
              for n in names}
    main = source["model_metadata"]
    slab = main["slab_m"]
    bars = []
    radius = main["reinforcement"]["diameter_m"] / 2
    for face in ("face_A", "face_B"):
        for direction in ("X", "Y"):
            item = main["reinforcement"][face][f"{direction}_direction"]
            centres = item["y_centres_m" if direction == "X" else "x_centres_m"]
            span = slab["length_X" if direction == "X" else "width_Y"]
            for i, centre in enumerate(centres):
                bars.append(dict(id=f"{face}_{direction}_{i+1}", direction=direction,
                                 centre=centre, z=item["z_m"], radius=radius,
                                 start=(span-item["bar_length_m"])/2,
                                 end=(span+item["bar_length_m"])/2))
    for name in ("additional_rebars_metadata", "edge_rebars_metadata"):
        for item in source[name]["bars"]:
            bars.append(dict(id=item["id"], direction="Y", centre=item["x_m"],
                             z=item["z_center_m"], radius=item["diameter_m"]/2,
                             start=item["y_min_m"], end=item["y_max_m"]))
    return dict(slab=slab, bars=bars, defects=source["foam_defects_metadata"]["defects"],
                plates=source["foam_plates_metadata"]["plates"],
                hashes={f"{n}.json": base.sha256(directory / f"{n}.json") for n in names})


def section_objects(model: dict, y: float) -> list[dict]:
    """Plane y=constant intersected with flat-ended bars, cubes, spheres, plates."""
    zmax = model["slab"]["z_max"]
    length = model["slab"]["length_X"]
    objects = []
    for bar in model["bars"]:
        if bar["direction"] == "Y":
            # Cylinder caps do not extend by a radius beyond their endpoints.
            if bar["start"]-EPS <= y <= bar["end"]+EPS:
                objects.append(dict(kind="steel", shape="circle", id=bar["id"],
                                    s=length-bar["centre"], depth=zmax-bar["z"],
                                    radius=bar["radius"]))
        else:
            delta = y-bar["centre"]
            if abs(delta) < bar["radius"]-EPS:
                halfheight = float(np.sqrt(bar["radius"]**2-delta**2))
                objects.append(dict(kind="steel", shape="rectangle", id=bar["id"],
                                    s=length-bar["end"], depth=zmax-bar["z"]-halfheight,
                                    width=bar["end"]-bar["start"], height=2*halfheight))
    for item in model["defects"]:
        x, cy, z = item["center_m"]
        delta = y-cy
        if item["shape"] == "cube":
            size = item["size_m"]
            if abs(delta) <= size/2+EPS:
                objects.append(dict(kind="EPS", shape="rectangle", id=item["file"],
                                    cell=item["cell"], s=length-x-size/2,
                                    depth=zmax-z-size/2, width=size, height=size))
        else:
            radius = item["diameter_m"]/2
            # Tangency is a zero-area point, not a full circular section.
            if abs(delta) < radius-EPS:
                section_radius = float(np.sqrt(radius**2-delta**2))
                objects.append(dict(kind="EPS", shape="circle", id=item["file"],
                                    cell=item["cell"], s=length-x, depth=zmax-z,
                                    radius=section_radius))
    for item in model["plates"]:
        x, cy, z = item["center_m"]
        if abs(y-cy) <= item["width_m"]/2+EPS:
            objects.append(dict(kind="EPS plate", shape="rectangle", id=item["file"],
                                s=length-x-item["length_m"]/2,
                                depth=zmax-z-item["thickness_m"]/2,
                                width=item["length_m"], height=item["thickness_m"]))
    return objects


def draw_section(ax, row: dict, model: dict, objects: list[dict]):
    slab = model["slab"]
    length, thickness = slab["length_X"], slab["thickness_Z"]
    ax.add_patch(Rectangle((0, 0), length, thickness, facecolor=CONCRETE,
                           edgecolor=".25", linewidth=.7, zorder=0))
    # Steel first; EPS replaces the corresponding concrete volume in the model.
    for item in objects:
        style = dict(facecolor=STEEL if item["kind"] == "steel" else FOAM,
                     edgecolor="#3b3530" if item["kind"] == "steel" else "#225a65",
                     linewidth=.45, zorder=2)
        if item["shape"] == "circle":
            patch = Circle((item["s"], item["depth"]), item["radius"], **style)
        else:
            patch = Rectangle((item["s"], item["depth"]), item["width"], item["height"], **style)
        ax.add_patch(patch)
    ax.set_xlim(0, length)
    ax.set_ylim(thickness, 0)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks(np.arange(0, length+.01, .5))
    ax.set_yticks([0, .15, .30, .45])
    ax.set_ylabel("Depth from A (m)", labelpad=5)
    ax.tick_params(direction="out", width=.6, length=3)
    ax.set_title(f"(a) Model section | Line {row['number']:03d}, y = {row['y']:.2f} m", pad=7)
    # Axis is inverted: depth zero (A) is the top boundary.
    ax.text(1.012, .985, "A", transform=ax.transAxes, fontsize=8, va="top")
    ax.text(1.012, .015, "B", transform=ax.transAxes, fontsize=8, va="bottom")
    for spine in ax.spines.values():
        spine.set_linewidth(.6)


def single_figure(row: dict, product: str, limit: float, out: Path, display):
    fig, ax = plt.subplots(figsize=(7.2, 3.8), layout="constrained")
    raw = product == "raw_Ex"
    im = base.plot(ax, row, product, limit) if raw else plot_magnitude(ax, row, display)
    caption = "Raw Ex | unfiltered, no gain" if raw else "Ex/Ey/Ez magnitude | 50 mm realized offset"
    ax.set_title(f"Line {row['number']:03d} (y = {row['y']:.2f} m) | {caption}")
    cb = fig.colorbar(im, ax=ax, pad=.018, fraction=.035, aspect=25)
    if raw:
        cb.set_ticks([-1, 0, 1])
        cb.set_label("Display amplitude / common clip level")
    else:
        magnitude_bar(cb, display)
    cb.outline.set_linewidth(.5)
    base.save_figure(fig, out / f"line_{row['number']:03d}" / product)


def combined_figure(row: dict, model: dict, objects: list[dict], display, out: Path):
    fig = plt.figure(figsize=(7.2, 5.4))
    # Both axes have the same physical X span and width. The section retains
    # its true 3:0.45 aspect; the B-scan keeps time as a separate ordinate.
    section = fig.add_axes([.09, .755, .79, .158])
    radar = fig.add_axes([.09, .11, .79, .525])
    draw_section(section, row, model, objects)
    legend = [Patch(facecolor=CONCRETE, edgecolor=".4", label="Concrete"),
              Patch(facecolor=STEEL, edgecolor=".2", label="Steel"),
              Patch(facecolor=FOAM, edgecolor="#225a65", label="EPS foam")]
    fig.legend(handles=legend, loc="center", bbox_to_anchor=(.49, .685), ncol=3,
               frameon=False, fontsize=8, handlelength=1.5, columnspacing=1.6)
    im = plot_magnitude(radar, row, display)
    radar.set_title("(b) Ex/Ey/Ez magnitude | 50 mm realized offset", pad=8)
    cb = fig.colorbar(im, cax=fig.add_axes([.902, .11, .018, .525]))
    magnitude_bar(cb, display)
    fig.text(.09, .967, "Dongzhi-Nan | true section and simulated B-scan", fontsize=10)
    fig.text(.09, .017, "301 computed traces at 10 mm spacing    |    0.25–2.60 GHz bandpass    |    5–8 ns late gain", fontsize=6.8)
    base.save_figure(fig, out / f"line_{row['number']:03d}" / "section_and_synthetic", color=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, default=base.DEFAULT_SOURCE)
    ap.add_argument("--out", type=Path, default=base.DEFAULT_OUT)
    ap.add_argument("--metadata", type=Path, default=METADATA)
    ap.add_argument("--only", type=int, help="Preview one line using all-21-line clipping")
    ap.add_argument("--keep-raw", action="store_true", help="Leave previously rendered Raw Ex files in place")
    args = ap.parse_args()
    rows = [base.load_line(args.source, number) for number in range(1, 22)]
    model = read_model(args.metadata)
    display = magnitude_display(rows, args.metadata)
    limits = {"raw_Ex": base.limit_for(rows, "raw_Ex"), "synthetic_magnitude_gray": display["clip"]}
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                         "axes.titlesize": 9, "axes.labelsize": 9,
                         "xtick.labelsize": 8, "ytick.labelsize": 8,
                         "pdf.fonttype": 42, "ps.fonttype": 42,
                         "hatch.linewidth": .35})
    inventory = []
    for row in rows:
        objects = section_objects(model, row["y"])
        inventory.append(dict(line=row["number"], y_m=row["y"], objects=objects,
                              steel_sections=sum(o["kind"] == "steel" for o in objects),
                              EPS_sections=sum(o["kind"].startswith("EPS") for o in objects)))
        if args.only is not None and args.only != row["number"]:
            continue
        for product, limit in limits.items():
            if product != "raw_Ex" or not args.keep_raw:
                single_figure(row, product, limit, args.out, display)
        combined_figure(row, model, objects, display, args.out)
        print(f"Rendered line {row['number']:03d}", flush=True)
    for row in rows:
        for path, digest in row["source_hashes"].items():
            assert base.sha256(args.source / path) == digest, f"Source array changed: {path}"
    for path, digest in model["hashes"].items():
        assert base.sha256(args.metadata / path) == digest, f"Geometry metadata changed: {path}"
    if args.only is not None:
        return
    manifest = dict(line_count=21, trace_count_per_line=601, samples_per_trace=521,
                    primary_product="section_and_synthetic",
                    input_policy="Numerical original gprMax Ex/Ey/Ez fields; no existing raster used as input",
                    section_policy="Actual plane intersection, not projection; analytical schematic of the geometry voxelized at 10 mm for simulation",
                    coordinate_transform=dict(y_model="raw y_m - 0.1 m", distance="3 m - x_model", depth="0.425 m - z_model"),
                    slab=model["slab"], model_hashes=model["hashes"],
                    section_inventory=inventory,
                    raw_Ex="Original signed Ex, no mean removal, filter or gain; black negative, middle gray zero, white positive",
                    synthetic_magnitude_gray="Trace means removed; 4th-order zero-phase Butterworth 0.25-2.60 GHz on each original component; sqrt(Ex_filtered^2+Ey_filtered^2+Ez_filtered^2); late gain",
                    late_gain="1x before 5 ns, quadratic rise 1 -> 6 from 5 -> 8 ns, 6x after 8 ns",
                    no_dewow=True,
                    composite_consistency="Combined lower panel and standalone synthetic use the identical numerical matrix and common display scale",
                    clip_limits=limits, clip_percentile=99.5,
                    clip_scope="Magnitude P99.5 pooled over all displayed traces and samples in 0–10 ns",
                    magnitude_display=dict(source_traces=601, selected_traces=301, trace_numbers="1,3,...,601",
                        nominal_spacing_mm=5, display_spacing_mm=10, realized_offset_mm=50, nominal_offset_mm=46,
                        palette="GPR2 embedded 256 levels, white at zero to black at clip",
                        mapping="asinh(amplitude/knee) / asinh(clip/knee), clipped to [0,1]",
                        knee=display["knee"], clip=display["clip"], direct_wave_adjacent_rms_jump=display["metrics"]),
                    export=dict(PNG="600 dpi, RGB for combined, L for standalone", PDF="vector labels + raster radar", JPG="300 dpi", combined_size_inches=[7.2,5.4], single_size_inches=[7.2,3.8]),
                    source_hashes={k:v for row in rows for k,v in row["source_hashes"].items()},
                    source_arrays_unchanged=True,
                    notes=["Depth and time are different axes; no travel-time-to-depth equivalence is implied.",
                           "Lines 001 and 021 cut slab side boundaries and no steel/EPS; 3D off-plane scattering may still appear in their B-scans.",
                           "Raw z_m is a stale antenna label, not used for section geometry.",
                           "No per-trace normalization, spatial smoothing or missing-trace interpolation."])
    (args.out / "section_render_manifest.json").write_text(json.dumps(manifest,indent=2), encoding="utf-8")
    with (args.out / "figure_index.csv").open("w",newline="",encoding="utf-8") as fp:
        w=csv.writer(fp)
        w.writerow(["line","y_m","section_and_synthetic_JPG","raw_Ex_JPG","synthetic_magnitude_JPG","signed_Ex_JPG","late_Ex_JPG"])
        for row in rows:
            folder=f"line_{row['number']:03d}"
            w.writerow([row["number"],f"{row['y']:.2f}",*[f"{folder}/{p}.jpg" for p in
                       ("section_and_synthetic","raw_Ex","synthetic_magnitude_gray","grayscale_Ex_late_gain","late_window_Ex")]])
    gallery=["# 21 model sections and grayscale vector-magnitude B-scans", "",
             "Top: model section with steel in rust and EPS in teal. Bottom: 301 computed traces at a common 50 mm realized offset, using the measured GPR2 white-to-black palette.", "",
             "Distance is aligned from the right start. Depth (top) and time (bottom) are distinct axes. See [method](README.md).", ""]
    for row in rows:
        folder=f"line_{row['number']:03d}"
        gallery += [f"## Line {row['number']:03d} — y = {row['y']:.2f} m", "",
                    f"![Section and synthetic B-scan]({folder}/section_and_synthetic.jpg)", "",
                    f"[PNG]({folder}/section_and_synthetic.png) | [PDF]({folder}/section_and_synthetic.pdf) | [Raw Ex]({folder}/raw_Ex.jpg) | [Ex/Ey/Ez magnitude]({folder}/synthetic_magnitude_gray.jpg)", ""]
    (args.out / "preview_gallery.md").write_text("\n".join(gallery),encoding="utf-8")
    print(json.dumps(dict(lines=21, figures_updated=42 if args.keep_raw else 63, source_arrays_unchanged=True, limits=limits)),flush=True)


if __name__ == "__main__":
    main()
