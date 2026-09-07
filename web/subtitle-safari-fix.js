// Safari subtitle language compatibility for PiTorrent web player.
// Stored subtitle language codes use ISO-639-2 (eng/vie/...), while HTML5
// track.srclang is best represented with BCP-47/ISO-639-1 codes.
const PLAYER_SUB_LANGS={
  eng:{code:'en',label:'English'},
  vie:{code:'vi',label:'Vietnamese'},
  dual:{code:'mul',label:'Dual Language'},
  jpn:{code:'ja',label:'Japanese'},
  kor:{code:'ko',label:'Korean'},
  chi:{code:'zh',label:'Chinese'},
  zho:{code:'zh',label:'Chinese'},
  und:{code:'und',label:'Other'}
};

function ensureDualLanguageOption(){
  const sel=document.getElementById('sub-lang');
  if(!sel||sel.querySelector('option[value="dual"]')) return;
  const opt=document.createElement('option');
  opt.value='dual';
  opt.textContent='Dual Language';
  const other=sel.querySelector('option[value="und"]');
  if(other) sel.insertBefore(opt,other); else sel.appendChild(opt);
}

if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',ensureDualLanguageOption);
else ensureDualLanguageOption();

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
      const meta=PLAYER_SUB_LANGS[String(s.lang||'und').toLowerCase()]||{code:String(s.lang||'und').toLowerCase(),label:String(s.lang||'Subtitle').toUpperCase()};
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
