// Safari subtitle language compatibility for PiTorrent web player.
const PLAYER_SUB_LANGS={
  eng:{code:'en',label:'English'},
  vie:{code:'vi',label:'Vietnamese'},
  dual:{code:'mul',label:'Dual Language'}
};

function limitSubtitleLanguageOptions(){
  const sel=document.getElementById('sub-lang');
  if(!sel) return;
  const current=sel.value;
  sel.innerHTML='';
  [
    ['eng','English'],
    ['vie','Vietnamese'],
    ['dual','Dual Language']
  ].forEach(([value,label])=>{
    const opt=document.createElement('option');
    opt.value=value;
    opt.textContent=label;
    sel.appendChild(opt);
  });
  if(['eng','vie','dual'].includes(current)) sel.value=current;
}

if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',limitSubtitleLanguageOptions);
else limitSubtitleLanguageOptions();

openPlayer=async function(path){
  const box=$('player-box'),v=$('player');
  v.pause();
  v.removeAttribute('src');
  v.innerHTML='';
  $('player-title').textContent=path.split('/').pop();
  $('player-note').textContent='Loading subtitles…';
  box.classList.add('open');
  v.src=mediaUrl(path);
  try{
    const r=await fetch('/subtitle-api?file='+enc(path));
    const d=await r.json();
    const a=d.subtitles||[];
    a.forEach((s,i)=>{
      const meta=PLAYER_SUB_LANGS[String(s.lang||'').toLowerCase()]||{code:'und',label:String(s.lang||'Subtitle').toUpperCase()};
      const tr=document.createElement('track');
      tr.kind='subtitles';
      tr.label=meta.label;
      tr.srclang=meta.code;
      tr.src='/player-subtitle?file='+enc(path)+'&id='+enc(s.id);
      if(i===0)tr.default=true;
      v.appendChild(tr);
    });
    $('player-note').textContent=a.length?`${a.length} subtitle track(s) loaded. Choose a subtitle from CC/Subtitles.`:'No subtitle attached to this file.';
  }catch(e){
    $('player-note').textContent='Could not load subtitle list.';
  }
  v.load();
  box.scrollIntoView({behavior:'smooth',block:'start'});
  v.play().catch(()=>{});
};
