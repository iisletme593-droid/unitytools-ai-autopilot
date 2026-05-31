import json
d=json.load(open('studio/autopilot/_triage.json',encoding='utf-8'))
print('OZET',json.dumps(d['ozet'],ensure_ascii=False))
ps=[p for p in d['secilenler'] if p['tag']=='PROBLEM'][:5]
for p in ps:
    print(p['review'].split('\')[-1],'score',p['problem_score'],'parlak',p['brightness'],'siyahblok',p['black_block'],'src',p.get('src'))
