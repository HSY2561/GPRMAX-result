"""Inspect the ParaView state and all referenced VTP geometry.

This is a read-only audit. It records the resolved files, bounds, units,
cell/point counts, and boundary-edge counts before voxelisation.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
import xml.etree.ElementTree as ET

import pyvista as pv


ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "model" / "paraview"
PVSM = ROOT / "model" / "东至南模型.pvsm"
REPORT = ROOT / "simulation" / "model_audit.json"


def paths_from_pvsm(path: Path) -> list[Path]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    found: list[Path] = []
    for value in re.findall(r'value="([^"]+\.vtp)"', text, flags=re.I):
        candidate = Path(value)
        if not candidate.exists():
            candidate = MODEL / candidate.name
        if candidate not in found:
            found.append(candidate)
    return found


def audit_mesh(path: Path) -> dict:
    mesh = pv.read(path)
    edges = mesh.extract_feature_edges(
        boundary_edges=True,
        feature_edges=False,
        manifold_edges=False,
        non_manifold_edges=True,
    )
    return {
        "file": path.name,
        "resolved_path": str(path),
        "n_points": int(mesh.n_points),
        "n_cells": int(mesh.n_cells),
        "bounds_m": [float(x) for x in mesh.bounds],
        "boundary_or_nonmanifold_edge_cells": int(edges.n_cells),
    }


def main() -> None:
    if not PVSM.exists():
        raise FileNotFoundError(PVSM)
    referenced = paths_from_pvsm(PVSM)
    missing = [str(p) for p in referenced if not p.exists()]
    meshes = [audit_mesh(p) for p in referenced if p.exists()]
    report = {
        "source_pvsm": str(PVSM),
        "model_directory": str(MODEL),
        "coordinate_system": {"X": "length (m)", "Y": "face width (m)", "Z": "thickness (m)"},
        "units": "m",
        "referenced_vtp_count": len(referenced),
        "missing_vtp": missing,
        "meshes": meshes,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
