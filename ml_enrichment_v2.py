"""OFERTA IA V11.10.12 — patch de enriquecimento do Mercado Livre.

Mantém o enriquecimento V11.10.2 e fixa o seletor de marketplace
estruturalmente dentro do formulário de Oportunidades, imediatamente antes
do campo opportunityNiche. Remove versões antigas do seletor para evitar
conflitos de HTML/JavaScript. Não usa middleware, MutationObserver ou wrapper
ASGI para a interface.
"""
import math
import time
import urllib.request
import re

_V1120_PRODUCT_CACHE = {}
_V1120_PRODUCT_TTL = 300
_V1120_REVIEWS_BLOCKED = False


def _v1120_num(value):
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


def _v1120_cache_get(cache, key, ttl):
    entry = cache.get(key)
    if not entry:
        return None
    if time.time() - entry[0] > ttl:
        cache.pop(key, None)
        return None
    return entry[1]


def _v1120_product(pid, token):
    pid = str(pid or "").upper()
    if not pid or not token:
        return None
    cached = _v1120_cache_get(_V1120_PRODUCT_CACHE, pid, _V1120_PRODUCT_TTL)
    if cached is not None:
        return cached
    product = None
    try:
        data, status = _v11_fetch_json(token, f"https://api.mercadolibre.com/products/{pid}", timeout=8, stage="CATALOG")
        if isinstance(data, dict) and status and 200 <= int(status) < 300:
            product = data
            try:
                _v11_remember_product(data)
            except Exception:
                pass
    except Exception:
        product = None
    _V1120_PRODUCT_CACHE[pid] = (time.time(), product or {})
    return product or None


def _v1120_sold(product, winner, row, item):
    for obj in (winner, product, row, item):
        if not isinstance(obj, dict):
            continue
        for key in ("sold_quantity", "sold", "sales", "sales_count"):
            value = _v1120_num(obj.get(key))
            if value is not None and value >= 0:
                return int(value)
    return None


def _v1120_rating(row, item):
    for obj in (row, item):
        if not isinstance(obj, dict):
            continue
        for key in ("rating", "product_rating", "review_rating"):
            value = _v1120_num(obj.get(key))
            if value is not None and 0 < value <= 5:
                return value
    return None


def _v1120_enrich_ml(items):
    global _V1120_REVIEWS_BLOCKED
    enriched = []
    try:
        token = _v9_valid_meli_token()
    except Exception:
        token = None

    for original in list(items or []):
        item = dict(original or {})
        row = _v119_row(item)
        pid = str(item.get("catalog_product_id") or item.get("product_id") or row.get("product_id") or "").upper()
        product = _v1120_product(pid, token) if token and pid else None
        winner = product.get("buy_box_winner") if isinstance(product, dict) else None
        winner = winner if isinstance(winner, dict) else {}

        sold = _v1120_sold(product, winner, row, item)
        rating = _v1120_rating(row, item)
        current = _v1120_num(item.get("current_price"))
        if current is None:
            current = _v1120_num(winner.get("price"))
        if current is None and isinstance(product, dict):
            rng = product.get("buy_box_winner_price_range")
            if isinstance(rng, dict) and isinstance(rng.get("min"), dict):
                current = _v1120_num(rng["min"].get("price"))
        if current is not None:
            item["current_price"] = current

        old = _v1120_num(item.get("old_price"))
        if old is None:
            old = _v1120_num(winner.get("original_price"))
        if old is not None:
            item["old_price"] = old

        discount = _v1120_num(item.get("discount_rate"))
        if discount is None and old and current and old > current:
            discount = round((old - current) / old * 100.0, 2)
            item["discount_rate"] = discount

        if sold is not None:
            item["sold_quantity"] = int(sold)
            item["sales"] = int(sold)
            item["sales_count"] = int(sold)
            item["demand_index"] = round(min(100.0, math.log1p(max(0, sold)) / math.log1p(10000) * 100.0), 2)
        else:
            item["demand_index"] = None

        if rating is not None:
            item["rating"] = rating
            item["rating_score"] = round(rating / 5.0 * 100.0, 2)

        available = sum(x is not None for x in (sold, rating, discount, current))
        item["data_confidence"] = "alta" if available >= 4 else "média" if available >= 2 else "baixa"
        item["confidence"] = item["data_confidence"]
        item["score_provisional"] = sold is None or rating is None
        item.setdefault("commission_rate", None)
        item.setdefault("commission_value", None)
        item.setdefault("earnings", None)
        item["commission_source"] = "não disponível no catálogo público"

        old_score = _v1120_num(item.get("opportunity_score"))
        signals = []
        if sold is not None:
            signals.append((item["demand_index"], 0.35))
        if rating is not None:
            signals.append((rating / 5.0 * 100.0, 0.15))
        if discount is not None:
            signals.append((min(100.0, max(0.0, discount / 60.0 * 100.0)), 0.25))
        if current is not None:
            signals.append((100.0 if current <= 50 else 90.0 if current <= 100 else 75.0 if current <= 200 else 60.0, 0.15))
        if signals:
            total = sum(w for _, w in signals)
            fresh = sum(v * w for v, w in signals) / total
            item["opportunity_score"] = round((old_score * 0.35 + fresh * 0.65) if old_score is not None else fresh, 2)
        enriched.append(item)
    return enriched


