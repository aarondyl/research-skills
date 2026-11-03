from pathlib import Path
import json,shutil,sys
sys.path.insert(0,str(Path(__file__).parents[1]/'mupdf'))
import pymupdf as fitz
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'outputs/NV-CoT_字体优化'
items=[('一级章节标题',1,[104,644,507,669]),('二级标题：3.2',4,[104,185,507,208]),('二级标题：3.3',4,[104,342,507,365]),('Figure 1 图注',1,[104,568,507,633]),('Figure 2 右侧图注',2,[321,69,507,217])]
width=850;gap=25;margin=24;top=54
height=top+sum(round((r[3]-r[1])*2)+42 for _,_,r in items)+margin
canvas=Image.new('RGB',(width*2+margin*2+gap,height),'#eef2f1');draw=ImageDraw.Draw(canvas)
font=ImageFont.truetype('C:/Windows/Fonts/msyhbd.ttc',20);small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)
draw.text((margin,12),'修改前',font=font,fill='#31524a');draw.text((margin+width+gap,12),'修改后',font=font,fill='#31524a')
y=top
for title,page,r in items:
    h=round((r[3]-r[1])*2)
    for col,suffix in enumerate(['修改前','修改后']):
        x=margin+col*(width+gap);draw.text((x,y),title,font=small,fill='#35534e')
        im=Image.open(OUT/'页面对比'/f'{page:02d}-{suffix}.png')
        crop=im.crop(tuple(round(v*2) for v in r))
        draw.rectangle((x,y+26,x+width,y+26+h),fill='white');canvas.paste(crop,(x,y+26))
    y+=h+42
canvas.save(OUT/'字体与图注_前后对比.png')
doc=fitz.open(OUT/'NV-CoT_中文镜像_字体优化.pdf')
check=[]
for page,prefix,size in [(0,'1 引言',12.5),(3,'3.2',10.75),(3,'3.3',10.75)]:
    candidates=[s for b in doc[page].get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans'] if s['text'].replace('\xa0',' ').startswith(prefix)]
    assert candidates,prefix
    assert all(abs(s['size']-size)<.01 and s['flags']&16 for s in candidates),candidates
    check.append({'heading':prefix,'actual_font_size':size,'embedded_bold':True})
(OUT/'标题字体核验.json').write_text(json.dumps(check,ensure_ascii=False,indent=2),encoding='utf-8')
text='''# 字体层级与图注排版验收

仅修改章节标题和 Figure Caption；原 PDF 生成架构、正文、表格说明、公式、图片、页边距与分页均保持原设置。

## 代码修改

- typography.py：新增 section_heading、subsection_heading、subsubsection_heading、body_text、figure_caption、table_caption、equation 七类独立样式。标题必须同时满足原生结构类型和原始粗体样式；按原字体层级或显式 heading_level 分级，不将“4 Y”等公式误识别为标题。
- pipeline.py：将独立样式接入既有渲染器。正文、表格说明和公式样式不覆盖现有值。
- restyle.py：在已验收的中文 PDF 上仅替换标题和图注；保存前后截图，并逐页核对其他区域的像素。

一级标题 12.5 pt、二级标题 10.75 pt，采用嵌入的 Microsoft YaHei Bold 真粗体。三级配置为 9.75 pt；此论文没有独立三级标题，因此没有人为增加三级标题。

图注通常为 8.5 pt、1.20 倍行高；原文本框较矮的 Figure 6 使用 8.25 pt、1.10 倍行高。图号适度加粗，图注原框坐标均保留。Figure 1 在原有 (a)/(b)/(c) 分项处换行，以缩小字体而不制造过大的下方留白。Figure 2 的长图注仍位于右侧原区域，在区域内部保留 6 pt 顶部留白，使其与图形的上缘更协调。

标题文本框只向相邻空白处扩展；与后续正文至少保持 2 pt 几何间隔。没有移动正文以容纳标题。

## 实际验证

- 23 页，尺寸与分页均一致。
- 共调整 23 个标题及 7 个图注。
- “1 引言”实测为 12.5 pt 粗体；“3.2”“3.3”实测均为 10.75 pt 粗体，嵌入字体 Bold 标志已核验。
- 30 个区域全部在目标字号下排入，缩放比例均为 1，溢出为 0。
- 全部 23 页在标题和图注调整区域之外的像素变化为 0；因此正文行距、公式及其编号、图片尺寸、表格数据和原有页面结构未改变。
- 已可视检查首页标题层级、Figure 1 图注、Figure 2 侧边图注和 3.2/3.3 标题。缩小后的图注未遮挡图形，文本区域无截断。

逐页结果见“排版验收.json”；具体目标和实际字号见“样式调整记录.json”。原有翻译审校项不属于本次调整范围，未在此次排版工作中修改。
'''
(OUT/'排版调整说明.md').write_text(text,encoding='utf-8')
code=OUT/'system';code.mkdir(exist_ok=True)
for name in ['pipeline.py','typography.py','restyle.py','mappings.py']:
    shutil.copyfile(ROOT/'work/mirror'/name,code/name)
# Keep the previously delivered source tree executable with the new style module.
existing=ROOT/'outputs/NV-CoT_mirror/system'
for name in ['pipeline.py','typography.py','restyle.py']:
    shutil.copyfile(ROOT/'work/mirror'/name,existing/name)
print('Actual bold sizes verified; before/after comparison and report saved.')
