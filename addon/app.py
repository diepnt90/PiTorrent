import os,re,urllib.parse,struct,json,uuid
from flask import Flask,jsonify,request,send_from_directory,Response
from werkzeug.utils import secure_filename
import requests

app=Flask(__name__)
ROOT='/downloads/complete'
SUB_ROOT='/data/subtitles'
SUB_FILES=os.path.join(SUB_ROOT,'files')
SUB_MAP=os.path.join(SUB_ROOT,'mappings.json')
TRANSMISSION_RPC=os.environ.get('TRANSMISSION_RPC','http://transmission:9091/transmission/rpc')
VIDEO_EXT={'.mp4','.mkv','.avi','.mov','.m4v','.webm','.ts','.m2ts','.wmv','.flv'}
SUB_EXT={'.srt','.vtt','.ass','.ssa'}
HASH_CHUNK=64*1024
MASK64=0xFFFFFFFFFFFFFFFF
os.makedirs(SUB_FILES,exist_ok=True)

MANIFEST={
 'id':'community.pitorrent.lan','version':'0.3.0','name':'PiTorrent LAN',
 'description':'Streams completed PiTorrent files and their subtitles from the local Raspberry Pi.',
 'resources':[
  {'name':'stream','types':['movie','series'],'idPrefixes':['tt']},
  {'name':'subtitles','types':['movie','series'],'idPrefixes':['tt']}
 ],
 'types':['movie','series'],'catalogs':[],'behaviorHints':{'configurable':False,'p2p':True}
}

def norm(s):
 s=(s or '').lower(); s=re.sub(r'[^a-z0-9]+',' ',s); return ' '.join(s.split())

def safe_name(s):
 s=(s or '').strip(); s=re.sub(r'[^A-Za-z0-9]+','.',s); return s.strip('.')

def clean_rel(rel):
 rel=urllib.parse.unquote(rel or '').replace('\\','/').lstrip('/')
 p=os.path.realpath(os.path.join(ROOT,rel))
 root=os.path.realpath(ROOT)+os.sep
 if not p.startswith(root): return None
 return os.path.relpath(p,ROOT).replace(os.sep,'/')

def load_map():
 try:
  with open(SUB_MAP,'r',encoding='utf-8') as f: return json.load(f)
 except Exception: return {}

def save_map(data):
 os.makedirs(SUB_ROOT,exist_ok=True)
 tmp=SUB_MAP+'.tmp'
 with open(tmp,'w',encoding='utf-8') as f: json.dump(data,f,ensure_ascii=False,indent=2)
 os.replace(tmp,SUB_MAP)

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
   first=f.read(HASH_CHUNK); f.seek(size-HASH_CHUNK); last=f.read(HASH_CHUNK)
  for block in (first,last):
   usable=len(block)-(len(block)%8)
   for i in range(0,usable,8): h=(h+struct.unpack_from('<Q',block,i)[0]) & MASK64
  return f'{h:016x}'
 except (OSError,ValueError,struct.error): return None

def transmission_call(method,arguments=None):
 headers={'Content-Type':'application/json'}
 payload={'method':method,'arguments':arguments or {}}
 try:
  r=requests.post(TRANSMISSION_RPC,json=payload,headers=headers,timeout=5)
  if r.status_code==409:
   sid=r.headers.get('X-Transmission-Session-Id')
   if not sid: return None
   headers['X-Transmission-Session-Id']=sid
   r=requests.post(TRANSMISSION_RPC,json=payload,headers=headers,timeout=5)
  if not r.ok: return None
  data=r.json()
  if data.get('result')!='success': return None
  return data.get('arguments') or {}
 except Exception:
  return None

def torrent_source_for_file(path):
 rel=os.path.relpath(path,ROOT).replace(os.sep,'/').lstrip('/')
 data=transmission_call('torrent-get',{'fields':['id','hashString','name','downloadDir','files']})
 if not data: return None
 candidates=[]
 for t in data.get('torrents') or []:
  for idx,f in enumerate(t.get('files') or []):
   fname=(f.get('name') or '').replace('\\','/').lstrip('/')
   # Transmission file names are normally relative to downloadDir. Match exact
   # PiTorrent relative path first, then allow a unique suffix match.
   if fname==rel:
    return t.get('hashString'),idx,fname
   if rel.endswith('/'+fname) or fname.endswith('/'+rel):
    candidates.append((t.get('hashString'),idx,fname))
   elif os.path.basename(fname)==os.path.basename(rel):
    candidates.append((t.get('hashString'),idx,fname))
 if len(candidates)==1: return candidates[0]
 return None

