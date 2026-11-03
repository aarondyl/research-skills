"""Layout-preserving PDF translation. No page is reconstructed as an article.
Usage: python pipeline.py [--source FILE] [--out DIRECTORY]
NV-CoT fixture translations are explicit, reviewable JSON keyed by element ID.
For another paper, export IR, fill translations.json with an LLM, then rerun.
"""
import argparse, hashlib, html, json, re, sys, os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'mupdf'))
sys.path.append(str(Path(__file__).parents[1]/'ocr'))
import pymupdf as fitz
from mappings import translations, LABELS

ROOT=Path(__file__).resolve().parents[2]
SOURCE=Path(r'C:/Users/Aaron/AppData/Local/Temp/Zotero/drag/Thinking with Images as Continuous Actions_2026.pdf')
FONTDIR=Path(os.environ.get('PDF_TRANSLATION_FONT_DIR','C:/Windows/Fonts'))
FORMULAS={4:[(85,104),(266,298),(484,503),(551,586),(630,667),(692,730)],5:[(98,126),(211,228),(333,389),(551,582),(675,706)],6:[(110,129),(171,209)],9:[(372,388),(401,437)]}
def plain(b):return ' '.join(''.join(s['text'] for s in l['spans']) for l in b.get('lines',[]))
def norm(s):return re.sub(r'\s+',' ',s.replace('\xa0',' ')).strip()
def dump(p,data):
    def encode(x):
        if isinstance(x,(fitz.Point,fitz.Rect,fitz.Quad)):return list(x)
        if isinstance(x,bytes):return x.hex()
        return str(x)
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2,default=encode),encoding='utf-8')
def rectlist(r):return list(map(float,r))

