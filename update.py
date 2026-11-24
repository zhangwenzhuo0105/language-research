import json, pathlib, datetime as dt, urllib.request, urllib.parse, re, xml.etree.ElementTree as ET, email.utils, html
P=pathlib.Path('data.json'); C=json.loads(pathlib.Path('sources.json').read_text()); now=dt.datetime.now(dt.timezone(dt.timedelta(hours=8))); today=now.date(); old=json.loads(P.read_text()) if P.exists() else {'items':[]}; items={x['url']:x for x in old.get('items',[]) if x.get('url')}; ok=0; errors=[]
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'LanguageResearchHub/4.0 (academic metadata reader)'}),timeout=25) as r: return r.read()
def attempt(name,fn):
    global ok
    try: fn(); ok+=1
    except Exception as e: errors.append(name); print(name, str(e),flush=True)
def add(section,typ,title,url,date,source,**extra):
    if not title or not url.startswith('https://') or not date or date>str(today): return
    items[url]={'section':section,'type':typ,'title':html.unescape(title),'url':url,'date':date,'source':source,**extra}
def papers(section,journal):
    params=urllib.parse.urlencode({'query.container-title':journal,'filter':'from-pub-date:'+str(today-dt.timedelta(days=90))+',type:journal-article','rows':30,'sort':'published','order':'desc'})
    for w in json.loads(get('https://api.crossref.org/works?'+params))['message']['items']:
        source=(w.get('container-title') or [''])[0]
        if re.sub(r'\W','',source.casefold())!=re.sub(r'\W','',journal.casefold()): continue
        if not w.get('DOI') or not w.get('title'): continue
        if re.search(r'^(editorial|correction|erratum|retraction|book review|corrigendum)\b',w['title'][0],re.I): continue
        parts=(w.get('published-online') or w.get('published') or {}).get('date-parts',[[]])[0]
        if len(parts)!=3: continue
        try: date=str(dt.date(*parts))
        except ValueError: continue
        authors=', '.join(' '.join(filter(None,[a.get('given'),a.get('family')])) for a in w.get('author',[]))
        add(section,'paper',w['title'][0],'https://doi.org/'+w['DOI'].lower(),date,source,authors=authors,note='期刊论文候选；逐篇同行评审状态尚未核验。')
def dateparse(s):
    try: return str(dt.datetime.fromisoformat(s.replace('Z','+00:00')).date())
    except ValueError:
        try: return str(email.utils.parsedate_to_datetime(s).date())
        except Exception: return None
def feed(f,url):
    root=ET.fromstring(get(url))
    for e in root.iter():
        if e.tag.split('}')[-1] not in ('item','entry'): continue
        def val(*names):
            for c in e:
                if c.tag.split('}')[-1] in names: return ''.join(c.itertext()).strip()
            return ''
        title=val('title'); link=val('link')
        if not link:
            link=next((c.get('href','') for c in e if c.tag.split('}')[-1]=='link' and c.get('rel','alternate')=='alternate'),'')
        date=dateparse(val('pubDate','published','date'))
        if not date or date<str(today-dt.timedelta(days=180)): continue
        if f.get('keywords') and not any(k in title.lower() for k in f['keywords']): continue
        add(f['section'],f['type'],title,link,date,f['source'],note='机构或作者订阅源；请以原文为准。')
def video(f):
    page=get('https://www.youtube.com/'+f['handle']).decode('utf-8','replace'); m=re.search(r'<meta[^>]+itemprop="channelId"[^>]+content="(UC[\w-]+)"',page) or re.search(r'"externalId":"(UC[\w-]+)"',page)
    if not m: raise ValueError('Channel ID unavailable; configure verified channel ID')
    feed(dict(f,type='video'),'https://www.youtube.com/feeds/videos.xml?channel_id='+m[1])
for section,journals in C['journals'].items():
    for journal in journals: attempt(journal,lambda:papers(section,journal))
for f in C['feeds']: attempt(f['source'],lambda:feed(f,f['url']))
for f in C['video_channels']: attempt(f['source'],lambda:video(f))
if not ok: raise SystemExit('All sources failed; previous data preserved')
result={'checked':now.isoformat(timespec='minutes'),'failed_sources':errors,'successful_sources':ok,'items':sorted(items.values(),key=lambda x:x.get('date',''),reverse=True)}
tmp=P.with_suffix('.tmp'); tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n'); tmp.replace(P)
