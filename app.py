"""OFERTA IA V11.11.
Carrega V11.9 e garante que o seletor de marketplace apareça dentro da janela de Oportunidades.
"""
import urllib.request

_BASE = "https://raw.githubusercontent.com/Aracni/oferta-ia/639b53c7e97152b2756e70eef2940454ae3420d7/app.py"
try:
    with urllib.request.urlopen(_BASE, timeout=20) as response:
        source = response.read().decode("utf-8")
except Exception as exc:
    raise RuntimeError(f"Não foi possível carregar o núcleo V11.9 do OFERTA IA: {exc}") from exc

exec(compile(source, _BASE, "exec"), globals(), globals())

try:
    _V111_UI = r'''<style>
#v119-market-filter{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0 14px;padding:10px;border-radius:12px;background:rgba(127,127,127,.10);align-items:center;width:100%;box-sizing:border-box}
#v119-market-filter .v119-title{font-weight:700;margin-right:4px}
#v119-market-filter label{display:inline-flex;align-items:center;gap:6px;padding:7px 10px;border:1px solid rgba(127,127,127,.28);border-radius:9px;cursor:pointer;user-select:none}
#v119-market-filter input{accent-color:currentColor}
#v119-market-filter label.v119-active{font-weight:700;box-shadow:0 0 0 1px currentColor inset}
</style>
<div id="v119-market-filter" aria-label="Marketplace">
  <span class="v119-title">Marketplace:</span>
  <label><input type="radio" name="v119_market" value="both" checked> Ambos</label>
  <label><input type="radio" name="v119_market" value="mercadolivre"> Mercado Livre</label>
  <label><input type="radio" name="v119_market" value="shopee"> Shopee</label>
</div>
<script>
(function(){
  function setup(){
    if(document.getElementById('v119-market-filter')) return true;
    const box=document.createElement('div');
    box.id='v119-market-filter'; box.setAttribute('aria-label','Marketplace');
    box.innerHTML='<span class="v119-title">Marketplace:</span>'+
      '<label><input type="radio" name="v119_market" value="both" checked> Ambos</label>'+
      '<label><input type="radio" name="v119_market" value="mercadolivre"> Mercado Livre</label>'+
      '<label><input type="radio" name="v119_market" value="shopee"> Shopee</label>';
    const inputs=[...box.querySelectorAll('input[name=v119_market]')];
    function selected(){const x=inputs.find(i=>i.checked);return x?x.value:'both'}
    function paint(){inputs.forEach(i=>i.closest('label').classList.toggle('v119-active',i.checked))}
    inputs.forEach(i=>i.addEventListener('change',function(){paint();localStorage.setItem('oferta_ia_marketplace',selected())}));
    const saved=localStorage.getItem('oferta_ia_marketplace');
    if(saved&&inputs.some(i=>i.value===saved)) inputs.forEach(i=>i.checked=i.value===saved);
    paint();
    const all=[...document.querySelectorAll('input,button,div,label')];
    const anchor=all.find(el=>((el.textContent||'').trim().startsWith('Opcional: beleza')));
    const qty=all.find(el=>el.tagName==='INPUT'&&((el.type||'').toLowerCase()==='number'));
    const target=anchor||qty||all.find(el=>((el.textContent||'').includes('Encontrar oportunidades')));
    if(target&&target.parentNode){
      if(qty&&qty.parentNode&&target===qty) qty.parentNode.insertBefore(box,qty);
      else target.parentNode.insertBefore(box,target.nextSibling);
    } else {
      const modal=[...document.querySelectorAll('div')].find(el=>((el.textContent||'').includes('Encontrar oportunidades')&&el.offsetParent));
      if(modal) modal.insertBefore(box,modal.firstChild);
      else document.body.appendChild(box);
    }
    return true;
  }
  function selectedValue(){const x=document.querySelector('input[name=v119_market]:checked');return x?x.value:'both'}
  const originalFetch=window.fetch;
  window.fetch=function(input,init){
    try{
      const url=typeof input==='string'?input:(input&&input.url)||'';
      if(url.includes('/api/opportunities-central')&&init&&typeof init.body==='string'){
        const body=JSON.parse(init.body); body.marketplaces=selectedValue(); init=Object.assign({},init,{body:JSON.stringify(body)});
      }
    }catch(e){}
    return originalFetch.call(this,input,init);
  };
  setup();
  const observer=new MutationObserver(function(){setup()});
  observer.observe(document.documentElement,{childList:true,subtree:true});
})();
</script>'''
    # First try to place it in the existing HTML, but do not depend on the
    # internal structure of the V11.8 modal. The script itself also watches
    # dynamically-created modal content and inserts the selector there.
    if '</body>' in HTML:
        HTML = HTML.replace('</body>', _V111_UI + '</body>')
    else:
        HTML += _V111_UI
except Exception:
    pass

print("[V11.11] seletor marketplace inserido dentro da janela de Oportunidades; seleção única; padrão=Ambos", flush=True)
