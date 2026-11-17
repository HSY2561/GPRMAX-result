"""Generate 30 Y-direction (vertical in A-face view) geometry sections."""
from __future__ import annotations

import csv, hashlib, json, shutil
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Patch, Rectangle
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
MODEL=Path(r"C:\Users\user\Desktop\东至南模型")
REPO_MODEL=ROOT/"model"/"paraview"
OUT=ROOT/"simulation"/"results"/"竖向测线"
LINE_COUNT=30
X_START=1.25
X_STEP=0.05
X_RIGHT_BOUNDARY=2.75
ORIGIN_X=0.1
ORIGIN_Y=0.1

def read_json(name):
    p=MODEL/name
    if not p.exists(): p=REPO_MODEL/name
    return json.loads(p.read_text(encoding='utf-8'))

def inventory():
    meta=read_json('model_metadata.json'); slab=meta['slab_m']; z0=float(slab.get('z_min',-.025)); z1=float(slab.get('z_max',.425))
    bars=[]
    for ln,lk in [('A base','face_A'),('B base','face_B')]:
        lay=meta['reinforcement'][lk]
        for i,y in enumerate(lay['X_direction']['y_centres_m'],1): bars.append({'kind':'X','group':'base','label':f'{ln} X{i}','y':float(y),'z':float(lay['X_direction']['z_m']),'d':float(meta['reinforcement']['diameter_m']),'color':'#7b3f20'})
        for i,x in enumerate(lay['Y_direction']['x_centres_m'],1): bars.append({'kind':'Y','group':'base','label':f'{ln} Y{i}','x':float(x),'y0':.04,'y1':1.96,'z':float(lay['Y_direction']['z_m']),'d':float(meta['reinforcement']['diameter_m']),'color':'#7b3f20'})
    for b in read_json('additional_rebars_metadata.json')['bars']: bars.append({'kind':'Y','group':'added','label':b['id'],'x':float(b['x_m']),'y0':float(b['y_min_m']),'y1':float(b['y_max_m']),'z':float(b['z_center_m']),'d':float(b['diameter_m']),'color':'#b01868' if b['layer'].startswith('A') else '#5f4b9a'})
    for b in read_json('edge_rebars_metadata.json')['bars']: bars.append({'kind':'Y','group':'edge','label':b['id'],'x':float(b['x_m']),'y0':float(b['y_min_m']),'y1':float(b['y_max_m']),'z':float(b['z_center_m']),'d':float(b['diameter_m']),'color':'#e08b22'})
    defects=[]
    for d in read_json('foam_defects_metadata.json')['defects']: defects.append({'label':f"F{d['cell']}",'kind':d['shape'],'x':float(d['center_m'][0]),'y':float(d['center_m'][1]),'z':float(d['center_m'][2]),'size':float(d.get('size_m',d.get('diameter_m')))})
    plates=[]
    for p in read_json('foam_plates_metadata.json')['plates']: plates.append({'label':'Plate A' if 'A' in p['layer'] else 'Plate B','x':float(p['center_m'][0]),'y':float(p['center_m'][1]),'z':float(p['center_m'][2]),'lx':float(p['length_m']),'ly':float(p['width_m']),'t':float(p['thickness_m'])})
    return bars,defects,plates,z0,z1

def draw(ax,xline,bars,defects,plates,z0,z1):
    t=z1-z0; ax.set_xlim(0,2); ax.set_ylim(t,0); ax.set_aspect('equal',adjustable='box'); ax.add_patch(Rectangle((0,0),2,t,facecolor='#f3c6a6',edgecolor='#222',lw=1.2)); vis=[]
    for b in bars:
        if b['kind']=='Y':
            if abs(xline-b['x'])>b['d']/2: continue
            dep=z1-b['z']; ax.add_patch(Rectangle((b['y0'],dep-b['d']/2),b['y1']-b['y0'],b['d'],facecolor=b['color'],edgecolor='#35180e',lw=.35,zorder=4))
        else:
            if not (0.04-b['d']/2<=xline<=2.96+b['d']/2): continue
            dep=z1-b['z']; ax.add_patch(Ellipse((b['y'],dep),b['d'],b['d'],facecolor=b['color'],edgecolor='#35180e',lw=.35,zorder=4))
        vis.append(b['label'])
    for d in defects:
        r=d['size']/2; dx=xline-d['x']
        if abs(dx)>r: continue
        dep=z1-d['z']
        if d['kind']=='sphere':
            rr=float(np.sqrt(max(r*r-dx*dx,0))); ax.add_patch(Ellipse((d['y'],dep),2*rr,2*rr,facecolor='#c51f45',edgecolor='#72152a',lw=.7,zorder=7))
        else: ax.add_patch(Rectangle((d['y']-r,dep-r),d['size'],d['size'],facecolor='#b10f35',edgecolor='#72152a',lw=.7,zorder=7))
        ax.text(d['y'],dep,d['label'],color='white',fontsize=5.5,ha='center',va='center',zorder=8); vis.append(d['label'])
    for p in plates:
        if abs(xline-p['x'])>p['lx']/2: continue
        dep=z1-p['z']; ax.add_patch(Rectangle((p['y']-p['ly']/2,dep-p['t']/2),p['ly'],p['t'],facecolor='#d97706',edgecolor='#7c3f00',lw=.8,zorder=6)); vis.append(p['label'])
    ax.set_xlabel('Length along Y (m; bottom-to-top)',fontsize=8); ax.set_ylabel('Depth from A surface (m)',fontsize=8); ax.set_xticks(np.arange(0,2.01,.25)); ax.set_yticks(np.arange(0,t+.001,.05)); ax.grid(alpha=.18,lw=.4)
    return sorted(set(vis))

