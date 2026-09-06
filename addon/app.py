import os,re,urllib.parse,struct
from flask import Flask,jsonify,request
import requests

app=Flask(__name__)
ROOT='/downloads/complete'
VIDEO_EXT={'.mp4','.mkv','.avi','.mov','.m4v','.webm','.ts','.m2ts','.wmv','.flv'}
HASH_CHUNK=64*1024
MASK64=0xFFFFFFFFFFFFFFFF

MANIFEST={
 'id':'community.pitorrent.lan',
 'version':'0.1.3',
 'name':'PiTorrent LAN',
 'description':'Streams completed PiTorrent files from the local Raspberry Pi.',
 'resources':[{'name':'stream','types':['movie','series'],'idPrefixes':['tt']}],
 'types':['movie','series'],
 'catalogs':[],
 'behaviorHints':{'configurable':False}
}

def norm(s):
 s=(s or '').lower()
 s=re.sub(r'[^a-z0-9]+',' ',s)
 return ' '.join(s.split())

def safe_name(s):
 s=(s or '').strip()
 s=re.sub(r'[^A-Za-z0-9]+','.',s)
 return s.strip('.')

def video_files():
 out=[]
 if not os.path.isdir(ROOT): return out
 for base,_,files in os.walk(ROOT):
  for fn in files:
   if os.path.splitext(fn)[1].lower() in VIDEO_EXT:
    p=os.path.join(base,fn)
    try: size=os.path.getsize(p)
    except OSError: continue
    out.append((p,fn,size))
 return out

def opensubtitles_hash(path,size=None):
 try:
  if size is None: size=os.path.getsize(path)
  if size < HASH_CHUNK*2: return None
  h=size & MASK64
  with open(path,'rb') as f:
   first=f.read(HASH_CHUNK)
   f.seek(size-HASH_CHUNK)
   last=f.read(HASH_CHUNK)
  for block in (first,last):
   usable=len(block)-(len(block)%8)
   for i in range(0,usable,8):
    h=(h+struct.unpack_from('<Q',block,i)[0]) & MASK64
  return f'{h:016x}'
 except (OSError,ValueError,struct.error):
  return None

def fetch_meta(kind,meta_id):
 try:
  url=f'https://v3-cinemeta.strem.io/meta/{kind}/{urllib.parse.quote(meta_id,safe="")}.json'
  r=requests.get(url,timeout=8)
  if r.ok:
   return (r.json() or {}).get('meta') or {}
 except Exception:
  pass
 return {}

def content_info(kind,content_id):
 season=None; episode=None
 meta_id=content_id
 if kind=='series' and ':' in content_id:
  parts=content_id.split(':')
  meta_id=parts[0]
  if len(parts)>=3:
   try: season=int(parts[1]); episode=int(parts[2])
   except (ValueError,TypeError): pass
 meta=fetch_meta(kind,meta_id)
 title=meta.get('name') or ''
 ep_title=''
 if kind=='series' and season is not None and episode is not None:
  for v in meta.get('videos') or []:
   if str(v.get('id'))==content_id or (v.get('season')==season and v.get('episode')==episode):
    ep_title=v.get('title') or v.get('name') or ''
    break
 return meta,title,ep_title,season,episode

def choose_file(kind,content_id):
 files=video_files()
 if not files: return None
 meta,title,ep_title,season,episode=content_info(kind,content_id)
 nt,ne=norm(title),norm(ep_title)
 best=None; score=-1
 for p,fn,size in files:
  hay=norm(p)
  raw=' '+p.lower()+' '
  s=0
  if nt and nt in hay: s+=30
  if ne and ne in hay: s+=100
  if season is not None and episode is not None:
   patterns=[f's{season:02d}e{episode:02d}',f's{season}e{episode}']
   if any(x in raw for x in patterns): s+=70
   weak=[f' ep{episode:02d} ',f' ep{episode} ']
   if any(x in raw for x in weak): s+=10
  if s>score:
   best=(p,fn,size); score=s
 threshold=60 if kind=='series' else 25
 return best if score>=threshold else None

def subtitle_filename(kind,content_id,real_filename):
 ext=os.path.splitext(real_filename)[1].lower() or '.mp4'
 meta,title,ep_title,season,episode=content_info(kind,content_id)
 if kind=='series' and season is not None and episode is not None:
  parts=[safe_name(title),f'S{season:02d}E{episode:02d}',safe_name(ep_title)]
  name='.'.join(x for x in parts if x)
  return (name or os.path.splitext(real_filename)[0])+ext
 if kind=='movie':
  year=meta.get('year') or meta.get('releaseInfo') or ''
  parts=[safe_name(title),safe_name(str(year))]
  name='.'.join(x for x in parts if x)
  return (name or os.path.splitext(real_filename)[0])+ext
 return real_filename

@app.after_request
def cors(resp):
 resp.headers['Access-Control-Allow-Origin']='*'
 resp.headers['Access-Control-Allow-Headers']='*'
 resp.headers['Access-Control-Allow-Methods']='GET,HEAD,OPTIONS'
 resp.headers['Cache-Control']='no-store'
 return resp

@app.get('/manifest.json')
def manifest(): return jsonify(MANIFEST)

@app.get('/stream/<kind>/<path:content_id>.json')
def stream(kind,content_id):
 if kind not in ('movie','series'): return jsonify({'streams':[]})
 found=choose_file(kind,content_id)
 if not found: return jsonify({'streams':[]})
 p,fn,size=found
 rel=os.path.relpath(p,ROOT).replace(os.sep,'/')
 host=request.headers.get('X-Forwarded-Host') or request.headers.get('Host')
 proto=request.headers.get('X-Forwarded-Proto') or 'http'
 url=f'{proto}://{host}/media/{urllib.parse.quote(rel)}'
 hints={
  'filename':subtitle_filename(kind,content_id,fn),
  'videoSize':size,
  'notWebReady':True
 }
 vhash=opensubtitles_hash(p,size)
 if vhash:
  hints['videoHash']=vhash
 return jsonify({'streams':[{
  'name':'PiTorrent LAN',
  'description':f'Local • {fn}',
  'url':url,
  'behaviorHints':hints
 }]})

@app.get('/health')
def health(): return jsonify({'ok':True,'files':len(video_files())})

app.run(host='0.0.0.0',port=7000)
