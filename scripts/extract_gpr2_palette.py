"""Extract the common 256-entry grayscale palette from GeoScan32 F4 profiles."""

import argparse
import csv
from hashlib import sha256
from pathlib import Path
import struct


def read_palette(profile: Path) -> bytes:
    with profile.open("rb") as fp:
        header = fp.read(512)
        palette = fp.read(256 * 4)
    if len(header) != 512 or len(palette) != 256 * 4:
        raise ValueError(f"{profile.name}: incomplete header or palette")
    signature, version = struct.unpack_from("<II", header)
    if signature != 0xFEDCBA98 or version not in (1, 2):
        raise ValueError(f"{profile.name}: unrecognized GeoScan32 F4 signature or version")
    for index, (red, green, blue, _reserved) in enumerate(struct.iter_unpack("4B", palette)):
        if not red == green == blue == 255 - index:
            raise ValueError(f"{profile.name}: expected white-to-black grayscale at index {index}")
    return palette


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_directory", type=Path)
    parser.add_argument("output_csv", type=Path)
    args = parser.parse_args()
    profiles = sorted(p for p in args.input_directory.rglob("*") if p.suffix.lower() == ".gpr2" and p.is_file())
    if not profiles:
        parser.error(f"No GPR2 profiles in {args.input_directory}")

    palette = read_palette(profiles[0])
    for profile in profiles[1:]:
        if read_palette(profile) != palette:
            raise ValueError(f"{profile.name}: palette differs from {profiles[0].name}")

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", encoding="ascii", newline="") as fp:
        writer = csv.writer(fp, lineterminator="\n")
        writer.writerow(("index", "gray"))
        writer.writerows(enumerate(palette[::4]))
    print(f"{len(profiles)} matching profiles, palette SHA-256 {sha256(palette).hexdigest()}")


if __name__ == "__main__":
    main()