def parse(doc,out):
    pages=[]
    nv_fixture='Thinking with Images as Continuous Actions' in doc[0].get_text()
    for pi,page in enumerate(doc):
        blocks=[]
        for block in page.get_text('dict')['blocks']:
            if block['type']!=0:continue
            bid=f'p{pi+1}.b{block["number"]}';text=plain(block);r=fitz.Rect(block['bbox'])
            fontspans=[s for l in block['lines'] for s in l['spans']]
            kind='text'
            if nv_fixture and any(r.y0>=a and r.y1<=b for a,b in FORMULAS.get(pi+1,[])):kind='formula'
            elif not nv_fixture and sum(len(s['text']) for s in fontspans if re.search(r'CM(?:MI|SY|EX)|Math|Symbol',s['font']))>len(text)*.55 and len(re.findall(r'\b[A-Za-z]{4,}\b',text))<3:kind='formula'
            if re.match(r'(Figure|Table) \d',text):kind='caption'
            elif re.match(r'^(?:\d+(?:\.\d+)*|[AB](?:\.\d+)?)\s+[A-Z]',text) or text in ['Abstract','References','Acknowledgements and Disclosures','NeurIPS Paper Checklist']:kind='heading'
            if re.match(r'^\[\d+\]',text) and 11<=pi+1<=14:kind='reference'
            if re.fullmatch(r'\d+',text) and r.y0>730:kind='page_number'
            blocks.append({'id':bid,'page':pi+1,'bbox':list(block['bbox']),'type':kind,'text':text,'reading_order':len(blocks),'lines':block['lines'],'font_size':max(s['size'] for s in fontspans),'bold':sum(bool(s['flags']&16) for s in fontspans)>len(fontspans)/2,'direction':block['lines'][0]['dir']})
        images=page.get_image_info(hashes=True,xrefs=True)
        for n,im in enumerate(images):im.update(id=f'p{pi+1}.image{n}',digest=im.get('digest',b'').hex())
        drawings=[{'id':f'p{pi+1}.drawing{n}','bbox':rectlist(d['rect']),'type':d['type'],'fill':d['fill'],'color':d['color'],'items':d['items']} for n,d in enumerate(page.get_drawings())]
        tables=[]
        try:
            for n,t in enumerate(page.find_tables(strategy='lines_strict').tables):tables.append({'id':f'p{pi+1}.table{n}','bbox':list(t.bbox),'rows':t.row_count,'columns':t.col_count,'cells':t.cells,'text':t.extract()})
        except Exception as e:tables=[{'detection_error':str(e),'review_required':True}]
        pages.append({'number':pi+1,'size':[page.rect.width,page.rect.height],'mediabox':rectlist(page.mediabox),'cropbox':rectlist(page.cropbox),'blocks':blocks,'images':images,'tables':tables,'drawings':drawings,'formula_regions':FORMULAS.get(pi+1,[]) if nv_fixture else []})
    ir={'schema':'layout-ir/1','source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'coordinate_system':'PDF points; top-left origin','pages':pages}
    dump(out/'layout.json',ir);return ir

def label_translation(text):
    t=norm(text)
    if t in LABELS:return LABELS[t]
    local={
      'where':'其中','is the clipping range.':'为裁剪范围。','is the clipping range':'为裁剪范围',
      'What is the man on':'左侧男子的', 'the left holding in his':'手中拿着', 'hands?':'什么？',
      'Bbox_2d (text-space):':'Bbox_2d（文本空间）：', 'Bbox_2d (Eulidean-space):':'Bbox_2d（欧氏空间）：',
      'What is the color of the':'问题：手提包', 'handbag?':'是什么颜色？',
      'Question: What is the color of the handbag? Ground Truth: yellow':'问题：手提包是什么颜色？\n真实答案：黄色',
      'Question: Is the blue bench on the left or right side of the green door? Ground Truth: left':'问题：蓝色长椅在绿色门的左侧还是右侧？\n真实答案：左侧',
      'Question: What is cost of chemicals and supplies? Ground Truth: $485':'问题：化学品和耗材的费用是多少？\n真实答案：$485',
      'Question: What is touching the teddy bear? Ground Truth: laptop':'问题：什么东西接触着泰迪熊？\n真实答案：笔记本电脑',
      'Question: What is touching the cat? Ground Truth: umbrella':'问题：什么东西接触着猫？\n真实答案：雨伞',
      'Question: What is touching the cat? Ground Truth: donut':'问题：什么东西接触着猫？\n真实答案：甜甜圈',
      'Question: What is the table number? Ground Truth: Table II':'问题：表格编号是多少？\n真实答案：表 II',
      'Question: When is the lunch break? Ground Truth: 13.00 - 14.00':'问题：午休是什么时候？\n真实答案：13.00 - 14.00',
      'Training Progress':'训练进度','Answer Accuracy':'答案准确率','Bbox IoU':'边界框 IoU',
    }
    if t in local:return local[t]
    answers={'yellow':'黄色','white':'白色','left':'左侧','laptop':'笔记本电脑','bottle':'瓶子','umbrella':'雨伞','ball':'球','donut':'甜甜圈','cup':'杯子','Table II':'表 II','Table 12':'表 12'}
    if t.startswith('Answer:'):
        v=t.split(':',1)[1].strip();return '答案：'+answers.get(v,v)
    if t.startswith('+ Independent'):return t.replace('Independent','独立')
    if t.endswith(' loss'):return t[:-5]+' 损失'
    return None

def compile_jobs(ir,out):
    fixture_dir=Path(__file__).parent if (Path(__file__).parent/'translation_revised.txt').exists() else ROOT
    tr=translations(fixture_dir);jobs=[];unmapped=[]
    # Fix source/translation box splits, never write prose on numerical data rows.
    tr.pop('p8.b1',None);tr.pop('p8.b4',None);tr.pop('p8.b7',None)
    tr['p5.b5']='优化。给定问题 q 和输入图像 I₀，从 πθold 采样 G 条轨迹 {o⁽¹⁾,…,o⁽ᴳ⁾}，并通过公式（2）得到对应中间边界框 {b⁽¹⁾,…,b⁽ᴳ⁾}。按公式（7）计算轨迹奖励 R={R(o⁽¹⁾),…,R(o⁽ᴳ⁾)}，第 i 条轨迹各步采用以下归一化优势：'
    tr['p5.b6']='给定上述';tr['p5.b7']='重要性比值 r_t⁽ⁱ⁾(θ) 和 KL 项 KL(πθ‖πref)，优化目标如下：'
    tr['p5.b25']='SFT 目标。在拉普拉斯假设下，最大化真实坐标的对数似然等价于最小化 ℓ₁ 损失，因为 −log p(b*|μ,α)=‖μ−b*‖₁/α+常数。'
    tr['p5.b26']='因此，在 SFT 阶段，将公式（2）中的 ℓ₂² 损失替换为：'
    # Distinct answer and justification objects in the checklist.
    splits={17:{8:'回答：[是]',9:'理由：§5 讨论了本工作的局限。'},19:{1:'回答：[是]',2:'理由：项目主页链接到公开 NV-CoT 代码仓库。论文与附录描述复现实验所需的方法、数据集、训练配置和评估提示。',7:'回答：[是]',8:'理由：§4.1 报告 SFT、RL 训练设置及评估协议，附录记录数据集和评估提示。',13:'回答：[否]',14:'理由：所报告图表提供点估计，没有误差棒、置信区间或统计显著性检验。'},20:{3:'回答：[是]',4:'理由：§4.1 报告 RL 使用 32 张 A100 GPU 训练 80 次迭代，批量 256，GRPO 组大小 16，给出主要 RL 实验的硬件与规模。',9:'回答：[是]',10:'理由：实验使用既有基准数据，不招募人类参与者，论文未报告偏离 NeurIPS 伦理准则。'}}
    for pg,entries in splits.items():
        for bid,t in entries.items():tr[f'p{pg}.b{bid}']=t
    # Remove duplicated answer/justification portions when native PDF splits them.
    tr['p21.b2']='问题：是否描述为负责任发布高滥用风险数据或模型（如预训练语言模型、图像生成器、抓取数据集）所采取的防护措施？\n回答：[不适用]'
    tr['p21.b3']='理由：论文未描述发布需要防护的高风险数据集、预训练模型或部署系统。\n指南：'
    tr['p22.b3']='问题：对众包实验和人类受试者研究，是否给出提供给参与者的完整说明、适用截图及报酬（如有）的细节？\n回答：[不适用]'
    tr['p22.b4']='理由：研究使用既有数据集，不开展众包，也不从人类参与者收集新数据。\n指南：'
    tr['p23.b2']='问题：若 LLM 是核心研究方法中重要、原创或非标准的组成部分，是否说明其使用？若 LLM 仅用于写作、编辑或排版，且不影响核心方法、科学严谨性或原创性，则无需声明。\n回答：[是]'
    tr['p23.b3']='理由：§A.1 说明，在语言标注中使用 GPT-4 生成或完善训练问题、答案和推理步骤；所提方法本身见 §3。\n指南：'
    for page in ir['pages']:
        for b in page['blocks']:
            bid=b['id'];t=tr.get(bid)
            if t is None:t=label_translation(b['text'])
            if t is not None:
                box=b['bbox'].copy()
                # Mixed source blocks include a displayed equation: trim replacement to prose only.
                if bid=='p5.b3':box[3]=210
                if bid=='p9.b24':box[1]=389
                if bid=='p5.b5':box[3]=311
                # Small labels may use only their native rectangle; no font expansion onto data.
                jobs.append({'id':bid,'page':b['page'],'bbox':box,'source':b['text'],'translation':t,'font_size':b['font_size'],'bold':b['bold'],'type':b['type'],'direction':b['direction'],'method':'native-text'})
                continue
            if b['type']=='page_number':continue
            if b['type']=='formula':
                for li,l in enumerate(b['lines']):
                    for si,s in enumerate(l['spans']):
                        v=label_translation(s['text'])
                        if v:jobs.append({'id':bid+f'.l{li}.s{si}','page':b['page'],'bbox':list(s['bbox']),'source':s['text'],'translation':v,'font_size':s['size'],'bold':False,'type':'label','direction':l['dir'],'method':'formula-language-only'})
                continue
            matched=False
            for li,l in enumerate(b['lines']):
                raw=''.join(s['text'] for s in l['spans']);v=label_translation(raw)
                if v:
                    jobs.append({'id':bid+f'.l{li}','page':b['page'],'bbox':list(l['bbox']),'source':raw,'translation':v,'font_size':max(s['size'] for s in l['spans']),'bold':False,'type':'label','direction':l['dir'],'method':'native-label'});matched=True
            proper_name_block=bid=='p1.b1' or (7<=b['page']<=9 and re.sub(r'(?:[+\-]?\d[\d.%]*|[-+∆Δ†(),]|Qwen\S*|LLaVA\S*|DeepEyes\S*|NV-CoT\S*|Vis-CoT\S*|DyFo\S*|PaDT\S*|LVR\S*|UV-CoT\S*|ZoomEye\S*|RAP\S*|SFT|RL|ℓ|\s)+','',b['text'])=='')
            if not matched and not proper_name_block and len(re.findall(r'\b[a-zA-Z]{3,}\b',b['text']))>=4 and b['bbox'][2]-b['bbox'][0]>50:
                unmapped.append({'id':bid,'page':b['page'],'bbox':b['bbox'],'text':b['text'],'reason':'unmapped natural language; retained for review'})
    # Figure 2 uses outlined glyphs, not editable text. Boxes are verified against source rendering.
    for n,(box,t,rotate) in enumerate([
      ([107.0,119.0,115.0,145.1],'边界框 IoU',90),([205.1,108.5,213.5,155.0],'答案准确率',90),
      ([143.0,190.7,189.2,198.0],'训练进度',0),([241.2,190.7,287.5,198.0],'训练进度',0)]):
        jobs.append({'id':f'p2.outlined-label{n}','page':2,'bbox':box,'source':'outlined Figure 2 axis label','translation':t,'font_size':5.4,'bold':False,'type':'label','direction':[1,0],'rotate':rotate,'method':'verified-outlined-label','overlay':True})
    dump(out/'translations.json',jobs);dump(out/'unmapped.json',unmapped);return jobs,unmapped

def repair_overlapping_prose(jobs):
    """Native PDFs may split fractions into overlapping prose blocks.
    Merge only connected prose regions, never labels, tables, or display math.
    Coordinates remain their original union and all child IDs remain traceable.
    """
    result=[]
    for original in jobs:
        j=original.copy()
        while True:
            match=None
            if j['type']=='text':
                for k in result:
                    if k['page']!=j['page'] or k['type']!='text':continue
                    a=fitz.Rect(k['bbox']);b=fitz.Rect(j['bbox'])
                    if (a&b).get_area()>.2*min(a.get_area(),b.get_area()):match=k;break
            if match is None:break
            result.remove(match)
            j={**match,'bbox':rectlist(fitz.Rect(match['bbox'])|fitz.Rect(j['bbox'])),'source':match['source']+'\n'+j['source'],'translation':match['translation']+'\n'+j['translation'],'children':match.get('children',[match['id']])+j.get('children',[j['id']]),'repair_merge':'overlapping native prose boxes'}
        result.append(j)
    return result

SUP=str.maketrans('⁰¹²³⁴⁵⁶ᴳ⁻⁽⁾ⁱᵀᴰˣ','0123456G−()iTD×')
SUB=str.maketrans('₀₁₂₃₄₊ᵢᵧₜₓ','01234+iytx')
def markup(s):
    s=html.escape(s)
    s=re.sub(r'\*\*(.*?)\*\*',r'<b>\1</b>',s)
    s=re.sub(r'^#{1,2} (.*)',r'<b>\1</b>',s,flags=re.M)
    s=re.sub(r'[⁰¹²³⁴⁵⁶ᴳ⁻⁽⁾ⁱᵀᴰˣ]+',lambda m:'<sup>'+m.group().translate(SUP)+'</sup>',s)
    s=re.sub(r'[₀₁₂₃₄₊ᵢᵧₜₓ]+',lambda m:'<sub>'+m.group().translate(SUB)+'</sub>',s)
    return s.replace('\n','<br>')
CSS='''@font-face{font-family:cn;src:url(simsun.ttc)}@font-face{font-family:hei;src:url(simhei.ttf)}@font-face{font-family:latin;src:url(times.ttf)}@font-face{font-family:math;src:url(cambria.ttc)}*{margin:0;padding:0}body{font-family:cn,latin,math;letter-spacing:0;line-height:1.12;color:#000}b,strong{font-family:hei}sup,sub{font-size:.72em}'''

def render(doc,ir,jobs,out,reuse_jobs=None):
    from typography import resolve_style
    originals={b['id']:b for p in ir['pages'] for b in p['blocks']}
    for j in jobs:
        native=originals.get(j['id'])
        if native is None:continue
        plan=resolve_style(j,native,ir['pages'][j['page']-1])
        if plan:
            j['source_bbox']=j['bbox'].copy();j['bbox']=plan['bbox'];j['font_size']=plan['font_size'];j['type_style']=plan
    archive=fitz.Archive(str(FONTDIR));failures=[]
    cached=None;backing=fitz.open(SOURCE)
    if reuse_jobs is not None and (out/'NV-CoT_中文镜像.pdf').exists() and (out/'original.pdf').read_bytes()==SOURCE.read_bytes():cached=fitz.open(stream=(out/'NV-CoT_中文镜像.pdf').read_bytes(),filetype='pdf')
    def signature(xs):return json.dumps([{k:x.get(k) for k in ['id','page','bbox','source','translation','font_size','bold','type','direction','rotate','overlay','children','type_style']} for x in xs],sort_keys=True)
    for pi in range(len(doc)):
        page=doc[pi]
        active=[j for j in jobs if j['page']==pi+1]
        previous=[j for j in (reuse_jobs or []) if j['page']==pi+1]
        if cached is not None and signature(active)==signature(previous):
            doc.delete_page(pi);doc.insert_pdf(cached,from_page=pi,to_page=pi,start_at=pi)
            old={j['id']:j for j in previous}
            for j in active:
                for k in ['font_scale','spare_height','rendered','repair','restored_inline_formula']: 
                    if k in old[j['id']]:j[k]=old[j['id']][k]
            print('Reused unchanged page',pi+1,flush=True);continue
        for j in active:
            if not j.get('overlay'):
                # Adjacent PDF glyph bounding boxes can overlap despite disjoint ink.
                # Inset the deletion hit-test to avoid deleting a neighboring legend row.
                rr=fitz.Rect(j['bbox']);inset=min(1.35,rr.height*.16)
                if abs(j['direction'][1])<.9:rr.y0+=inset;rr.y1-=inset
                page.add_redact_annot(rr,fill=False,cross_out=False)
        # Text-only redaction: never delete image pixels, strokes, lines, charts, or equations.
        page.apply_redactions(images=0,graphics=0,text=0)
        for j in active:
            r=fitz.Rect(j['bbox']);fs=j['font_size']
            # Native text boxes are not used as line spacing. Font is fitted locally.
            # Titles/captions can use the original font size; no cross-object box growth.
            fs=min(fs,17)
            if j.get('overlay'):page.draw_rect(r,color=None,fill=(1,1,1),overlay=True)
            rotate=j.get('rotate',90 if abs(j['direction'][1])>.9 else 0)
            align='center' if j['type']=='heading' and (j['id']=='p1.b0' or j['id']=='p1.b3') else 'left'
            body=f'<body style="font-size:{fs}pt;text-align:{align};'+('font-family:hei;' if j['type']=='heading' or j['bold'] else '')+'">'+markup(j['translation'])+'</body>'
            local_css=CSS;scale_low=.43
            if plan:=j.get('type_style'):
                content=markup(j['translation'])
                if plan.get('panel_breaks'):content=re.sub(r'（([abc])）',r'<br>（\1）',content)
                if plan['style']=='figure_caption':content=re.sub(r'^(图\s*\d+)',r'<b>\1</b>',content)
                local_css=CSS.replace('line-height:1.12',f'line-height:{plan["line_height"]}')+'@font-face{font-family:heading;src:url(msyhbd.ttc);font-weight:700}'
                family='heading' if plan['bold'] else 'cn,latin,math'
                body=f'<body style="font-family:{family};font-size:{fs}pt;font-weight:{700 if plan["bold"] else 400};text-align:{plan["align"]};padding-top:{plan["padding_top"]}pt">{content}</body>'
                scale_low=1
            spare,scale=page.insert_htmlbox(r,body,css=local_css,archive=archive,scale_low=scale_low,rotate=rotate)
            j['font_scale']=scale;j['spare_height']=spare;j['rendered']=spare>=0
            if spare<0:
                # Retry with tighter local leading only; retain source text if even that fails.
                spare,scale=page.insert_htmlbox(r,body,css=local_css.replace('line-height:1.12','line-height:1.0'),archive=archive,scale_low=1 if j.get('type_style') else .30,rotate=rotate)
                j.update(font_scale=scale,spare_height=spare,rendered=spare>=0,repair='tightened leading')
            if spare<0:failures.append({'id':j['id'],'page':pi+1,'reason':'translation cannot fit source bounding box'})
            if j['id']=='p5.b5' and 'children' in j:
                # Restore the original inline advantage fraction, not just its rule.
                # Keep both source coordinates and exact vector glyphs; reserve its slot.
                math_rect=fitz.Rect(356,294,455.5,312)
                page.draw_rect(math_rect,color=None,fill=(1,1,1),overlay=True)
                page.show_pdf_page(math_rect,backing,4,clip=math_rect,overlay=True)
                j['restored_inline_formula']=list(math_rect)
        print('Rendered page',pi+1,flush=True)
    doc.subset_fonts();pdf=out/'NV-CoT_中文镜像.pdf';doc.save(pdf,garbage=4,deflate=True)
    dump(out/'translations.json',jobs);return pdf,failures

def validate(source,pdf,ir,jobs,unmapped,failures,out):
    a=fitz.open(source);b=fitz.open(pdf);shots=out/'screenshots';shots.mkdir(exist_ok=True)
    checks=[];formula_checks=[]
    import numpy as np
    for pi,(p,q) in enumerate(zip(a,b)):
        ap=p.get_pixmap(matrix=fitz.Matrix(1.6,1.6),alpha=False);bp=q.get_pixmap(matrix=fitz.Matrix(1.6,1.6),alpha=False)
        ap.save(shots/f'{pi+1:02d}-original.png');bp.save(shots/f'{pi+1:02d}-translated.png')
        # Pixels outside replacement masks must be exactly unchanged at the same coordinates.
        ar=np.frombuffer(ap.samples,dtype=np.uint8).reshape(ap.height,ap.width,3);br=np.frombuffer(bp.samples,dtype=np.uint8).reshape(bp.height,bp.width,3)
        mask=np.zeros(ar.shape[:2],dtype=bool)
        for j in jobs:
            if j['page']!=pi+1:continue
            x0,y0,x1,y1=j['bbox'];mask[max(0,int(y0*1.6)-3):min(ap.height,int(y1*1.6)+4),max(0,int(x0*1.6)-3):min(ap.width,int(x1*1.6)+4)]=True
        changed=(np.max(abs(ar.astype('int16')-br.astype('int16')),axis=2)>12)&~mask
        inv_changed=int(changed.sum())
        images_a=[(x['digest'].hex(),list(x['bbox'])) for x in p.get_image_info(hashes=True)]
        images_b=[(x['digest'].hex(),list(x['bbox'])) for x in q.get_image_info(hashes=True)]
        imok=all(x in images_b for x in images_a)
        for top,bottom in ir['pages'][pi]['formula_regions']:
            # Protect exact geometry of every displayed equation; compare its original pixels.
            crop=(slice(int(top*1.6),int(bottom*1.6)),slice(int(108*1.6),int(541*1.6)))
            region=~mask[crop];diff=np.max(abs(ar[crop].astype('int16')-br[crop].astype('int16')),axis=2)
            formula_checks.append({'page':pi+1,'region':[108,top,541,bottom],'changed_unmasked_pixels':int(((diff>12)&region).sum())})
        for j in jobs:
            if j['page']!=pi+1 or 'restored_inline_formula' not in j:continue
            x0,y0,x1,y1=j['restored_inline_formula'];crop=(slice(int(y0*1.6)+1,int(y1*1.6)-1),slice(int(x0*1.6)+1,int(x1*1.6)-1))
            diff=np.max(abs(ar[crop].astype('int16')-br[crop].astype('int16')),axis=2)
            formula_checks.append({'page':pi+1,'region':j['restored_inline_formula'],'kind':'restored_inline_fraction','changed_pixels':int((diff>12).sum())})
        pagejobs=[j for j in jobs if j['page']==pi+1]
        small=[j['id'] for j in pagejobs if j.get('font_scale',1)*min(j['font_size'],17)<5]
        leftovers=[u for u in unmapped if u['page']==pi+1]
        overlaps=[]
        for n,j in enumerate(pagejobs):
            for k in pagejobs[n+1:]:
                r1=fitz.Rect(j['bbox']);r2=fitz.Rect(k['bbox']);intersection=r1&r2
                if intersection.get_area()>.2*min(r1.get_area(),r2.get_area()):overlaps.append([j['id'],k['id']])
        glyph_delta=max(0,q.get_text().count('\ufffd')-p.get_text().count('\ufffd'))
        checks.append({'page':pi+1,'same_dimensions':p.rect==q.rect,'images_preserved':imok,'source_image_count':len(images_a),'drawings_source':len(p.get_drawings()),'drawings_output':len(q.get_drawings()),'outside_mask_changed_pixels':inv_changed,'overflow_count':sum(not j['rendered'] for j in pagejobs),'small_font_elements':small,'unmapped':leftovers,'replacement_count':len(pagejobs),'possible_box_overlaps':overlaps,'new_unicode_replacement_characters':glyph_delta,'status':'review' if leftovers or small or inv_changed or overlaps or glyph_delta else 'pass'})
    report={'page_count_source':len(a),'page_count_translation':len(b),'pages':checks,'formula_checks':formula_checks,'failures':failures,'limitations':['Inline mathematics in replaced prose is typeset from Unicode and needs semantic review; displayed equations remain original PDF objects.','Native text not in the translation manifest is preserved and reported, not silently deleted.','Visible overlap and font glyph quality require screenshot review; structural checks do not prove semantic translation correctness.','Figure 2 outlined axis labels use independently verified coordinates; OCR candidates are reported separately.'],'all_pages_same_size':all(p['same_dimensions'] for p in checks),'all_source_images_preserved':all(p['images_preserved'] for p in checks),'total_overflows':sum(p['overflow_count'] for p in checks),'total_unmapped':len(unmapped),'total_outside_mask_changed_pixels':sum(p['outside_mask_changed_pixels'] for p in checks)}
    dump(out/'quality.json',report);return report

def main():
    global SOURCE
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,default=SOURCE);ap.add_argument('--out',type=Path,default=ROOT/'outputs/NV-CoT_mirror');ap.add_argument('--parse-only',action='store_true');ap.add_argument('--translations-file',type=Path);ap.add_argument('--llm-url');ap.add_argument('--model');ap.add_argument('--reuse',action='store_true');args=ap.parse_args();args.out.mkdir(exist_ok=True,parents=True)
    SOURCE=args.source
    cached_jobs=json.loads((args.out/'translations.json').read_text(encoding='utf-8')) if args.reuse and (args.out/'translations.json').exists() else None
    doc=fitz.open(SOURCE);ir=parse(doc,args.out)
    if args.parse_only:return
    is_nv_cot='Thinking with Images as Continuous Actions' in ir['pages'][0]['blocks'][0]['text']
    if args.translations_file or args.llm_url:
        if args.translations_file:entries=json.loads(args.translations_file.read_text(encoding='utf-8'))
        else:
            if not args.model:ap.error('--llm-url requires --model')
            from llm_adapter import translate
            glossary={'visual chain-of-thought':'视觉思维链','grounding':'定位','bounding box':'边界框','supervised fine-tuning':'监督微调','reinforcement learning':'强化学习'}
            entries=translate(ir,glossary,args.llm_url,args.model,args.out/'llm-cache.json')
        tr={x['id']:x['translation'] for x in entries};jobs=[];unmapped=[]
        for page in ir['pages']:
            for b in page['blocks']:
                if b['id'] in tr:jobs.append({'id':b['id'],'page':b['page'],'bbox':b['bbox'],'source':b['text'],'translation':tr[b['id']],'font_size':b['font_size'],'bold':b['bold'],'type':b['type'],'direction':b['direction'],'method':'provided-manifest'})
                elif b['type'] not in ('formula','page_number'):unmapped.append({'id':b['id'],'page':b['page'],'bbox':b['bbox'],'text':b['text'],'reason':'missing translation manifest entry'})
        dump(args.out/'translations.json',jobs);dump(args.out/'unmapped.json',unmapped)
    elif is_nv_cot:jobs,unmapped=compile_jobs(ir,args.out)
    else:ap.error('Unknown source: provide --translations-file or --llm-url/--model. NV-CoT fixture will not be applied to another paper.')
    jobs=repair_overlapping_prose(jobs)
    pdf,failures=render(doc,ir,jobs,args.out,reuse_jobs=cached_jobs)
    r=validate(SOURCE,pdf,ir,jobs,unmapped,failures,args.out)
    import shutil;shutil.copyfile(SOURCE,args.out/'original.pdf')
    print(json.dumps({k:v for k,v in r.items() if k not in ['pages','formula_checks','limitations']},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
