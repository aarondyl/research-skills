"""Optional JSON chat endpoint adapter; no credentials are stored or bundled.
The NV-CoT regression uses reviewed cached translations, not a paid remote call.
For a different source, require this adapter or a complete explicit ID manifest.
"""
import json,os,urllib.request,re

PROMPT='''你是计算机科学论文的学术翻译专家。按给定全文摘要、术语表和当前页上下文翻译文本块。
只返回 JSON 对象 {"translations": [{"id": "原ID", "translation": "完整中文译文"}]}。
不省略内容，不增补结论。保护原模型名、公式、数字及引文。保留占位符。严禁修改 ID、坐标或其他元数据。
图注、标题和图内标签同样翻译；姓名和算法名保留。对不确定内容在另一个 review 字段列出。'''

def translate(ir,glossary,endpoint,model,cache_path):
    key=os.environ.get('PDF_TRANSLATION_API_KEY','')
    result=[];abstract='\n'.join(b['text'] for b in ir['pages'][0]['blocks'] if b['type']=='text')
    for page in ir['pages']:
        selected=[b for b in page['blocks'] if b['type'] in ('text','heading','caption','reference')]
        protected={};elements=[]
        for b in selected:
            tokens={};lines=[]
            for line in b['lines']:
                parts=[]
                for span in line['spans']:
                    raw=span['text']
                    if re.search(r'CM(?:MI|SY|EX)|Math|Symbol',span['font']) and raw.strip():
                        token='__MATH_'+str(len(tokens))+'__';tokens[token]=raw;parts.append(token)
                    else:parts.append(raw)
                lines.append(''.join(parts))
            protected[b['id']]=tokens;elements.append({'id':b['id'],'text':' '.join(lines),'type':b['type']})
        payload={'model':model,'temperature':0,'messages':[{'role':'system','content':PROMPT},{'role':'user','content':json.dumps({'abstract_context':abstract,'glossary':glossary,'page':page['number'],'elements':elements},ensure_ascii=False)}]}
        req=urllib.request.Request(endpoint,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json',**({'Authorization':'Bearer '+key} if key else {})})
        with urllib.request.urlopen(req,timeout=180) as resp:answer=json.load(resp)
        content=answer['choices'][0]['message']['content'].strip()
        if content.startswith('```'):content='\n'.join(content.splitlines()[1:-1])
        entries=json.loads(content)['translations'];known={b['id'] for b in selected}
        if {x['id'] for x in entries}!=known:raise ValueError('LLM response omitted, duplicated, or introduced element IDs')
        if len(entries)!=len(known):raise ValueError('Duplicate LLM element IDs')
        for entry in entries:
            for token,raw in protected[entry['id']].items():
                if entry['translation'].count(token)!=1:raise ValueError('Math placeholder lost or duplicated: '+entry['id']+' '+token)
                entry['translation']=entry['translation'].replace(token,raw)
        result.extend(entries);cache_path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result
