"""Conservative PDF mirror primitives; semantic translation is supplied by the agent."""
import argparse
import hashlib
import html
import json
import re
from pathlib import Path
import pymupdf as fitz
import numpy as np

STYLES = {'section_heading': (12.5, 1.08), 'subsection_heading': (10.75, 1.08),
          'subsubsection_heading': (9.75, 1.08), 'figure_caption': (8.5, 1.2),
          'body_text': (None, 1.12), 'table_caption': (None, 1.12), 'equation': (None, 1.12)}
CSS = '''@font-face{font-family:cn;src:url(simsun.ttc)}
@font-face{font-family:latin;src:url(times.ttf)}
@font-face{font-family:math;src:url(cambria.ttc)}
@font-face{font-family:heading;src:url(msyhbd.ttc);font-weight:700}
*{margin:0;padding:0}body{font-family:cn,latin,math;letter-spacing:0;color:#000}'''

def dump(path, value):
    def encode(x):
        if isinstance(x, bytes): return x.hex()
        if isinstance(x, (fitz.Rect, fitz.Point, fitz.Quad)): return list(x)
        raise TypeError(type(x).__name__)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=encode), encoding='utf-8')

def parse(source, out):
    pages, entries = [], []
    with fitz.open(source) as doc:
        for i, page in enumerate(doc):
            blocks = []
            for b in page.get_text('dict')['blocks']:
                if b['type'] != 0: continue
                spans = [s for line in b['lines'] for s in line['spans']]
                text = '\n'.join(''.join(s['text'] for s in line['spans']) for line in b['lines'])
                bid = f'p{i+1}.b{b["number"]}'
                size = max(s['size'] for s in spans)
                math = any(re.search(r'CM(?:MI|SY|EX)|Math|Symbol', s['font']) for s in spans)
                kind = 'figure_caption' if re.match(r'^Figure\s+\d', text) else 'table_caption' if re.match(r'^Table\s+\d', text) else 'body_text'
                blocks.append(dict(id=bid, bbox=b['bbox'], text=text, lines=b['lines'], font_size=size,
                                   math_font_detected=math, suggested_style=kind))
                entries.append(dict(id=bid, action='pending', translation='', style=kind,
                                    font_size=None, line_height=None))
            images = page.get_image_info(hashes=True)
            drawings = page.get_drawings()
            pages.append(dict(number=i+1, size=list(page.rect), mediabox=list(page.mediabox),
                              cropbox=list(page.cropbox), rotation=page.rotation, blocks=blocks,
                              images=images, drawings=drawings))
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    ir = dict(schema='paper-mirror/1', source_sha256=digest, pages=pages)
    dump(out/'layout.json', ir)
    dump(out/'manifest.template.json', dict(source_sha256=digest, entries=entries))
    return ir

