"""Apply only heading/figure-caption type changes to the accepted Chinese PDF."""
from pathlib import Path
import json,re,shutil,sys,argparse
sys.path.insert(0,str(Path(__file__).parents[1]/'mupdf'))
sys.path.append(str(Path(__file__).parents[1]/'ocr'))
import pymupdf as fitz
import numpy as np
from pipeline import CSS,markup,FONTDIR
from typography import resolve_style,STYLES

ROOT=Path(__file__).resolve().parents[3] if Path(__file__).parent.name=='system' else Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser();ap.add_argument('--base',type=Path,default=ROOT/'outputs/NV-CoT_mirror');ap.add_argument('--out',type=Path,default=ROOT/'outputs/NV-CoT_字体优化');args=ap.parse_args()
BASE=args.base;OUT=args.out
OUT.mkdir(parents=True,exist_ok=True)
source=BASE/'NV-CoT_中文镜像.pdf'
jobs=json.loads((BASE/'translations.json').read_text(encoding='utf-8'))
ir=json.loads((BASE/'layout.json').read_text(encoding='utf-8'))
native={b['id']:b for p in ir['pages'] for b in p['blocks']}
plans=[]
for j in jobs:
    if j['id'] not in native:continue
    plan=resolve_style(j,native[j['id']],ir['pages'][j['page']-1])
    if plan:plans.append({'id':j['id'],'page':j['page'],'source_bbox':j['bbox'],'translation':j['translation'],**plan})
doc=fitz.open(source);archive=fitz.Archive(str(FONTDIR))
css=CSS+'''@font-face{font-family:heading;src:url(msyhbd.ttc);font-weight:700}'''
for pi,page in enumerate(doc):
    active=[p for p in plans if p['page']==pi+1]
    if not active:continue
    for p in active:
        r=fitz.Rect(p['source_bbox']);inset=min(1.35,r.height*.16)
        r.y0+=inset;r.y1-=inset
        page.add_redact_annot(r,fill=False,cross_out=False)
    page.apply_redactions(images=0,graphics=0,text=0)
    for p in active:
        content=markup(p['translation'])
        if p.get('panel_breaks'):content=re.sub(r'（([abc])）',r'<br>（\1）',content)
        if p['style']=='figure_caption':content=re.sub(r'^(图\s*\d+)',r'<b>\1</b>',content)
        pcss=css.replace('line-height:1.12',f'line-height:{p["line_height"]}')
        family='heading' if p['bold'] else 'cn,latin,math'
        body=f'<body style="font-family:{family};font-size:{p["font_size"]}pt;font-weight:{700 if p["bold"] else 400};text-align:{p["align"]};padding-top:{p["padding_top"]}pt">{content}</body>'
        spare,scale=page.insert_htmlbox(fitz.Rect(p['bbox']),body,css=pcss,archive=archive,scale_low=1)
        p.update(spare_height=spare,font_scale=scale,effective_font_size=p['font_size']*scale)
        if spare<0:raise RuntimeError(f'Local style cannot fit without shrinkage: {p["id"]}')
doc.subset_fonts()
pdf=OUT/'NV-CoT_中文镜像_字体优化.pdf';doc.save(pdf,garbage=4,deflate=True)
(OUT/'样式配置.json').write_text(json.dumps(STYLES,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'样式调整记录.json').write_text(json.dumps(plans,ensure_ascii=False,indent=2),encoding='utf-8')
before=fitz.open(source);after=fitz.open(pdf);results=[]
shots=OUT/'页面对比';shots.mkdir(exist_ok=True)
for pi,(a,b) in enumerate(zip(before,after)):
    pa=a.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False);pb=b.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False)
    aa=np.frombuffer(pa.samples,dtype=np.uint8).reshape(pa.height,pa.width,3)
    bb=np.frombuffer(pb.samples,dtype=np.uint8).reshape(pb.height,pb.width,3)
    mask=np.zeros(aa.shape[:2],dtype=bool)
    for p in plans:
        if p['page']!=pi+1:continue
        r=fitz.Rect(p['bbox'])|fitz.Rect(p['source_bbox'])
        mask[max(0,int(r.y0*2)-4):int(r.y1*2)+5,max(0,int(r.x0*2)-4):int(r.x1*2)+5]=True
    change=(np.max(abs(aa.astype('int16')-bb.astype('int16')),axis=2)>12)&~mask
    results.append({'page':pi+1,'same_page_size':a.rect==b.rect,'changed_pixels_outside_title_caption_regions':int(change.sum())})
    if pi+1 in [1,2,3,4,5,6,8,9,10,11,14,15,16,17]:
        pa.save(shots/f'{pi+1:02d}-修改前.png');pb.save(shots/f'{pi+1:02d}-修改后.png')
assert len(before)==len(after)==23
assert all(r['same_page_size'] for r in results)
assert all(r['changed_pixels_outside_title_caption_regions']==0 for r in results),results
report={'pages':results,'page_count':23,'style_changes':len(plans),'headings':sum(p['style'].endswith('heading') for p in plans),'figure_captions':sum(p['style']=='figure_caption' for p in plans),'overflow_count':sum(p['spare_height']<0 for p in plans),'all_target_font_sizes_preserved':all(p['font_scale']==1 for p in plans)}
(OUT/'排版验收.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
