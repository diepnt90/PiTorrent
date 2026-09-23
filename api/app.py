import os,re,urllib.parse,json,uuid,ipaddress,socket
from flask import Flask,jsonify,request,send_from_directory,Response
from werkzeug.utils import secure_filename
import requests

app=Flask(__name__)
ROOT='/downloads/complete'
SUB_ROOT='/data/subtitles'
SUB_FILES=os.path.join(SUB_ROOT,'files')
SUB_MAP=os.path.join(SUB_ROOT,'mappings.json')
SUB_EXT={'.srt','.vtt','.ass','.ssa'}
os.makedirs(SUB_FILES,exist_ok=True)

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

def video_count():
 exts={'.mp4','.mkv','.avi','.mov','.m4v','.webm','.ts','.m2ts','.wmv','.flv'}
 n=0
 if os.path.isdir(ROOT):
  for _,_,files in os.walk(ROOT):
   n+=sum(1 for fn in files if os.path.splitext(fn)[1].lower() in exts)
 return n

def redirect_target_url(value):
 value=(value or '').strip()
 if not value: return None
 if not re.match(r'^https?://',value,re.I): value='https://'+value
 try: u=urllib.parse.urlsplit(value)
 except ValueError: return None
 if u.scheme not in ('http','https') or not u.hostname or u.username or u.password: return None
 return value

def public_http_url(url):
 try:
  u=urllib.parse.urlsplit(url); host=u.hostname
  if u.scheme not in ('http','https') or not host or u.username or u.password: return False
  try:
   ips={x[4][0] for x in socket.getaddrinfo(host,u.port or (443 if u.scheme=='https' else 80),type=socket.SOCK_STREAM)}
  except socket.gaierror: return False
  return all(ipaddress.ip_address(raw.split('%',1)[0]).is_global for raw in ips)
 except (ValueError,OSError): return False

def follow_redirects(url,max_redirects=10):
 history=[]; current=url
 headers={'User-Agent':'Mozilla/5.0 (PiTorrent Redirect Checker)'}
 for _ in range(max_redirects+1):
  if not public_http_url(current): raise ValueError('URL resolves to a non-public address')
  r=requests.get(current,timeout=(5,10),headers=headers,allow_redirects=False,stream=True)
  try:
   status=r.status_code
   if status in (301,302,303,307,308) and r.headers.get('Location'):
    if len(history)>=max_redirects: raise ValueError('too many redirects')
    nxt=urllib.parse.urljoin(current,r.headers['Location'])
    history.append({'status':status,'url':current,'location':nxt}); current=nxt; continue
   return current,status,history
  finally: r.close()
 raise ValueError('too many redirects')

def subtitle_to_vtt(text):
 text=(text or '').replace('\r\n','\n').replace('\r','\n').lstrip('\ufeff')
 if text.lstrip().startswith('WEBVTT'): return text
 out=['WEBVTT','']
 for line in text.split('\n'):
  if '-->' in line: line=re.sub(r'(\d{2}:\d{2}:\d{2}),(\d{3})',r'\1.\2',line)
  out.append(line)
 return '\n'.join(out)

@app.after_request
def cors(resp):
 resp.headers['Access-Control-Allow-Origin']='*'
 resp.headers['Access-Control-Allow-Headers']='*'
 resp.headers['Access-Control-Allow-Methods']='GET,HEAD,OPTIONS,POST,DELETE'
 resp.headers['Cache-Control']='no-store'
 return resp

@app.get('/subtitle-api')
def subtitle_get():
 rel=clean_rel(request.args.get('file'))
 if rel is None: return jsonify({'error':'invalid file'}),400
 return jsonify({'file':rel,'subtitles':load_map().get(rel,[])})

@app.post('/subtitle-api')
def subtitle_add():
 rel=clean_rel(request.form.get('file'))
 if rel is None or not os.path.isfile(os.path.join(ROOT,rel)): return jsonify({'error':'video file not found'}),400
 lang=(request.form.get('lang') or 'eng').strip() or 'eng'
 url=(request.form.get('url') or '').strip(); upload=request.files.get('upload')
 entry={'id':uuid.uuid4().hex[:12],'lang':lang}
 if upload and upload.filename:
  ext=os.path.splitext(upload.filename)[1].lower()
  if ext not in SUB_EXT: return jsonify({'error':'subtitle must be .srt, .vtt, .ass or .ssa'}),400
  stored=entry['id']+'-'+secure_filename(upload.filename)
  upload.save(os.path.join(SUB_FILES,stored)); entry['file']=stored; entry['name']=upload.filename
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
 save_map(data)
 return jsonify({'ok':bool(removed)})

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
 except Exception as e: return jsonify({'error':f'could not load subtitle: {e}'}),502

@app.post('/check-redirect')
def check_redirect():
 data=request.get_json(silent=True) or {}
 value=(data.get('domain') or data.get('url') or request.form.get('domain') or request.form.get('url') or '').strip()
 target=redirect_target_url(value)
 if not target: return jsonify({'error':'provide a valid http/https domain or URL'}),400
 try:
  final_url,status,history=follow_redirects(target)
  return jsonify({'input':value,'final_url':final_url,'final_domain':urllib.parse.urlsplit(final_url).hostname or '','status':status,'redirects':len(history),'history':history})
 except requests.RequestException as e: return jsonify({'error':f'request failed: {e}'}),502
 except ValueError as e: return jsonify({'error':str(e)}),400

@app.get('/health')
def health(): return jsonify({'ok':True,'files':video_count(),'subtitleMappings':len(load_map())})

app.run(host='0.0.0.0',port=7000)