def render(source, out, manifest, fonts):
    ir = parse(source, out)
    data = json.loads(manifest.read_text(encoding='utf-8'))
    if data['source_sha256'] != ir['source_sha256']: raise ValueError('Manifest belongs to a different source PDF')
    entries = data['entries']
    known = {b['id'] for p in ir['pages'] for b in p['blocks']}
    if len({e['id'] for e in entries}) != len(entries): raise ValueError('Duplicate element IDs')
    if {e['id'] for e in entries} != known: raise ValueError('Manifest must account for every native text block')
    for e in entries:
        if e['action'] not in ('translate', 'preserve'): raise ValueError('Resolve pending entry: '+e['id'])
        if e['action']=='preserve' and not e.get('reason'): raise ValueError('Preservation requires a reason: '+e['id'])
        if e['action']=='translate' and not e.get('translation','').strip(): raise ValueError('Empty translation: '+e['id'])
        if e.get('style') not in STYLES: raise ValueError('Unknown style: '+e['id'])
    for f in ('simsun.ttc','times.ttf','cambria.ttc','msyhbd.ttc'):
        if not (fonts/f).is_file(): raise FileNotFoundError('Configure font mapping: '+str(fonts/f))
    lookup = {e['id']:e for e in entries}
    doc = fitz.open(source)
    archive = fitz.Archive(str(fonts))
    applied, review = [], []
    for pageinfo, page in zip(ir['pages'], doc):
        for b in pageinfo['blocks']:
            e=lookup[b['id']]
            if e['action']=='preserve':
                review.append(dict(id=b['id'],reason=e['reason'],status='preserved')); continue
            r=fitz.Rect(e.get('bbox', b['bbox']))
            src=fitz.Rect(b['bbox'])
            reason=None
            if page.rotation: reason='Rotated page requires coordinate normalization'
            elif b['math_font_detected']: reason='Split mixed mathematics and preserve original math objects before replacement'
            elif any(abs(line['dir'][0]-1)>.01 or abs(line['dir'][1])>.01 for line in b['lines']): reason='Rotated text requires dedicated placement'
            elif not page.rect.contains(r) or r.is_empty: reason='Replacement box outside page or empty'
            elif any(src.intersects(fitz.Rect(im['bbox'])) or r.intersects(fitz.Rect(im['bbox'])) for im in pageinfo['images']): reason='Image overlap requires verified label-specific handling'
            elif any(other['id']!=b['id'] and (r.intersects(fitz.Rect(other['bbox'])) or src.intersects(fitz.Rect(other['bbox']))) for other in pageinfo['blocks']): reason='Intersecting source or destination text boxes require splitting/review'
            if reason:
                review.append(dict(id=b['id'],reason=reason,status='not_translated')); continue
            fs, lh=STYLES[e['style']]
            fs=e.get('font_size') or fs or b['font_size']
            lh=e.get('line_height') or lh
            if fs<=0 or lh<=0: raise ValueError('Invalid typography: '+b['id'])
            heading=e['style'].endswith('heading')
            content=html.escape(e['translation']).replace('\n','<br>')
            if e['style']=='figure_caption': content=re.sub(r'^(图\s*\d+)',r'<b>\1</b>',content)
            body=f'<body style="font-size:{fs}pt;line-height:{lh};'+('font-family:heading;font-weight:700;' if heading else '')+'">'+content+'</body>'
            # Trial on an isolated blank page before deleting any source content.
            with fitz.open() as trial:
                tp=trial.new_page(width=page.rect.width,height=page.rect.height)
                spare, scale=tp.insert_htmlbox(r,body,css=CSS,archive=archive,scale_low=1)
            if spare<0:
                review.append(dict(id=b['id'],reason='Text does not fit at requested size; source retained',status='not_translated')); continue
            page.add_redact_annot(src,fill=False,cross_out=False)
            page.apply_redactions(images=0,graphics=0,text=0)
            spare,scale=page.insert_htmlbox(r,body,css=CSS,archive=archive,scale_low=1)
            if spare<0: raise RuntimeError('Unexpected placement failure; no PDF saved')
            applied.append(dict(id=b['id'],page=page.number+1,source_bbox=list(src),bbox=list(r),font_size=fs,font_scale=scale))
    target=out/'translated.pdf'
    if target.exists(): raise FileExistsError('Use a fresh output directory; translated.pdf already exists')
    doc.save(target,garbage=4,deflate=True);doc.close()
    checks=[];shots=out/'screenshots';shots.mkdir(exist_ok=True)
    with fitz.open(source) as a, fitz.open(target) as z:
        for i,(p,q) in enumerate(zip(a,z)):
            ap=p.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False)
            bp=q.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False)
            ap.save(shots/f'{i+1:02d}-original.png');bp.save(shots/f'{i+1:02d}-translated.png')
            aa=np.frombuffer(ap.samples,np.uint8).reshape(ap.height,ap.width,3)
            bb=np.frombuffer(bp.samples,np.uint8).reshape(bp.height,bp.width,3)
            mask=np.zeros(aa.shape[:2],bool)
            for job in applied:
                if job['page']!=i+1: continue
                r=fitz.Rect(job['bbox'])|fitz.Rect(job['source_bbox'])
                mask[max(0,int(r.y0*2)-4):min(ap.height,int(r.y1*2)+5),max(0,int(r.x0*2)-4):min(ap.width,int(r.x1*2)+5)]=True
            changed=int(((np.max(abs(aa.astype('int16')-bb.astype('int16')),axis=2)>12)&~mask).sum())
            def images(pg): return sorted((x['digest'].hex(),tuple(x['bbox'])) for x in pg.get_image_info(hashes=True))
            checks.append(dict(page=i+1,dimensions_unchanged=p.rect==q.rect and p.cropbox==q.cropbox and p.rotation==q.rotation,
                               images_unchanged=images(p)==images(q),outside_mask_changed_pixels=changed))
        report=dict(page_count_source=len(a),page_count_translation=len(z),pages=checks,applied=applied,review=review,
                    auto_checks_passed=len(a)==len(z) and all(c['dimensions_unchanged'] and c['images_unchanged'] and not c['outside_mask_changed_pixels'] for c in checks) and not any(r['status']=='not_translated' for r in review),
                    manual_checks_required=['translation fidelity','figure raster/outlined labels','formula regions including inside masks','glyph quality and visual overlap'])
    dump(out/'quality.json',report)
    print(json.dumps(dict(pdf=str(target),translated=len(applied),review=len(review),auto_checks_passed=report['auto_checks_passed']),ensure_ascii=False))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('command',choices=['parse','render']);ap.add_argument('--source',required=True,type=Path)
    ap.add_argument('--out',required=True,type=Path);ap.add_argument('--manifest',type=Path);ap.add_argument('--fonts',type=Path)
    args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    if args.command=='parse': parse(args.source,args.out)
    else:
        if not args.manifest or not args.fonts: ap.error('render requires --manifest and --fonts')
        render(args.source,args.out,args.manifest,args.fonts)

if __name__=='__main__': main()
