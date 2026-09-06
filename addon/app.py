import os,re,urllib.parse
from flask import Flask,jsonify,request
import requests

app=Flask(__name__)
ROOT='/downloads/complete'
VIDEO_EXT={'.mp4','.mkv','.avi','.mov','.m4v','.webm','.ts','.m2ts','.wmv','.flv'}

MANIFEST={
 'id':'community.pitorrent.lan',
 'version':'0.1.1',
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

def fetch_meta(kind,meta_id):
 try:
  url=f'https://v3-cinemeta.strem.io/meta/{kind}/{urllib.parse.quote(meta_id,safe="")}.json'
  r=requests.get(url,timeout=8)
  if r.ok:
   return (r.json() or {}).get('meta') or {}
 except Exception:
  pass
 return {}

def choose_file(kind,content_id):
 files=video_files()
 if not files: return None

 season=None; episode=None
 meta_id=content_id
 if kind=='series' and ':' in content_id:
  parts=content_id.split(':')
  meta_id=parts[0]
  if len(parts)>=3:
   try: season=int(parts[1]); episode=int(parts[2])
   except (ValueError,TypeError): pass

 # Cinemeta meta endpoint expects the SERIES id, not the episode video id.
 meta=fetch_meta(kind,meta_id)
 title=meta.get('name') or ''
 ep_title=''
 if kind=='series' and season is not None and episode is not None:
  for v in meta.get('videos') or []:
   if str(v.get('id'))==content_id or (v.get('season')==season and v.get('episode')==episode):
    ep_title=v.get('title') or v.get('name') or ''
    break

 nt,ne=norm(title),norm(ep_title)
 best=None; score=-1
 for p,fn,size in files:
  hay=norm(p)
  raw=' '+p.lower()+' '
  s=0
  if nt and nt in hay: s+=30
  # Episode title is the strongest match. This also handles torrents using
  # absolute episode numbering (e.g. Ep41) while Nuvio requests S7E6.
  if ne and ne in hay: s+=100
  if season is not None and episode is not None:
   patterns=[f's{season:02d}e{episode:02d}',f's{season}e{episode}']
   if any(x in raw for x in patterns): s+=70
   # Only use EpNN as a weak fallback because many collection torrents use
   # absolute episode numbering rather than season-relative numbering.
   weak=[f' ep{episode:02d} ',f' ep{episode} ']
   if any(x in raw for x in weak): s+=10
  if s>score:
   best=(p,fn,size); score=s

 # For series, require an episode-specific match; matching only the show title
 # must never return the wrong local episode.
 threshold=60 if kind=='series' else 25
 return best if score>=threshold else None

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
 return jsonify({'streams':[{
  'name':'PiTorrent LAN',
  'description':f'Local • {fn}',
  'url':url,
  'behaviorHints':{
   'filename':fn,
   'videoSize':size,
   'notWebReady':True
  }
 }]})

@app.get('/health')
def health(): return jsonify({'ok':True,'files':len(video_files())})

app.run(host='0.0.0.0',port=7000)
