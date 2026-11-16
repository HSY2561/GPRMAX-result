"""Build long five-radar comparison panels for all vertical survey lines."""
from __future__ import annotations
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "simulation" / "results" / "竖向测线"
GEOM = RESULT / "geometry_sections"
RADAR = RESULT / "radar_profiles"
GRAY = RESULT / "grayscale_enhanced"
OUT = RESULT / "comparison_panels_multichannel"
N = 30; W=1600; MARGIN=42; TITLE_H=52; LABEL_H=32; GAP=18; GEOM_H=410; RADAR_H=300
PANEL_H=TITLE_H+LABEL_H+GEOM_H+GAP+5*(LABEL_H+RADAR_H)+4*GAP+20

def font(size:int,bold=False):
    candidates=[r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",r"C:\Windows\Fonts\msyh.ttc"]
    for p in candidates:
        if Path(p).exists():
            try:return ImageFont.truetype(p,size=size)
            except OSError:pass
    return ImageFont.load_default()

def clean(src:Image.Image,kind:str)->Image.Image:
    w,h=src.size; cut=min(112,h//4) if kind=="geometry" else min(54,h//12); return src.crop((0,cut,w,h))

def paste_contain(canvas,src,box,fill=(250,250,250)):
    x,y,w,h=box; fitted=ImageOps.contain(src.convert("RGB"),(w,h),method=Image.Resampling.LANCZOS); bg=Image.new("RGB",(w,h),fill); bg.paste(fitted,((w-fitted.width)//2,(h-fitted.height)//2)); canvas.paste(bg,(x,y))

def image_path(n,kind): return RADAR/f"line_{n:02d}_radar_Esynthetic.jpg" if kind=="purple" else GRAY/f"line_{n:02d}_{kind}_gray_enhanced.jpg"

def make_panel(n):
    g=GEOM/f"line_{n:02d}_geometry_section.jpg"; kinds=["purple","Ex","Ey","Ez","Esynthetic"]; paths=[image_path(n,k) for k in kinds]
    if not g.exists() or not all(p.exists() for p in paths): return None
    canvas=Image.new("RGB",(W,PANEL_H),"white"); draw=ImageDraw.Draw(canvas); draw.text((MARGIN,14),f"V{n:02d}",fill=(20,20,20),font=font(30,True)); draw.text((MARGIN,TITLE_H+5),"(a) Geometry",fill=(35,35,35),font=font(21,True)); y=TITLE_H+LABEL_H
    with Image.open(g) as im: paste_contain(canvas,clean(im,"geometry"),(MARGIN,y,W-2*MARGIN,GEOM_H))
    y+=GEOM_H+GAP; labels=["(b) GPRMax Esynthetic (purple)","(c) Ex","(d) Ey","(e) Ez","(f) enhanced Esynthetic (grayscale)"]
    for label,path in zip(labels,paths):
        draw.text((MARGIN,y),label,fill=(35,35,35),font=font(19,True)); y+=LABEL_H
        with Image.open(path) as im: paste_contain(canvas,clean(im,"radar"),(MARGIN,y,W-2*MARGIN,RADAR_H))
        y+=RADAR_H+GAP
    out=OUT/f"V{n:02d}_comparison_multichannel.jpg"; canvas.save(out,quality=94,optimize=True); return out

def make_grid(paths,name,cols,cell=(520,700)):
    if not paths:return None
    cw,ch=cell; rows=(len(paths)+cols-1)//cols; canvas=Image.new("RGB",(cols*cw,rows*ch),"white"); draw=ImageDraw.Draw(canvas)
    for idx,p in enumerate(paths):
        x=(idx%cols)*cw; y=(idx//cols)*ch; img=Image.open(p).convert("RGB"); fitted=ImageOps.contain(img,(cw-12,ch-34),method=Image.Resampling.LANCZOS); canvas.paste(fitted,(x+(cw-fitted.width)//2,y+26+(ch-34-fitted.height)//2)); draw.text((x+10,y+5),p.stem.split("_")[0],fill=(20,20,20),font=font(20,True)); draw.rectangle((x,y,x+cw-1,y+ch-1),outline=(205,205,205),width=2)
    out=OUT/name; canvas.save(out,quality=93,optimize=True); return out

def main():
    OUT.mkdir(parents=True,exist_ok=True); panels=[]; pending=[]
    for n in range(1,N+1):
        out=make_panel(n); (panels if out else pending).append(out if out else n)
    grids=[make_grid(panels,"multichannel_grid_5x6.jpg",5),make_grid(panels,"multichannel_grid_3x10.jpg",3)]
    manifest={"line_count":N,"completed_lines":[int(p.stem[1:3]) for p in panels],"pending_lines":pending,"panel_order":["geometry","purple Esynthetic","Ex grayscale enhanced","Ey grayscale enhanced","Ez grayscale enhanced","Esynthetic grayscale enhanced"],"panel_layout":"one long image per line; geometry on top and five radar images below","source_purple":"radar_profiles/line_##_radar_Esynthetic.jpg","source_gray":"grayscale_enhanced/line_##_{Ex,Ey,Ez,Esynthetic}_gray_enhanced.jpg","output_dir":"comparison_panels_multichannel","grid_files":[str(p.relative_to(RESULT)).replace('\\','/') for p in grids if p]}
    (OUT/"multichannel_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    (OUT/"README.md").write_text("每条测线一张长图：顶部为几何剖面；下方依次为原始紫色 Esynthetic、Ex、Ey、Ez、灰度增强 Esynthetic。原紫色 comparison_panels 保留不变。灰度增强采用中值背景去除、1.5 ns 去沃、适度晚时增益和 5–8 ns 增强。\n",encoding="utf-8")
    print(json.dumps(manifest,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