def fetch_meta(kind,meta_id):
 try:
  url=f'https://v3-cinemeta.strem.io/meta/{kind}/{urllib.parse.quote(meta_id,safe="")}.json'
  r=requests.get(url,timeout=8)
  if r.ok: return (r.json() or {}).get('meta') or {}
 except Exception: pass
 return {}

def content_info(kind,content_id):
 season=None; episode=None; meta_id=content_id
 if kind=='series' and ':' in content_id:
  parts=content_id.split(':'); meta_id=parts[0]
  if len(parts)>=3:
   try: season=int(parts[1]); episode=int(parts[2])
   except (ValueError,TypeError): pass
 meta=fetch_meta(kind,meta_id); title=meta.get('name') or ''; ep_title=''
 if kind=='series' and season is not None and episode is not None:
  for v in meta.get('videos') or []:
   if str(v.get('id'))==content_id or (v.get('season')==season and v.get('episode')==episode):
    ep_title=v.get('title') or v.get('name') or ''; break
 return meta,title,ep_title,season,episode

def choose_file(kind,content_id):
 files=video_files()
 if not files: return None
 meta,title,ep_title,season,episode=content_info(kind,content_id); nt,ne=norm(title),norm(ep_title)
 best=None; score=-1
 for p,fn,size in files:
  hay=norm(p); raw=' '+p.lower()+' '; s=0
  if nt and nt in hay: s+=30
  if ne and ne in hay: s+=100
  if season is not None and episode is not None:
   if any(x in raw for x in [f's{season:02d}e{episode:02d}',f's{season}e{episode}']): s+=70
   if any(x in raw for x in [f' ep{episode:02d} ',f' ep{episode} ']): s+=10
  if s>score: best=(p,fn,size); score=s
 return best if score >= (60 if kind=='series' else 25) else None

def subtitle_filename(kind,content_id,real_filename):
 ext=os.path.splitext(real_filename)[1].lower() or '.mp4'; meta,title,ep_title,season,episode=content_info(kind,content_id)
 if kind=='series' and season is not None and episode is not None:
  name='.'.join(x for x in [safe_name(title),f'S{season:02d}E{episode:02d}',safe_name(ep_title)] if x)
  return (name or os.path.splitext(real_filename)[0])+ext
 if kind=='movie':
  year=meta.get('year') or meta.get('releaseInfo') or ''
  name='.'.join(x for x in [safe_name(title),safe_name(str(year))] if x)
  return (name or os.path.splitext(real_filename)[0])+ext
 return real_filename

def external_base():
 host=request.headers.get('X-Forwarded-Host') or request.headers.get('Host')
 proto=request.headers.get('X-Forwarded-Proto') or 'http'
 return f'{proto}://{host}'

def subtitle_to_vtt(text):
 text=(text or '').replace('\r\n','\n').replace('\r','\n').lstrip('\ufeff')
 if text.lstrip().startswith('WEBVTT'): return text
 lines=text.split('\n'); out=['WEBVTT','']
 for line in lines:
  if '-->' in line:
   line=re.sub(r'(\d{2}:\d{2}:\d{2}),(\d{3})',r'\1.\2',line)
  out.append(line)
 return '\n'.join(out)

@app.after_request
def cors(resp):
 resp.headers['Access-Control-Allow-Origin']='*'; resp.headers['Access-Control-Allow-Headers']='*'; resp.headers['Access-Control-Allow-Methods']='GET,HEAD,OPTIONS,POST,DELETE'; resp.headers['Cache-Control']='no-store'; return resp

@app.get('/manifest.json')
def manifest(): return jsonify(MANIFEST)

@app.get('/stream/<kind>/<path:content_id>.json')
def stream(kind,content_id):
 if kind not in ('movie','series'): return jsonify({'streams':[]})
 found=choose_file(kind,content_id)
 if not found: return jsonify({'streams':[]})
 p,fn,size=found
 source=torrent_source_for_file(p)
 if not source: return jsonify({'streams':[]})
 info_hash,file_idx,torrent_filename=source
 hints={'filename':subtitle_filename(kind,content_id,fn),'bingeGroup':f'pitorrent|{info_hash.lower()}'}
 return jsonify({'streams':[{
  'name':'PiTorrent LAN',
  'description':f'Local completed • {fn}',
  'infoHash':info_hash.lower(),
  'fileIdx':file_idx,
  'behaviorHints':hints
 }]})

