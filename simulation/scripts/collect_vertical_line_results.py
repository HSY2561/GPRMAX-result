"""Collect completed vertical-line HDF5 traces into radar profile images."""
from __future__ import annotations
import json
from pathlib import Path
import h5py
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'simulation'/'raster_scan'/'vertical_lines'
OUT=ROOT/'simulation'/'results'/'竖向测线'/'radar_profiles'
N=30; NTR=401; TW=10.0

def read(path,comp):
    with h5py.File(path,'r') as h: return np.asarray(h['rxs']['rx1'][comp],dtype=np.float32)

def collect_line(n:int):
    d=RUN/f'line_{n:02d}'; paths=[d/f'input{i}.h5' for i in range(1,NTR+1)]
    if not all(p.exists() for p in paths): return False
    arrays={c:np.stack([read(p,c) for p in paths],axis=0) for c in ('Ex','Ey','Ez')}
    arrays['Esynthetic']=np.sqrt(arrays['Ex']**2+arrays['Ey']**2+arrays['Ez']**2)
    with h5py.File(paths[0],'r') as h:
        dt=float(h.attrs['dt'])
    nt=arrays['Ex'].shape[1]; t=np.arange(nt,dtype=np.float64)*dt*1e9; dist=np.arange(NTR,dtype=np.float32)*.005
    OUT.mkdir(parents=True,exist_ok=True)
    target=OUT/f'line_{n:02d}_components.npz'
    if not target.exists():
        np.savez_compressed(target,**arrays,time_ns=t,scan_distance_m=dist,dt_s=dt)
    # Original fields remain untouched. Render via render_paper_radargrams.py.
    return True

def main():
    done=[]
    for n in range(1,N+1):
        if collect_line(n): done.append(n)
    existing = []
    if OUT.exists():
        for p in OUT.glob('line_*_components.npz'):
            try:
                existing.append(int(p.stem.split('_')[1]))
            except (IndexError, ValueError):
                pass
    manifest={'line_count':N,'completed_lines':sorted(set(existing) | set(done)),'trace_spacing_m':.005,'line_length_m':2.0,'time_window_ns':TW,'processing':'raw fields retained; latest figures and provenance in ../paper_grayscale'}
    (OUT/'radar_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(manifest,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
