import json, urllib.request, urllib.parse, datetime, pathlib
p=pathlib.Path('data.json'); d=json.loads(p.read_text()); items={x['url']:x for x in d['items']}; today=datetime.date.today(); successes=0
queries={'二语习得':'second language acquisition usage based language learning','中文教育':'Chinese as a second language teaching writing','AI语言教学':'generative artificial intelligence second language learning','语言学理论':'construction grammar second language acquisition dynamic assessment'}
for category,query in queries.items():
    params=urllib.parse.urlencode({'query.bibliographic':query,'filter':'from-pub-date:'+str(today-datetime.timedelta(days=30))+',type:journal-article','rows':8,'sort':'relevance'})
    try:
        req=urllib.request.Request('https://api.crossref.org/works?'+params,headers={'User-Agent':'LanguageResearchHub/1.0'})
        with urllib.request.urlopen(req,timeout=40) as r: works=json.load(r)['message']['items']
        successes+=1
        for w in works:
            parts=w.get('published',{}).get('date-parts',[[]])[0]
            if len(parts)!=3 or not w.get('DOI') or not w.get('title'): continue
            date=datetime.date(*parts)
            if date>today: continue
            url='https://doi.org/'+w['DOI'].lower(); authors=', '.join(' '.join(filter(None,[a.get('given'),a.get('family')])) for a in w.get('author',[]));items[url]={'title':w['title'][0],'date':str(date),'category':category,'url':url,'authors':authors,'description':'来源：'+(w.get('container-title') or ['Crossref'])[0]+'。自动检索候选文献，相关性及研究结论待人工核查。'}
    except Exception as e: print(category,e)
if not successes: raise SystemExit('All sources failed; preserving previous data')
d={'checked':str(today),'items':sorted(items.values(),key=lambda x:x['date'],reverse=True)};p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