@app.get('/subtitles/<kind>/<path:content_id>.json')
def subtitles(kind,content_id):
 if kind not in ('movie','series'): return jsonify({'subtitles':[]})
 found=choose_file(kind,content_id)
 if not found: return jsonify({'subtitles':[]})
 p,fn,size=found; rel=os.path.relpath(p,ROOT).replace(os.sep,'/')
 entries=load_map().get(rel,[]); out=[]
 for i,e in enumerate(entries):
  url=e.get('url')
  if e.get('file'): url=f'{external_base()}/subtitle-files/{urllib.parse.quote(e["file"])}'
  if url: out.append({'id':e.get('id') or f'pitorrent-{i}','lang':e.get('lang') or 'eng','url':url})
 return jsonify({'subtitles':out})

@app.get('/subtitle-api')
def subtitle_get():
 rel=clean_rel(request.args.get('file'))
 if rel is None: return jsonify({'error':'invalid file'}),400
 return jsonify({'file':rel,'subtitles':load_map().get(rel,[])})

@app.post('/subtitle-api')
def subtitle_add():
 rel=clean_rel(request.form.get('file'))
 if rel is None or not os.path.isfile(os.path.join(ROOT,rel)): return jsonify({'error':'video file not found'}),400
 lang=(request.form.get('lang') or 'eng').strip() or 'eng'; url=(request.form.get('url') or '').strip(); upload=request.files.get('upload')
 entry={'id':uuid.uuid4().hex[:12],'lang':lang}
 if upload and upload.filename:
  ext=os.path.splitext(upload.filename)[1].lower()
  if ext not in SUB_EXT: return jsonify({'error':'subtitle must be .srt, .vtt, .ass or .ssa'}),400
  stored=entry['id']+'-'+secure_filename(upload.filename); upload.save(os.path.join(SUB_FILES,stored)); entry['file']=stored; entry['name']=upload.filename
 elif url:
  if not re.match(r'^https?://',url,re.I): return jsonify({'error':'subtitle URL must start with http:// or https://'}),400
  entry['url']=url; entry['name']=url.rsplit('/',1)[-1]
 else: return jsonify({'error':'provide a subtitle URL or upload a file'}),400
 data=load_map(); data.setdefault(rel,[]).append(entry); save_map(data)
 return jsonify({'ok':True,'subtitle':entry})

@app.delete('/subtitle-api')
def subtitle_delete():
 rel=clean_rel(request.args.get('file')); sid=request.args.get('id') or ''
 if rel is None: return jsonify({'error':'invalid file'}),400
 data=load_map(); old=data.get(rel,[]); keep=[]; removed=None
 for e in old:
  if e.get('id')==sid and removed is None: removed=e
  else: keep.append(e)
 if removed and removed.get('file'):
  try: os.remove(os.path.join(SUB_FILES,removed['file']))
  except OSError: pass
 if keep: data[rel]=keep
 else: data.pop(rel,None)
 save_map(data); return jsonify({'ok':bool(removed)})

@app.get('/subtitle-files/<path:name>')
def subtitle_file(name): return send_from_directory(SUB_FILES,name,as_attachment=False)

@app.get('/player-subtitle')
def player_subtitle():
 rel=clean_rel(request.args.get('file')); sid=request.args.get('id') or ''
 if rel is None: return jsonify({'error':'invalid file'}),400
 entry=next((e for e in load_map().get(rel,[]) if e.get('id')==sid),None)
 if not entry: return jsonify({'error':'subtitle not found'}),404
 try:
  if entry.get('file'):
   path=os.path.join(SUB_FILES,entry['file'])
   ext=os.path.splitext(entry.get('name') or entry['file'])[1].lower()
   with open(path,'rb') as f: raw=f.read()
  else:
   url=entry.get('url') or ''
   ext=os.path.splitext(urllib.parse.urlparse(url).path)[1].lower()
   r=requests.get(url,timeout=12,headers={'User-Agent':'Mozilla/5.0'}); r.raise_for_status(); raw=r.content
  if ext in ('.ass','.ssa'): return jsonify({'error':'ASS/SSA is not supported by the browser player'}),415
  try: text=raw.decode('utf-8-sig')
  except UnicodeDecodeError: text=raw.decode('latin-1','replace')
  return Response(subtitle_to_vtt(text),mimetype='text/vtt; charset=utf-8')
 except Exception as e:
  return jsonify({'error':f'could not load subtitle: {e}'}),502

@app.get('/health')
def health(): return jsonify({'ok':True,'files':len(video_files()),'subtitleMappings':len(load_map())})

app.run(host='0.0.0.0',port=7000)
