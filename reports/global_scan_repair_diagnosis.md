# Global scan repair plan and validation

The original 10 mm result is retained under `simulation/results/global_10mm/`.
The internal Y=0.500 m line was used for the repair acceptance test because it
contained the repeated low-amplitude columns.

| case | Tx/Rx height | low-RMS traces in line 005 |
|---|---:|---:|
| original | 0.500 m | 30 |
| diagnostic | 0.510 m | 22 |
| repaired | 0.520 m | 0 |

The repaired production input is `simulation/raster_scan/global_10mm_fixed520/`.
It keeps the 10 mm grid, 10 ns time window, 301 traces per line and the same
right-to-left / bottom-to-top path. The source and receiver are raised above
the 0.500 m A surface so that they are in air cells and do not coincide with
the top reinforcement.

The 20 mm reference uses a separate domain and translated insertion point so
that the same local specimen is compared without placing the imported volume
outside the FDTD grid. It is generated under
`simulation/raster_scan/global_20mm_reference/`.

Both result sets will be processed with the same physical coordinate system:
raw, 1.5 ns dewow, 0.25–2.60 GHz fourth-order zero-phase Butterworth bandpass,
median background removal, quadratic time gain, FFT spectrum, and a reported
candidate hyperbola map. Candidate hyperbolas are a detection aid and are not
treated as a replacement for the original data.