def main():
    bars,defects,plates,z0,z1=inventory(); t=z1-z0
    # Never remove the parent results directory: it also contains receiver fields.
    (OUT/'geometry_sections').mkdir(parents=True,exist_ok=True)
    rows=[]
    for i in range(LINE_COUNT):
        x=X_START+i*X_STEP; fig,ax=plt.subplots(figsize=(11,2.8),dpi=180); vis=draw(ax,x,bars,defects,plates,z0,z1)
        handles=[Patch(facecolor='#7b3f20',label='Base mesh'),Patch(facecolor='#b01868',label='Added A (6)'),Patch(facecolor='#5f4b9a',label='Added B (6)'),Patch(facecolor='#e08b22',label='Edge bars'),Patch(facecolor='#c51f45',label='EPS/void'),Patch(facecolor='#d97706',label='Foam plate')]
        fig.legend(handles=handles,loc='upper center',bbox_to_anchor=(.5,.91),ncol=6,fontsize=6,frameon=False); fig.suptitle(f'Vertical line V{i+1:02d} | X={x:.3f} m | latest model 3.0 m × 0.45 m',fontsize=12,y=.98); fig.subplots_adjust(top=.74,bottom=.24,left=.06,right=.98)
        name=f'line_{i+1:02d}_geometry_section.jpg'; fig.savefig(OUT/'geometry_sections'/name,bbox_inches='tight',pil_kwargs={'quality':95}); plt.close(fig)
        rows.append({'line_no':i+1,'x_local_m':x,'x_physical_gprmax_m':x+ORIGIN_X,'y_start_local_m':0.0,'y_end_local_m':2.0,'length_m':2.0,'visible_model_objects':vis,'file':f'geometry_sections/{name}'})
    pvsm=MODEL/'东至南模型.pvsm'; manifest={'name':'30 vertical Y-direction survey-line geometry sections','line_count':LINE_COUNT,'spacing_m':X_STEP,'x_start_local_m':X_START,'x_end_last_line_local_m':X_START+(LINE_COUNT-1)*X_STEP,'right_boundary_local_m':X_RIGHT_BOUNDARY,'line_length_m':2.0,'direction':'Y / A-face vertical','slab_dimensions_m':[3.0,2.0,t],'slab_z_range_m':[z0,z1],'model_origin_m':[ORIGIN_X,ORIGIN_Y,0.1],'source_pvsm':str(pvsm.resolve()),'source_pvsm_sha256':hashlib.sha256(pvsm.read_bytes()).hexdigest(),'steel_inventory':{'base_X':8,'base_Y':12,'added_Y':12,'edge_A':2,'total_objects':len(bars)},'lines':rows}
    (OUT/'geometry_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'README.md').write_text('竖向测线几何剖面：30条Y方向测线，线长2 m，横向X位置从cell3/8/13左边界附近开始，间距5 cm。所有剖面按最新0.45 m板厚和等比例坐标绘制；实际坐标见geometry_manifest.json。\n',encoding='utf-8')
    with (OUT/'line_coordinates.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(['line_no','x_local_m','x_physical_gprmax_m','y_start_local_m','y_end_local_m','length_m'])
        for r in rows: w.writerow([r['line_no'],r['x_local_m'],r['x_physical_gprmax_m'],0,2,2])
    print(json.dumps({'output':str(OUT),'lines':LINE_COUNT,'x_first':X_START,'x_last':X_START+(LINE_COUNT-1)*X_STEP,'thickness':t},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
