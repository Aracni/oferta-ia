"""Inicialização explícita do OFERTA IA."""
import os
import re
import app as oferta_app
import v106_patch

v106_patch.install(oferta_app.app)

oferta_app.app._get_connection = oferta_app._get_connection
oferta_app.app._save_connection = oferta_app._save_connection

import meli_auto
meli_auto.install(oferta_app.app)

import meli_fast
meli_fast.install(oferta_app.app)

# V11.10.5 — última camada, depois de TODOS os patches.
# O seletor é inserido na resposta HTTP do / para garantir que nenhuma
# alteração posterior de app.HTML consiga removê-lo antes do navegador receber a página.
_MARKET_UI_FINAL = r'''<style>
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


def _finalize_home_response(original):
    def endpoint(*args, **kwargs):
        response = original(*args, **kwargs)
        try:
            from fastapi.responses import HTMLResponse
            if isinstance(response, HTMLResponse):
                body = response.body.decode("utf-8", errors="replace")
                if 'id="oferta-market-filter"' not in body:
                    anchor = re.search(r'<input\s+id="opportunityNiche"\b[^>]*>', body)
                    if anchor:
                        body = body[:anchor.start()] + _MARKET_UI_FINAL + '\n    ' + body[anchor.start():]
                        response = HTMLResponse(content=body, status_code=response.status_code, headers=dict(response.headers), media_type="text/html")
                        print("[V11.10.5] seletor Marketplace injetado na resposta final /", flush=True)
                    else:
                        print("[V11.10.5] ERRO: anchor opportunityNiche nao encontrado na resposta /", flush=True)
                else:
                    print("[V11.10.5] seletor Marketplace confirmado na resposta final /", flush=True)
        except Exception as exc:
            print(f"[V11.10.5] falha controlada no /: {exc}", flush=True)
        return response
    endpoint._v11105_final_home = True
    return endpoint

try:
    from fastapi.dependencies.utils import get_dependant
    from fastapi.routing import request_response
    for _route in getattr(oferta_app.app, "routes", []):
        if getattr(_route, "path", None) == "/" and not getattr(_route.endpoint, "_v11105_final_home", False):
            _original_home = _route.endpoint
            _final_home = _finalize_home_response(_original_home)
            _route.endpoint = _final_home
            _route.dependant = get_dependant(path=_route.path, call=_final_home)
            _route.app = request_response(_route.get_route_handler())
            print("[V11.10.5] endpoint / reconstruido com injecao final do seletor", flush=True)
            break
except Exception as exc:
    print(f"[V11.10.5] falha ao reconstruir endpoint /: {exc}", flush=True)

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        oferta_app.app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "10000")),
    )
