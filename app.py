"""OFERTA IA V11.10.
Carrega V11.9 e corrige o seletor de marketplace para seleção única.
"""
import urllib.request

_BASE = "https://raw.githubusercontent.com/Aracni/oferta-ia/639b53c7e97152b2756e70eef2940454ae3420d7/app.py"
try:
    with urllib.request.urlopen(_BASE, timeout=20) as response:
        source = response.read().decode("utf-8")
except Exception as exc:
    raise RuntimeError(f"Não foi possível carregar o núcleo V11.9 do OFERTA IA: {exc}") from exc

# Mantém toda a lógica estável da V11.9 e substitui apenas a UI do filtro.
exec(compile(source, _BASE, "exec"), globals(), globals())

try:
    _V110_UI = r'''<style>
#v119-market-filter{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0 14px;padding:10px;border-radius:12px;background:rgba(127,127,127,.10);align-items:center}
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
  const box=document.getElementById('v119-market-filter'); if(!box) return;
  const inputs=[...box.querySelectorAll('input[name=v119_market]')];
  function selected(){const x=inputs.find(i=>i.checked);return x?x.value:'both'}
  function paint(){inputs.forEach(i=>i.closest('label').classList.toggle('v119-active',i.checked))}
  inputs.forEach(i=>i.addEventListener('change',function(){paint();localStorage.setItem('oferta_ia_marketplace',selected())}));
  const saved=localStorage.getItem('oferta_ia_marketplace');
  if(saved&&inputs.some(i=>i.value===saved)){inputs.forEach(i=>i.checked=i.value===saved)}
  paint();
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
})();
</script>'''
    # Remove the V11.9 selector and inject the V11.10 radio selector.
    start = HTML.find('<div id="v119-market-filter"')
    if start >= 0:
        script_start = HTML.find('<script>', start)
        if script_start >= 0:
            end = HTML.find('</script>', script_start)
            if end >= 0:
                end += len('</script>')
                # Include the preceding style block if it belongs to this selector.
                style_start = HTML.rfind('<style>', 0, start)
                if style_start >= 0:
                    style_end = HTML.find('</style>', style_start)
                    if style_end >= 0 and style_end < start:
                        style_end += len('</style>')
                        start = style_start
                HTML = HTML[:start] + _V110_UI + HTML[end:]
    elif '</body>' in HTML:
        HTML = HTML.replace('</body>', _V110_UI + '</body>')
except Exception:
    pass

print("[V11.10] filtro de marketplace em seleção única; padrão=Ambos", flush=True)
