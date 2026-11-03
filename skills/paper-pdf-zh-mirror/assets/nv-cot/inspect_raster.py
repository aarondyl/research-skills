"""Detect text inside image carriers without altering scientific image evidence."""
from pathlib import Path
import sys,json,re
sys.path.insert(0,str(Path(__file__).parents[1]/'mupdf'))
sys.path.append(str(Path(__file__).parents[1]/'ocr'))
import pymupdf as fitz
from rapidocr_onnxruntime import RapidOCR
from PIL import Image
import numpy as np

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];out=HERE.parent if HERE.name=='system' else ROOT/'outputs/NV-CoT_mirror'
doc=fitz.open(out/'original.pdf');ocr=RapidOCR();cache={};records=[]
for pi,page in enumerate(doc):
    for n,item in enumerate(page.get_image_info(hashes=True)):
        r=fitz.Rect(item['bbox'])
        if r.width<25 or r.height<20:continue
        digest=item['digest'].hex()
        if digest not in cache:
            pix=page.get_pixmap(matrix=fitz.Matrix(4,4),clip=r)
            im=Image.frombytes('RGB',[pix.width,pix.height],pix.samples)
            result,_=ocr(np.array(im));cache[digest]=result or []
        for box,text,confidence in cache[digest]:
            if confidence<.80 or len(re.findall(r'[A-Za-z]{3,}',text))<1:continue
            records.append({'page':pi+1,'image_id':f'p{pi+1}.image{n}','image_bbox':list(r),'ocr_box_image_pixels':box,'text':text,'confidence':confidence,'action':'retained for human review; image evidence is not regenerated'})
    print('OCR page',pi+1,flush=True)
(out/'raster-review.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
print('Raster natural-language candidates:',len(records))
