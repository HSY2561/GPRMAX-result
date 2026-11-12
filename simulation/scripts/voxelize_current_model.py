"""Create a gprMax GeometryObjectsRead HDF5 volume from the current model.

The VTPs are audited separately. Here the exact dimensions from the model
metadata are rasterised into a cell-centred material volume so the open-edge
surface representation of the cylindrical rebar does not create ambiguous
interiors during voxelisation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import h5py
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "model" / "paraview"


def load_json(name: str) -> dict:
    return json.loads((MODEL / name).read_text(encoding="utf-8"))


def apply_box(mask: np.ndarray, X: np.ndarray, Y: np.ndarray, cx: float, cy: float, sx: float, sy: float) -> None:
    mask |= (np.abs(X - cx) <= sx / 2) & (np.abs(Y - cy) <= sy / 2)


def build_volume(dx: float, outdir: Path) -> dict:
    model = load_json("model_metadata.json")
    defects = load_json("foam_defects_metadata.json")["defects"]
    plates = load_json("foam_plates_metadata.json")["plates"]

    # Store the specimen plus a 0.2 m local air margin.  The input deck
    # inserts this volume at p1=(0.1, 0.1, 0.1) inside a larger FDTD domain,
    # leaving a PML/air margin around all six sides.
    domain = (3.2, 2.2, 0.6)
    origin = (0.0, 0.0, 0.0)
    shape = tuple(int(round(length / dx)) for length in domain)
    nx, ny, nz = shape
    data = np.ones(shape, dtype=np.int16)  # material_001_air
    tags = np.zeros(shape, dtype=np.uint8)
    x = (np.arange(nx, dtype=np.float32) + 0.5) * dx
    y = (np.arange(ny, dtype=np.float32) + 0.5) * dx
    X = x[:, None]
    Y = y[None, :]

    slab = model["slab_m"]
    rebar = model["reinforcement"]
    radius = rebar["diameter_m"] / 2.0

    for k in range(nz):
        z = (k + 0.5) * dx
        layer = np.ones((nx, ny), dtype=np.int16)
        layer_tags = np.zeros((nx, ny), dtype=np.uint8)

        concrete = (
            (X >= 0.0) & (X <= slab["length_X"])
            & (Y >= 0.0) & (Y <= slab["width_Y"])
            & (z >= 0.0) & (z <= slab["thickness_Z"])
        )
        layer[concrete] = 0
        layer_tags[concrete] = 1

        eps = np.zeros((nx, ny), dtype=bool)
        for item in defects:
            cx, cy, cz = item["center_m"]
            if item["shape"] == "cube":
                s = item["size_m"]
                if abs(z - cz) <= s / 2:
                    apply_box(eps, X, Y, cx, cy, s, s)
            else:
                r = item["diameter_m"] / 2
                dz = z - cz
                if abs(dz) <= r:
                    rr = np.sqrt(max(r * r - dz * dz, 0.0))
                    eps |= (X - cx) ** 2 + (Y - cy) ** 2 <= rr * rr
        for plate in plates:
            cx, cy, cz = plate["center_m"]
            sx, sy = plate["length_m"], plate["width_m"]
            sz = plate["thickness_m"]
            if abs(z - cz) <= sz / 2:
                apply_box(eps, X, Y, cx, cy, sx, sy)
        layer[eps] = 3
        layer_tags[eps] = 2

        steel = np.zeros((nx, ny), dtype=bool)
        for zbar, ys in ((rebar["face_A"]["X_direction"]["z_m"], rebar["face_A"]["X_direction"]["y_centres_m"]),
                         (rebar["face_B"]["X_direction"]["z_m"], rebar["face_B"]["X_direction"]["y_centres_m"])):
            for y0 in ys:
                steel |= ((X >= 0.04) & (X <= 2.96) & ((Y - y0) ** 2 + (z - zbar) ** 2 <= radius * radius))
        for zbar, xs in ((rebar["face_A"]["Y_direction"]["z_m"], rebar["face_A"]["Y_direction"]["x_centres_m"]),
                         (rebar["face_B"]["Y_direction"]["z_m"], rebar["face_B"]["Y_direction"]["x_centres_m"])):
            for x0 in xs:
                steel |= ((Y >= 0.04) & (Y <= 1.96) & ((X - x0) ** 2 + (z - zbar) ** 2 <= radius * radius))
        layer[steel] = 2
        layer_tags[steel] = 3
        data[:, :, k] = layer
        tags[:, :, k] = layer_tags

    outdir.mkdir(parents=True, exist_ok=True)
    geofile = outdir / "geometry.h5"
    matfile = outdir / "materials.json"
    with h5py.File(geofile, "w") as h5:
        h5.create_dataset("data", data=data, compression="gzip", compression_opts=4)
        h5.create_dataset("material_keys", data=np.asarray([
            b"material_000_concrete", b"material_001_air", b"material_002_steel", b"material_003_eps"
        ], dtype="S21"))
        h5.create_dataset("tag_data", data=tags, compression="gzip", compression_opts=4)
        h5.create_dataset("tag_names", data=np.asarray([
            b"untagged", b"concrete_slab", b"foam_eps", b"steel"
        ], dtype="S16"))
        h5.attrs["GeometryTagsSchemaVersion"] = 1
        h5.attrs["MaterialDatabase"] = "materials"
        h5.attrs["MaterialDatabaseSchemaVersion"] = 1
        h5.attrs["dx_dy_dz"] = np.asarray([dx, dx, dx], dtype=np.float64)
        h5.attrs["origin_xyz"] = np.asarray(origin, dtype=np.float64)
        h5.attrs["shape_nxyz"] = np.asarray(shape, dtype=np.int64)
    materials = {
        "schema": "gprMax-material-database",
        "schema_version": 1,
        "database": {"id": "materials", "name": "东至南模型 materials", "version": "1.0.0"},
        "materials": {
            "material_000_concrete": {"name": "concrete", "model": "constant", "base": {"relative_permittivity": 6.0, "electric_conductivity_s_per_m": 0.01, "relative_permeability": 1.0, "magnetic_conductivity_s_per_m": 0.0}},
            "material_001_air": {"name": "air", "model": "constant", "base": {"relative_permittivity": 1.0, "electric_conductivity_s_per_m": 0.0, "relative_permeability": 1.0, "magnetic_conductivity_s_per_m": 0.0}},
            "material_002_steel": {"name": "steel", "model": "constant", "base": {"relative_permittivity": 1.0, "electric_conductivity_s_per_m": 1.0e6, "relative_permeability": 1.0, "magnetic_conductivity_s_per_m": 0.0}},
            "material_003_eps": {"name": "eps", "model": "constant", "base": {"relative_permittivity": 1.05, "electric_conductivity_s_per_m": 0.0, "relative_permeability": 1.0, "magnetic_conductivity_s_per_m": 0.0}},
        },
    }
    matfile.write_text(json.dumps(materials, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {"dx_m": dx, "domain_m": domain, "origin_m": origin, "shape_nxyz": shape, "cell_count": int(np.prod(shape)), "geometry_file": str(geofile), "materials_file": str(matfile), "material_counts": {str(k): int(np.count_nonzero(data == k)) for k in range(4)}}
    (outdir / "conversion.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dx", type=float, default=0.02)
    ap.add_argument("--outdir", type=Path, default=ROOT / "simulation" / "geometry_20mm")
    args = ap.parse_args()
    build_volume(args.dx, args.outdir)
