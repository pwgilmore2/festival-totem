import phone_server

_CSS = r'''
<style>
.safeRangeRow{display:grid;grid-template-columns:46px minmax(0,1fr) 46px;gap:8px;align-items:center}
.safeRangeRow input[type=range]{width:100%;touch-action:pan-y}
.safeRangeStep{min-height:42px;padding:0;font-size:23px;font-weight:850;line-height:1;border-radius:11px;background:#2f3040;box-shadow:inset 0 0 0 1px #ffffff18}
.safeRangeStep:active{transform:scale(.96);filter:brightness(1.25)}
</style>
'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</head>', _CSS + '</head>', 1)

_JS = r'''
<script>
(function(){
  const oldDefaults=['DRINK WATER','MEET ME HERE','FOLLOW THE TOTEM',"WHERE'S THE AFTERS?",'YOU GOOD?','HAPPY BIRTHDAY'];
  const newDefaults=['DRINK WATER','YOU GOOD?','WAKAAN','K HOLE','SPAGHETTI TIME','BASS FACE'];
  try{
    const key='festivalTotem.quickText',raw=localStorage.getItem(key);
    if(!raw){localStorage.setItem(key,JSON.stringify(newDefaults));quickPresets=[...newDefaults];renderQuickPresets()}
    else{
      const saved=JSON.parse(raw);
      if(Array.isArray(saved)&&JSON.stringify(saved)===JSON.stringify(oldDefaults)){
        localStorage.setItem(key,JSON.stringify(newDefaults));quickPresets=[...newDefaults];renderQuickPresets()
      }
    }
  }catch(_){ }

  function n(v,fallback){v=parseFloat(v);return Number.isFinite(v)?v:fallback}
  function stepRange(input,dir){
    const step=n(input.step,1)||1,min=n(input.min,-Infinity),max=n(input.max,Infinity);
    let value=n(input.value,0)+dir*step;
    if(Number.isFinite(min))value=Math.max(min,value);
    if(Number.isFinite(max))value=Math.min(max,value);
    const decimals=(String(step).split('.')[1]||'').length;
    input.value=decimals?value.toFixed(decimals):String(Math.round(value));
    input.dispatchEvent(new Event('input',{bubbles:true}));
    input.dispatchEvent(new Event('change',{bubbles:true}));
  }
  function installSafeRanges(){
    document.querySelectorAll('input[type="range"]').forEach(input=>{
      if(input.dataset.safeWrapped==='1')return;
      input.dataset.safeWrapped='1';
      const row=document.createElement('div');row.className='safeRangeRow';
      const minus=document.createElement('button');minus.type='button';minus.className='safeRangeStep';minus.textContent='−';minus.setAttribute('aria-label','Decrease');
      const plus=document.createElement('button');plus.type='button';plus.className='safeRangeStep';plus.textContent='+';plus.setAttribute('aria-label','Increase');
      input.parentNode.insertBefore(row,input);row.append(minus,input,plus);
      minus.addEventListener('click',()=>stepRange(input,-1));plus.addEventListener('click',()=>stepRange(input,1));
    })
  }
  installSafeRanges();
  setTimeout(installSafeRanges,250);
  setTimeout(installSafeRanges,1000);
})();
</script>
'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</body>', _JS + '</body>', 1)