_v119_enrich_ml = _v1120_enrich_ml

# UI única e estrutural. Primeiro removemos versões antigas para que somente
# uma implementação possa existir no HTML final.
_V1120_UI = r'''<div id="oferta-market-filter" aria-label="Marketplace" style="grid-column:1 / -1;display:flex;flex-direction:column;gap:9px;margin:2px 0 4px;padding:12px;border:1px solid #d0d5dd;border-radius:12px;background:#f8fafc;width:100%;box-sizing:border-box">
  <div style="font-weight:800;font-size:14px;color:#172033">Marketplace</div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;width:100%">
    <label style="display:inline-flex;align-items:center;gap:6px;padding:8px 10px;border:1px solid #2563eb;border-radius:9px;background:#fff;cursor:pointer;font-size:13px;font-weight:800;box-sizing:border-box">
      <input type="radio" name="oferta_marketplace" value="both" checked style="width:auto;margin:0;padding:0;accent-color:#2563eb"> Ambos — padrão
    </label>
    <label style="display:inline-flex;align-items:center;gap:6px;padding:8px 10px;border:1px solid #d0d5dd;border-radius:9px;background:#fff;cursor:pointer;font-size:13px;font-weight:400;box-sizing:border-box">
      <input type="radio" name="oferta_marketplace" value="mercadolivre" style="width:auto;margin:0;padding:0;accent-color:#2563eb"> Mercado Livre
    </label>
    <label style="display:inline-flex;align-items:center;gap:6px;padding:8px 10px;border:1px solid #d0d5dd;border-radius:9px;background:#fff;cursor:pointer;font-size:13px;font-weight:400;box-sizing:border-box">
      <input type="radio" name="oferta_marketplace" value="shopee" style="width:auto;margin:0;padding:0;accent-color:#2563eb"> Shopee
    </label>
  </div>
</div>
<script>
(function(){
  if(window.__ofertaMarketplaceFilterInstalled)return;
  window.__ofertaMarketplaceFilterInstalled=true;
  var box=document.getElementById('oferta-market-filter');
  if(!box)return;
  var radios=box.querySelectorAll('input[name="oferta_marketplace"]');
  function selected(){for(var i=0;i<radios.length;i++)if(radios[i].checked)return radios[i].value;return 'both';}
  function paint(){for(var i=0;i<radios.length;i++){var label=radios[i].parentElement;if(label){label.style.fontWeight=radios[i].checked?'800':'400';label.style.borderColor=radios[i].checked?'#2563eb':'#d0d5dd';}}}
  var saved=null;
  try{saved=localStorage.getItem('oferta_ia_marketplace')}catch(e){}
  if(saved){for(var i=0;i<radios.length;i++)radios[i].checked=(radios[i].value===saved);}
  for(var i=0;i<radios.length;i++)radios[i].addEventListener('change',function(){paint();try{localStorage.setItem('oferta_ia_marketplace',selected())}catch(e){}});
  paint();
  if(window.__ofertaMarketplaceFetchWrapped)return;
  window.__ofertaMarketplaceFetchWrapped=true;
  var originalFetch=window.fetch;
  window.fetch=function(input,init){
    try{
      var url=typeof input==='string'?input:(input&&input.url)||'';
      if(url.indexOf('/api/opportunities-central')!==-1&&init&&typeof init.body==='string'){
        var body=JSON.parse(init.body);body.marketplaces=selected();init=Object.assign({},init,{body:JSON.stringify(body)});
      }
    }catch(e){}
    return originalFetch.call(this,input,init);
  };
})();
</script>'''

try:
    # Remove the previous structural selector and the original V11.9 selector.
    HTML = re.sub(r'<style>\s*#oferta-market-filter[\s\S]*?</script>\s*', '', HTML, count=1)
    HTML = re.sub(r'<style>\s*#v119-market-filter[\s\S]*?</script>\s*', '', HTML, count=1)
    HTML = re.sub(r'<div id="oferta-market-filter"[\s\S]*?</script>\s*', '', HTML, count=1)
    HTML = re.sub(r'<div id="v119-market-filter"[\s\S]*?</script>\s*', '', HTML, count=1)

    anchor = re.search(r'<input\s+id="opportunityNiche"\b[^>]*>', HTML)
    if anchor:
        HTML = HTML[:anchor.start()] + _V1120_UI + '\n' + HTML[anchor.start():]
        print('[V11.10.12] seletor único fixado diretamente antes de opportunityNiche', flush=True)
    elif '</body>' in HTML:
        HTML = HTML.replace('</body>', _V1120_UI + '</body>', 1)
        print('[V11.10.12] seletor inserido antes de </body> (fallback)', flush=True)
    else:
        print('[V11.10.12] ERRO: âncora opportunityNiche não encontrada', flush=True)
except Exception as exc:
    print(f'[V11.10.12] falha controlada na UI: {exc}', flush=True)

print('[V11.10.12] vendas ML via /products/{id}; seletor estrutural único ativo', flush=True)
