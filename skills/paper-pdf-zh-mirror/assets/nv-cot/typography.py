"""Independent local type styles. Body text and mathematical layout are untouched.

Heading eligibility requires the parsed structural role AND original bold style.
The native font-size tiers determine level, not a leading chapter number.
"""
import re
import pymupdf as fitz

STYLES={
    'section_heading':{'font_size':12.5,'line_height':1.08,'bold':True},
    'subsection_heading':{'font_size':10.75,'line_height':1.08,'bold':True},
    'subsubsection_heading':{'font_size':9.75,'line_height':1.08,'bold':True},
    'body_text':{'font_size':None,'line_height':None,'bold':None},
    'figure_caption':{'font_size':8.5,'line_height':1.20,'bold':False},
    'table_caption':{'font_size':None,'line_height':None,'bold':None},
    'equation':{'font_size':None,'line_height':None,'bold':None},
}

def element_style(native):
    if re.match(r'^Figure\s+\d+\s*:',native['text']):return 'figure_caption'
    if re.match(r'^Table\s+\d+\s*:',native['text']):return 'table_caption'
    if native['type']=='formula':return 'equation'
    if native['type']!='heading':return 'body_text'
    spans=[s for l in native['lines'] for s in l['spans']]
    bold_chars=sum(len(s['text']) for s in spans if s['flags']&16)
    if bold_chars<.5*sum(len(s['text']) for s in spans):return 'body_text'
    explicit=native.get('heading_level')
    if explicit:return {1:'section_heading',2:'subsection_heading',3:'subsubsection_heading'}.get(explicit,'subsubsection_heading')
    original_size=native['font_size']
    return 'section_heading' if original_size>=11.5 else 'subsection_heading' if original_size>=9.5 else 'subsubsection_heading'

def resolve_style(job,native,page):
    name=element_style(native);config=STYLES[name]
    if config['font_size'] is None:return None
    r=fitz.Rect(job['bbox']);size=config['font_size']
    plan={'style':name,**config,'bbox':list(r),'padding_top':0,'align':'left'}
    if name.endswith('heading'):
        # Source titles were laid out as tightly cropped English glyph bounds.
        # Use adjacent whitespace rather than shrinking the Chinese title.
        if job['id']=='p1.b3':plan['align']='center'
        else:r.x1=max(r.x1,min(page['size'][0]-108,505.8))
        r.y0-=.5;r.y1=r.y0+size*1.48
        for b in page['blocks']:
            s=fitz.Rect(b['bbox'])
            if b['id']==native['id'] or s.y0<native['bbox'][3]:continue
            if min(r.x1,s.x1)>max(r.x0,s.x0):r.y1=min(r.y1,s.y0-2)
        plan['bbox']=list(r)
    elif name=='figure_caption':
        if r.height<23:plan.update(font_size=8.25,line_height=1.10)
        # Short, full-width panel captions retain semantic breaks to avoid a
        # disproportionately large new gap above the next fixed-position title.
        plan['panel_breaks']=job['id']=='p1.b27'
        # The long sidebar keeps its original bounding box, beside Figure 2.
        if r.x0>page['size'][0]/2 and r.height>100:plan['padding_top']=6
    return plan
