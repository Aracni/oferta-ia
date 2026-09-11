"""OFERTA IA V11.12.
Corrige a posição do seletor de marketplace dentro da janela de oportunidades.
"""
import re
import urllib.request

_BASE = "https://raw.githubusercontent.com/Aracni/oferta-ia/9ec0735ab105d9a0d76432d1c82a7996cf1b7c26/app.py"
with urllib.request.urlopen(_BASE, timeout=30) as response:
    source = response.read().decode("utf-8")
source = source.replace("api.mercadolivre.com", "api.mercadolibre.com")
exec(compile(source, _BASE, "exec"), globals(), globals())

_V112_UI = r'''<style>
#v112-market-filter{margin:12px 0;padding:10px 12px;border:1px solid rgba(127,127,127,.25);border-radius:10px;font-size:14px;display:flex;gap:12px;align-items:center;flex-wrap:wrap;background:rgba(127,127,127,.06)}
#v112-market-filter .v112-title{font-weight:700;margin-right:2px}
#v112-market-filter label{display:inline-flex;align-items:center;gap:5px;cursor:pointer;white-space:nowrap}
#v112-market-filter input{accent-color:currentColor}
</style>
<script>
(function(){
  const ID='v112-market-filter';
  const OLD='v119-market-filter';
  function selected(){const x=document.querySelector('input[name="v112_market"]:checked');return x?x.value:'both'}
  function makeBox(){
    let box=document.getElementById(ID);
    if(box) return box;
    box=document.createElement('div'); box.id=ID; box.setAttribute('aria-label','Marketplace');
    box.innerHTML='<span class="v112-title">Marketplace:</span>'+['both|Ambos','mercadolivre|Mercado Livre','shopee|Shopee'].map(function(v){const p=v.split('|');return '<label><input type="radio" name="v112_market" value="'+p[0]+'"> '+p[1]+'</label>'}).join('');
    box.querySelectorAll('input').forEach(function(i){i.addEventListener('change',function(){localStorage.setItem('oferta_ia_marketplace',selected())})});
    const saved=localStorage.getItem('oferta_ia_marketplace')||'both';
    const radio=box.querySelector('input[value="'+saved+'"]')||box.querySelector('input[value="both"]');
    radio.checked=true;
    return box;
  }
  function visible(el){return !!el && (el.offsetWidth||el.offsetHeight||el.getClientRects().length)}
  function findModal(){
    const dialogs=[...document.querySelectorAll('[role="dialog"],dialog')].filter(visible);
    for(const d of dialogs){const t=d.innerText||'';if(t.includes('Oportunidades')&&t.includes('Encontrar oportunidades'))return d}
    const nodes=[...document.querySelectorAll('div')].filter(visible).filter(function(el){const t=el.innerText||'';return t.includes('Oportunidades')&&t.includes('Encontrar oportunidades')});
    nodes.sort((a,b)=>a.innerText.length-b.innerText.length);
    return nodes[0]||null;
  }
  function place(){
    const modal=findModal(); if(!modal)return false;
    const box=makeBox();
    const qty=[...modal.querySelectorAll('input')].find(function(i){return (i.type||'').toLowerCase()==='number'&&visible(i)});
    const niche=[...modal.querySelectorAll('*')].find(function(el){return visible(el)&&((el.textContent||'').trim().startsWith('Opcional: beleza, eletrônicos, fitness'))});
    const button=[...modal.querySelectorAll('button')].find(function(b){return visible(b)&&(b.textContent||'').includes('Encontrar oportunidades')});
    if(qty&&qty.parentNode){
      const parent=qty.parentNode;
      if(box.parentNode!==parent || box.nextSibling!==qty) parent.insertBefore(box,qty);
      return true;
    }
    if(niche&&niche.parentNode){niche.parentNode.insertBefore(box,niche.nextSibling);return true}
    if(button&&button.parentNode){button.parentNode.insertBefore(box,button);return true}
    if(box.parentNode!==modal)modal.appendChild(box);
    return true;
  }
  function cleanOld(){const old=document.getElementById(OLD);if(old)old.remove()}
  cleanOld(); place();
  let timer=0;
  const observer=new MutationObserver(function(){cleanOld();clearTimeout(timer);timer=setTimeout(place,30)});
  if(document.body)observer.observe(document.body,{childList:true,subtree:true});
  const originalFetch=window.fetch;
  window.fetch=function(input,init){
    try{
      const url=typeof input==='string'?input:(input&&input.url)||'';
      if(url.includes('/api/opportunities-central')&&init&&typeof init.body==='string'){
        const body=JSON.parse(init.body); body.marketplaces=selected(); init=Object.assign({},init,{body:JSON.stringify(body)});
      }
    }catch(e){}
    return originalFetch.call(this,input,init);
  };
  window.setInterval(place,1000);
})();
</script>'''

if "id=\"v112-market-filter\"" not in HTML and "</body>" in HTML:
    HTML = HTML.replace("</body>", _V112_UI + "</body>")
else:
    HTML = HTML.replace("</body>", _V112_UI + "</body>")

print("[V11.12] seletor de marketplace reposicionado dentro da janela de oportunidades; seleção única e filtro preservado")
