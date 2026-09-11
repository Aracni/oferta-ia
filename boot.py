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

# V11.10.8 — restauração simples e segura do seletor.
# Não altera nenhuma rota FastAPI. Apenas garante que o HTML final usado pelo
# endpoint / contenha o mesmo seletor que já funcionou anteriormente.
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

try:
    if 'id="oferta-market-filter"' not in oferta_app.HTML:
        # A posição é dentro do formulário de Oportunidades, imediatamente
        # antes do campo de nicho, como na versão que já funcionou.
        pattern = r'(<input\s+id="opportunityNiche"\b[^>]*>)'
        match = re.search(pattern, oferta_app.HTML)
        if match:
            oferta_app.HTML = oferta_app.HTML[:match.start()] + _MARKET_UI + '\n    ' + oferta_app.HTML[match.start():]
            print('[V11.10.8] seletor Marketplace restaurado no HTML final', flush=True)
        elif '</body>' in oferta_app.HTML:
            oferta_app.HTML = oferta_app.HTML.replace('</body>', _MARKET_UI + '</body>', 1)
            print('[V11.10.8] seletor Marketplace restaurado antes de </body>', flush=True)
        else:
            print('[V11.10.8] ERRO: não foi possível localizar âncora do seletor', flush=True)
    else:
        print('[V11.10.8] seletor Marketplace já presente no HTML final', flush=True)
except Exception as exc:
    print(f'[V11.10.8] falha controlada ao restaurar seletor: {exc}', flush=True)

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        oferta_app.app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "10000")),
    )
