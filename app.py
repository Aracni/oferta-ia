"""OFERTA IA V11.10.4.
Preserva o patch de enriquecimento ML e injeta o seletor Marketplace em uma âncora estrutural estável.
"""
import urllib.request
import re

_BASE = "https://raw.githubusercontent.com/Aracni/oferta-ia/639b53c7e97152b2756e70eef2940454ae3420d7/app.py"
_PATCH = "https://raw.githubusercontent.com/Aracni/oferta-ia/c18c26a11794b66e037b8c78cbdc207ab83c9559/ml_enrichment_v2.py"

try:
    with urllib.request.urlopen(_BASE, timeout=20) as response:
        source = response.read().decode("utf-8")
except Exception as exc:
    raise RuntimeError(f"Não foi possível carregar o núcleo V11.9 do OFERTA IA: {exc}") from exc

exec(compile(source, _BASE, "exec"), globals(), globals())

try:
    with urllib.request.urlopen(_PATCH, timeout=20) as response:
        patch = response.read().decode("utf-8")
except Exception as exc:
    raise RuntimeError(f"Não foi possível carregar o patch V11.10.2 do OFERTA IA: {exc}") from exc

exec(compile(patch, _PATCH, "exec"), globals(), globals())

# SELETOR MARKETPLACE — inserção estrutural no formulário de Oportunidades.
# Não depende de </body>, MutationObserver ou intervalos.
try:
    _MARKET_UI = r'''<style>
#oferta-market-filter{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0 14px;padding:10px;border:1px solid #e4e7ec;border-radius:12px;background:#f8fafc;align-items:center;width:100%;box-sizing:border-box}
#oferta-market-filter .market-title{font-weight:800;margin-right:3px}
#oferta-market-filter label{display:inline-flex;align-items:center;gap:6px;padding:7px 10px;border:1px solid #d0d5dd;border-radius:9px;cursor:pointer;user-select:none;background:#fff;font-size:13px}
#oferta-market-filter input{width:auto;padding:0;margin:0;accent-color:#2563eb}
#oferta-market-filter label.active{font-weight:800;box-shadow:0 0 0 1px #2563eb inset}
</style>
<div id="oferta-market-filter" aria-label="Marketplace">
<span class="market-title">Marketplace:</span>
<label><input type="radio" name="oferta_marketplace" value="both" checked> 🔘 Ambos — padrão</label>
<label><input type="radio" name="oferta_marketplace" value="mercadolivre"> ⚪ Mercado Livre</label>
<label><input type="radio" name="oferta_marketplace" value="shopee"> ⚪ Shopee</label>
</div>
<script>
(function(){
  var box=document.getElementById('oferta-market-filter');
  if(!box)return;
  var radios=box.querySelectorAll('input[name="oferta_marketplace"]');
  function selected(){
    for(var i=0;i<radios.length;i++) if(radios[i].checked) return radios[i].value;
    return 'both';
  }
  function paint(){
    for(var i=0;i<radios.length;i++){
      var label=radios[i].parentElement;
      if(label) label.classList.toggle('active',radios[i].checked);
    }
  }
  var saved=null;
  try{saved=localStorage.getItem('oferta_ia_marketplace')}catch(e){}
  if(saved){
    for(var i=0;i<radios.length;i++) radios[i].checked=(radios[i].value===saved);
  }
  for(var i=0;i<radios.length;i++) radios[i].addEventListener('change',function(){
    paint();
    try{localStorage.setItem('oferta_ia_marketplace',selected())}catch(e){}
  });
  paint();
  var originalFetch=window.fetch;
  window.fetch=function(input,init){
    try{
      var url=typeof input==='string'?input:(input&&input.url)||'';
      if(url.indexOf('/api/opportunities-central')!==-1 && init && typeof init.body==='string'){
        var body=JSON.parse(init.body);
        body.marketplaces=selected();
        init=Object.assign({},init,{body:JSON.stringify(body)});
      }
    }catch(e){}
    return originalFetch.call(this,input,init);
  };
})();
</script>'''

    if 'id="oferta-market-filter"' not in HTML:
        # Aceita qualquer indentação e qualquer atributo adicional no input.
        _pattern = r'(<input\s+id="opportunityNiche"\b[^>]*>)'
        _match = re.search(_pattern, HTML)
        if _match:
            HTML = HTML[:_match.start()] + _MARKET_UI + '\n    ' + HTML[_match.start():]
            print('[V11.10.4] seletor Marketplace inserido antes de opportunityNiche', flush=True)
        else:
            print('[V11.10.4] ERRO: input opportunityNiche não encontrado; seletor não inserido', flush=True)
    else:
        print('[V11.10.4] seletor Marketplace já presente; nenhuma duplicação', flush=True)
except Exception as exc:
    print(f'[V11.10.4] falha controlada ao inserir seletor: {exc}', flush=True)

print('[V11.10.4] seletor Marketplace + enriquecimento ML ativos', flush=True)
