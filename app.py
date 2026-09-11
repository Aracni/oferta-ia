"""OFERTA IA V11.10.10.
Preserva o patch de enriquecimento ML e garante o seletor Marketplace na resposta final.
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

# Garante o seletor na variável HTML antes de qualquer resposta.
try:
    if 'id="oferta-market-filter"' not in HTML:
        _pattern = r'(<input\s+id="opportunityNiche"\b[^>]*>)'
        _match = re.search(_pattern, HTML)
        if _match:
            HTML = HTML[:_match.start()] + _MARKET_UI + '\n    ' + HTML[_match.start():]
            print('[V11.10.10] seletor inserido no HTML final', flush=True)
        elif '</body>' in HTML:
            HTML = HTML.replace('</body>', _MARKET_UI + '</body>', 1)
            print('[V11.10.10] seletor inserido antes de </body>', flush=True)
        else:
            print('[V11.10.10] ERRO: âncora HTML não encontrada', flush=True)
    else:
        print('[V11.10.10] seletor já presente no HTML final', flush=True)
except Exception as exc:
    print(f'[V11.10.10] falha controlada no HTML: {exc}', flush=True)

# Fallback definitivo: middleware HTTP, independente de como a rota / foi criada.
# Ele reescreve somente HTML da resposta raiz e corrige Content-Length.
try:
    from starlette.responses import Response
    from starlette.middleware.base import BaseHTTPMiddleware

    class _MarketSelectorMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            response = await call_next(request)
            if request.url.path != '/' or 'text/html' not in response.headers.get('content-type', ''):
                return response
            try:
                body = b''
                async for chunk in response.body_iterator:
                    body += chunk
                marker = b'id="oferta-market-filter"'
                if marker not in body and b'</body>' in body:
                    body = body.replace(b'</body>', _MARKET_UI.encode('utf-8') + b'</body>', 1)
                    print('[V11.10.10] seletor inserido pelo middleware HTTP', flush=True)
                elif marker in body:
                    print('[V11.10.10] seletor confirmado pelo middleware HTTP', flush=True)
                headers = dict(response.headers)
                headers.pop('content-length', None)
                return Response(content=body, status_code=response.status_code, headers=headers, media_type='text/html')
            except Exception as exc:
                print(f'[V11.10.10] falha controlada no middleware: {exc}', flush=True)
                return response

    if not any(type(m).__name__ == '_MarketSelectorMiddleware' for m in getattr(app, 'user_middleware', [])):
        app.add_middleware(_MarketSelectorMiddleware)
        print('[V11.10.10] middleware final do seletor instalado', flush=True)
except Exception as exc:
    print(f'[V11.10.10] middleware não instalado: {exc}', flush=True)

print('[V11.10.10] seletor Marketplace + enriquecimento ML ativos', flush=True)
