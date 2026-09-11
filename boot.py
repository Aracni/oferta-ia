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

# V11.10.8/V11.10.9 — seletor Marketplace.
# Mantemos a restauração no HTML e, adicionalmente, garantimos a presença
# na resposta HTTP REAL da rota /, sem reconstruir a rota FastAPI.
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

# Primeiro garante a variável HTML final, como nas versões anteriores.
try:
    if 'id="oferta-market-filter"' not in oferta_app.HTML:
        pattern = r'(<input\s+id="opportunityNiche"\b[^>]*>)'
        match = re.search(pattern, oferta_app.HTML)
        if match:
            oferta_app.HTML = oferta_app.HTML[:match.start()] + _MARKET_UI + '\n    ' + oferta_app.HTML[match.start():]
            print('[V11.10.9] seletor restaurado no HTML final', flush=True)
        elif '</body>' in oferta_app.HTML:
            oferta_app.HTML = oferta_app.HTML.replace('</body>', _MARKET_UI + '</body>', 1)
            print('[V11.10.9] seletor restaurado antes de </body>', flush=True)
        else:
            print('[V11.10.9] ERRO: âncora HTML não encontrada', flush=True)
    else:
        print('[V11.10.9] seletor já presente no HTML final', flush=True)
except Exception as exc:
    print(f'[V11.10.9] falha controlada no HTML: {exc}', flush=True)

# Segundo: intercepta somente a resposta ASGI real da rota /.
# Isso evita depender de como o endpoint / foi fechado pelo núcleo original.
try:
    async def _market_home_response(scope, receive, send, _original):
        if scope.get('type') != 'http' or scope.get('path') != '/':
            return await _original(scope, receive, send)

        messages = []
        body_parts = []

        async def _capture(message):
            if message.get('type') == 'http.response.start':
                messages.append(message)
                return
            if message.get('type') == 'http.response.body':
                body_parts.append(message.get('body', b''))
                if message.get('more_body', False):
                    return
                body = b''.join(body_parts)
                marker = b'id="oferta-market-filter"'
                if marker not in body and b'</body>' in body:
                    ui = _MARKET_UI.encode('utf-8')
                    body = body.replace(b'</body>', ui + b'</body>', 1)
                    new_headers = []
                    for key, value in messages[0].get('headers', []):
                        if key.lower() == b'content-length':
                            continue
                        new_headers.append((key, value))
                    messages[0]['headers'] = new_headers
                    print('[V11.10.9] seletor inserido na resposta HTTP real da rota /', flush=True)
                elif marker in body:
                    print('[V11.10.9] seletor confirmado na resposta HTTP real da rota /', flush=True)
                else:
                    print('[V11.10.9] resposta / sem </body>; seletor não inserido', flush=True)
                for i, saved in enumerate(messages):
                    await send(saved)
                await send({'type':'http.response.body','body':body,'more_body':False})
                return
            await send(message)

        return await _original(scope, receive, _capture)

    for _route in getattr(oferta_app.app, 'routes', []):
        if getattr(_route, 'path', None) == '/' and hasattr(_route, 'app'):
            if not getattr(_route.app, '_oferta_market_response_v11109', False):
                _original_home_app = _route.app
                async def _wrapped_home(scope, receive, send, _original=_original_home_app):
                    return await _market_home_response(scope, receive, send, _original)
                _wrapped_home._oferta_market_response_v11109 = True
                _route.app = _wrapped_home
                print('[V11.10.9] proteção da resposta HTTP da rota / instalada', flush=True)
            break
except Exception as exc:
    print(f'[V11.10.9] falha controlada no wrapper ASGI da rota /: {exc}', flush=True)

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        oferta_app.app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "10000")),
    )
