"""Recover the grid-snapped horizontal antenna positions from gprMax run logs."""

import argparse
import csv
from decimal import Decimal
from pathlib import Path
import re


TX = re.compile(r"Hertzian dipole with polarity x at ([\d.]+)m,")
RX = re.compile(r"Receiver at ([\d.]+)m,")
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "model/section_metadata/horizontal_acquisition.csv"


def millimetres(value):
    measured = Decimal(value) * 1000
    if measured != measured.to_integral_value():
        raise ValueError(f"Position in log is not a whole millimetre: {value} m")
    return int(measured)


def read_line(line_directory):
    pairs = []
    logs = sorted(line_directory.glob("chunk_*/run.log"), key=lambda p: int(p.parent.name.split("_")[-1]))
    for log in logs:
        first = int(log.parent.name.split("_")[-1])
        if first != len(pairs):
            raise ValueError(f"Missing or overlapping traces before {log}")
        content = log.read_text(encoding="utf-8", errors="replace")
        tx_values, rx_values = TX.findall(content), RX.findall(content)
        if not tx_values or len(tx_values) != len(rx_values):
            raise ValueError(f"Unpaired source and receiver records in {log}")
        pairs.extend((millimetres(tx), millimetres(rx)) for tx, rx in zip(tx_values, rx_values))
    if len(pairs) != 601:
        raise ValueError(f"{line_directory}: expected 601 traces, found {len(pairs)}")
    return pairs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raster", type=Path, required=True, help="Directory containing line_001 through line_021")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    reference = read_line(args.raster / "line_001")
    for line in range(2, 22):
        if read_line(args.raster / f"line_{line:03d}") != reference:
            raise ValueError(f"Line {line:03d} differs from line 001; one shared table cannot be used")
    consistent_geometry = [(tx, tx - 50) for tx in range(3100, 99, -10)]
    if reference[::2] != consistent_geometry:
        raise ValueError("Odd numbered traces do not cover the expected 301 positions at 50 mm offset")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("trace_no", "tx_mm", "rx_mm"))
        writer.writerows((number, tx, rx) for number, (tx, rx) in enumerate(reference, start=1))
    print(f"Wrote {len(reference)} shared positions for 21 lines; verified 301 traces at a 50 mm offset.")


if __name__ == "__main__":
    main()
