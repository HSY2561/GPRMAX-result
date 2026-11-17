"""Render numerical gprMax fields as grayscale radargrams; never recolor old JPGs.

Figure contract: compare the same 401 x 521 field samples, three signed receiver
components and two explicitly unsigned vector magnitudes. The six-panel plate
aligns distance axes with a true-aspect geometry section. No local feature edits,
trace interpolation, migration, or extra source polarisations are introduced.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.patches import Circle, Rectangle
from matplotlib.ticker import MultipleLocator
import numpy as np
from scipy.ndimage import uniform_filter1d
from scipy.signal import butter, sosfiltfilt

ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / 'simulation/results/竖向测线'
SRC = RESULT / 'radar_profiles'
OUT = RESULT / 'paper_grayscale'
KINDS = ('Esynthetic_reference', 'Ex', 'Ey', 'Ez', 'Esynthetic_processed')
LABELS = ('Reference |E|', 'Ex', 'Ey', 'Ez', 'Processed |E|')
GRID_M = .01
DT_S = 1.0 / (299792458.0 * np.sqrt(3 / GRID_M**2))
DPI = 300
plt.rcParams.update({
    'font.family': 'sans-serif', 'font.sans-serif': ['Arial', 'DejaVu Sans'],
    'font.size': 8, 'axes.labelsize': 8, 'axes.titlesize': 9,
    'xtick.labelsize': 7, 'ytick.labelsize': 7, 'axes.linewidth': .65,
    'pdf.fonttype': 42, 'svg.fonttype': 'none', 'figure.facecolor': 'white',
    'savefig.facecolor': 'white', 'xtick.direction': 'out', 'ytick.direction': 'out',
})


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_line(n):
    path = SRC / f'line_{n:02d}_components.npz'
    with np.load(path) as z:
        fields = np.stack([z[c] for c in ('Ex', 'Ey', 'Ez')]).astype(np.float64)
        distance = z['scan_distance_m'].astype(np.float64)
        saved_time = z['time_ns'].astype(np.float64)
    if fields.shape != (3, 401, 521) or not np.isfinite(fields).all():
        raise ValueError(f'Invalid receiver arrays in {path.name}: {fields.shape}')
    time = np.arange(fields.shape[-1], dtype=np.float64) * DT_S * 1e9
    # Keep all physical samples, including the last 10.014 ns sample; nominal TW=10 ns.
    return fields, time, distance, saved_time


def processed_fields(raw, time):
    window = int(round(1.5 / (DT_S * 1e9))) | 1
    dewow = raw - uniform_filter1d(raw, window, axis=-1, mode='nearest')
    sos = butter(4, [.25e9, 2.60e9], btype='bandpass', fs=1/DT_S, output='sos')
    filtered = sosfiltfilt(sos, dewow, axis=-1)
    residual = filtered - np.median(filtered, axis=1, keepdims=True)
    gain = 1 + 4 * np.minimum(time / 10, 1)**2
    late = 1 + np.clip((time - 5) / 3, 0, 1)  # smooth ramp: x1 -> x2
    return residual * (gain * late)[None, None, :]


def arrays_for(n):
    raw, time, distance, saved = load_line(n)
    processed = processed_fields(raw, time)
    arrays = [np.linalg.norm(raw, axis=0), *processed, np.linalg.norm(processed, axis=0)]
    return dict(zip(KINDS, arrays)), time, distance


def geometry_snapshot():
    path = OUT / 'geometry_snapshot.json'
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))
    # Initial snapshot is only accepted if it matches the PVSM used for the run.
    import export_vertical_geometry as geo
    manifest = json.loads((RESULT/'geometry_manifest.json').read_text(encoding='utf-8'))
    pvsm = geo.MODEL/'东至南模型.pvsm'
    if digest(pvsm) != manifest['source_pvsm_sha256']:
        raise ValueError('Desktop model changed since the simulated geometry; require frozen snapshot.')
    bars, defects, plates, z0, z1 = geo.inventory()
    snapshot = dict(bars=bars, defects=defects, plates=plates, z0=z0, z1=z1,
                    source_pvsm_sha256=manifest['source_pvsm_sha256'])
    path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding='utf-8')
    return snapshot


def draw_geometry(ax, n, snapshot):
    xline = 1.25 + (n-1)*.05
    z1 = snapshot['z1']; depth = z1-snapshot['z0']
    ax.add_patch(Rectangle((0,0), 2, depth, facecolor='.94', edgecolor='.2', lw=.6))
    for bar in snapshot['bars']:
        r=bar['d']/2; dep=z1-bar['z']
        if bar['kind']=='X':
            ax.add_patch(Circle((bar['y'],dep),r,facecolor='.25',edgecolor='.1',lw=.3))
        else:
            delta=xline-bar['x']
            if abs(delta)>=r: continue
            section=2*np.sqrt(r*r-delta*delta)
            ax.add_patch(Rectangle((bar['y0'],dep-section/2),bar['y1']-bar['y0'],section,facecolor='.25',lw=0))
    for defect in snapshot['defects']:
        r=defect['size']/2; delta=xline-defect['x']; dep=z1-defect['z']
        if abs(delta)>=r-1e-8: continue
        if defect['kind']=='sphere':
            rr=np.sqrt(r*r-delta*delta)
            ax.add_patch(Circle((defect['y'],dep),rr,facecolor='.65',edgecolor='.1',lw=.55))
        else:
            ax.add_patch(Rectangle((defect['y']-r,dep-r),2*r,2*r,facecolor='.65',edgecolor='.1',lw=.55))
    for plate in snapshot['plates']:
        if abs(xline-plate['x'])>=plate['lx']/2: continue
        ax.add_patch(Rectangle((plate['y']-plate['ly']/2,z1-plate['z']-plate['t']/2),plate['ly'],plate['t'],facecolor='.55',edgecolor='.1',lw=.4))
    ax.set(xlim=(0,2),ylim=(depth,0),ylabel='Depth (m)')
    ax.set_aspect('equal',adjustable='box')
    ax.set_yticks([0,.15,.30,.45]); ax.xaxis.set_major_locator(MultipleLocator(.5))
    ax.tick_params(length=3,width=.65,pad=2)


def image(ax, data, time, distance, scale, signed, *, xlabel=False):
    dt = time[1]-time[0]; dx = distance[1]-distance[0]
    # Pixel centres correspond to the original sample coordinates.
    extent=[distance[0]-dx/2,distance[-1]+dx/2,time[-1]+dt/2,time[0]-dt/2]
    normalised = data/scale
    ax.imshow(normalised.T, cmap='gray_r', norm=Normalize(-1 if signed else 0,1),
              aspect='auto', origin='upper', extent=extent, interpolation='nearest', rasterized=True)
    ax.set(xlim=(0,2),ylim=(time[-1]+dt/2,0),ylabel='Time (ns)')
    ax.set_xticks([0,.5,1,1.5,2]); ax.set_yticks([0,2,4,6,8,10])
    ax.tick_params(length=3,width=.65,pad=2,labelbottom=xlabel)
    if xlabel: ax.set_xlabel('Distance along Y (m)')
    return float(np.mean(np.abs(normalised)>1))


def export_individual(n, kind, data, time, distance, scale):
    fig,ax=plt.subplots(figsize=(7.2,2.6))
    fig.subplots_adjust(left=.085,right=.985,bottom=.19,top=.91)
    ax.set_title(f'V{n:02d}   {LABELS[KINDS.index(kind)]}',loc='left',fontweight='bold')
    clipped=image(ax,data,time,distance,scale,kind in ('Ex','Ey','Ez'),xlabel=True)
    fig.savefig(OUT/'individual'/f'V{n:02d}_{kind}.jpg',dpi=DPI,pil_kwargs={'quality':95})
    plt.close(fig)
    return clipped


def export_plate(n, arrays, time, distance, scales, snapshot):
    width,height=7.2,13.9
    fig=plt.figure(figsize=(width,height))
    left,axes_width=.085,.9
    geometry_height=width*axes_width*.45/2
    bottom=height-.45-geometry_height
    ax=fig.add_axes([left,bottom/height,axes_width,geometry_height/height])
    draw_geometry(ax,n,snapshot)
    ax.set_title(f'a  V{n:02d}   Geometry',loc='left',fontweight='bold',pad=5)
    ax.tick_params(labelbottom=False)
    for i,kind in enumerate(KINDS):
        bottom -= .42+1.85
        ax=fig.add_axes([left,bottom/height,axes_width,1.85/height])
        image(ax,arrays[kind],time,distance,scales[kind],kind in ('Ex','Ey','Ez'),xlabel=i==4)
        ax.set_title(f'{chr(98+i)}  {LABELS[i]}',loc='left',fontweight='bold',pad=5)
    fig.savefig(OUT/'comparison'/f'V{n:02d}_grayscale.jpg',dpi=DPI,pil_kwargs={'quality':95})
    fig.savefig(OUT/'comparison'/f'V{n:02d}_grayscale.pdf',dpi=DPI)
    if n==18:
        fig.savefig(OUT/'V18_preview.png',dpi=DPI)
        fig.savefig(OUT/'V18_editable.svg',dpi=DPI)
    plt.close(fig)


def export_overview():
    # Index/contact sheet. Individual PDFs are the legible full-size figures.
    fig,axes=plt.subplots(6,5,figsize=(15,35))
    fig.subplots_adjust(left=.005,right=.995,bottom=.005,top=.995,wspace=.02,hspace=.03)
    for n,ax in enumerate(axes.flat,1):
        ax.imshow(plt.imread(OUT/'comparison'/f'V{n:02d}_grayscale.jpg'))
        ax.set_axis_off()
    fig.savefig(OUT/'overview_30_lines.jpg',dpi=300,pil_kwargs={'quality':93})
    plt.close(fig)


def main():
    p=argparse.ArgumentParser(); p.add_argument('--lines',nargs='*',type=int,default=list(range(1,31)))
    args=p.parse_args()
    for sub in ('individual','comparison'): (OUT/sub).mkdir(parents=True,exist_ok=True)
    snapshot=geometry_snapshot()
    # One scale per panel family pooled across all 30 lines, never per-trace AGC.
    pooled={k:[] for k in KINDS}
    source_hashes={}
    for n in range(1,31):
        arrays,_,_=arrays_for(n)
        for k in KINDS: pooled[k].append(np.abs(arrays[k]).ravel())
        source_hashes[f'line_{n:02d}_components.npz']=digest(SRC/f'line_{n:02d}_components.npz')
    scales={k:float(np.percentile(np.concatenate(pooled[k]),99.0)) or 1 for k in KINDS}
    del pooled
    rows=[]
    for n in args.lines:
        arrays,time,distance=arrays_for(n)
        clipping={k:export_individual(n,k,arrays[k],time,distance,scales[k]) for k in KINDS}
        export_plate(n,arrays,time,distance,scales,snapshot)
        rows.append({'line':n,'shape':[401,521],'clipped_fraction_by_panel':clipping})
        print(f'Rendered V{n:02d}: five grayscale radargrams + JPG/PDF plate',flush=True)
    if len(args.lines)==30: export_overview()
    manifest={
        'line_count':30,'rendered_lines':args.lines,'panel_order':['geometry',*KINDS],
        'runtime':'gprMax Python environment; saved receiver fields, no FDTD rerun',
        'nominal_time_window_ns':10.,'dt_s_reconstructed_from_3d_cfl':DT_S,
        'last_sample_time_ns':float(time[-1]),'original_npz_time_axis_retained_unchanged':True,
        'time_axis_correction':'arange(521)*dt instead of legacy linspace(0,10,521); no time-zero calibration',
        'components':'Ex/Ey/Ez are receiver components from the SAME x-polarised source',
        'processing':'signed components: dewow 1.5 ns -> zero-phase Butterworth order 4 0.25-2.60 GHz -> median background across traces -> gain',
        'gain':'(1+4*min(t/10ns,1)^2)*(1+clip((t-5ns)/3ns,0,1)); capped at 10; no AGC',
        'reference_magnitude':'sqrt(raw Ex^2+raw Ey^2+raw Ez^2); no processing or polarity invention',
        'processed_magnitude':'sqrt(processed Ex^2+processed Ey^2+processed Ez^2)',
        'grayscale':'gray_r; signed components: zero mid-gray, negative white, positive black; magnitudes: zero white',
        'scale_policy':'99th percentile pooled across all 30 lines, one constant per panel family; directions independently scaled, not amplitude-comparable',
        'normalisation_scales_v_per_m_after_gain':scales,'image_interpolation':'nearest, no spatial smoothing',
        'no_exclusions':{'lines':30,'traces_per_line':401,'samples_per_trace':521},
        'limitations':['10 mm FDTD mesh quantises nominal 5 mm steps; repeated adjacent traces retained',
                        'background removal may suppress continuous horizontal reflectors',
                        'late gain amplifies noise and multiples as well as targets; no target detection claimed',
                        'nonnegative vector magnitudes cannot have signed phase',
                        'display revision is not a new antenna model or a convergence study'],
        'source_sha256':source_hashes,'per_line_qa':rows,'exports':{'individual_jpg':150,'comparison_jpg':30,'comparison_pdf':30,'overview_jpg':1,'dpi':DPI}}
    (OUT/'processing_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
    (OUT/'README.md').write_text('''# Grayscale Radargrams — 30 竖向测线

从 gprMax Ex/Ey/Ez 数值数据直接绘图，未对旧 JPG 去色。每条对比图依次为几何、未处理合成模值、Ex、Ey、Ez、处理后合成模值；无材料图例。时间纵轴、距离横轴，所有子图等宽对齐。

Ex/Ey/Ez 保留正负相位，零值为中灰、负值白、正值黑。合成模值均非负（零白、强幅值黑），不能视为带极性的实测电压。Ex/Ey/Ez 是同一次 X 极化源的三个接收分量，不是三种源极化的独立正演。

新后处理：1.5 ns 去沃 → 四阶零相位 Butterworth 0.25–2.60 GHz → 沿测线中值背景去除 → 连续时间增益（上限10倍）。增强合成先处理各有符号分量再取范数；未对原始合成模值伪造正负号。原始合成面板不处理，保留参照。

色阶按全部30条的99%分位固定；每类图独立归一化，故不同分量亮度不能用于绝对振幅比较。未做逐道AGC、局部修补、插值补道或偏移成像。增益也会放大噪声和多次反射；背景去除可能减弱连续界面反射。

原始30个NPZ保持字节不变。旧汇总脚本时间轴用linspace(0,10,521)，本次绘图依据10mm三维CFL及运行日志恢复约19.2583ps间隔（末样约10.0143ns），不改变样本、无时间零点标定。名义5mm道间距小于10mm计算网格，相邻重复道保留，重绘不提高物理分辨率。

individual/：150张300dpi JPG。comparison/：30张上下对比JPG和30份可编辑坐标文字的PDF。overview_30_lines.jpg：5列6行索引总览，应放大单图/PDF观察。processing_manifest.json记录全部参数、色阶、裁剪比例及源哈希；geometry_snapshot.json固定本次几何剖面。
''',encoding='utf-8')
    print(json.dumps({'output':str(OUT),'lines':len(rows),'scales':scales}),flush=True)


if __name__=='__main__': main()
