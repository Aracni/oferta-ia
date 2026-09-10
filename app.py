"""OFERTA IA V11.9.
Carrega V11.8 estável e adiciona enriquecimento do Mercado Livre + seletor
Ambos / somente Mercado Livre / somente Shopee.
"""
import re
import urllib.request

_BASE = "https://raw.githubusercontent.com/Aracni/oferta-ia/547783528ebc03dbc0801a9f1a3ce5451f76fe11/app.py"
try:
    with urllib.request.urlopen(_BASE, timeout=20) as response:
        source = response.read().decode("utf-8")
except Exception as exc:
    raise RuntimeError(f"Não foi possível carregar o núcleo V11.8 do OFERTA IA: {exc}") from exc

exec(compile(source, _BASE, "exec"), globals(), globals())

_V119_VERSION = "11.9"
_V119_ORIGINAL_CENTRAL = opportunities_central
_V119_ORIGINAL_ML = mercadolivre_opportunities


def _v119_num(value):
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


def _v119_row(item):
    iid = str((item or {}).get("item_id") or (item or {}).get("id") or "")
    with _V11_LOCK:
        row = dict(_V11_ITEM_INDEX.get(iid, {}))
    return row


def _v119_rating(row, item):
    for obj in (row, item):
        if not isinstance(obj, dict):
            continue
        for key in ("rating", "product_rating", "review_rating", "score"):
            value = _v119_num(obj.get(key))
            if value is not None and 0 < value <= 5:
                return value
    seller = row.get("seller") if isinstance(row.get("seller"), dict) else {}
    rep = seller.get("reputation") if isinstance(seller.get("reputation"), dict) else {}
    for key in ("rating", "seller_rating"):
        value = _v119_num(rep.get(key))
        if value is not None and 0 < value <= 5:
            return value
    return None


def _v119_sold(row, item):
    for obj in (row, item):
        if not isinstance(obj, dict):
            continue
        for key in ("sold_quantity", "sold", "sales", "sales_count"):
            value = _v119_num(obj.get(key))
            if value is not None and value >= 0:
                return int(value)
    return None


def _v119_rescore(item, row, sold, rating, discount):
    old_score = _v119_num(item.get("opportunity_score"))
    signals = []
    if sold is not None:
        demand = min(100.0, (max(0.0, __import__("math").log1p(sold) / __import__("math").log1p(10000)) * 100.0))
        signals.append((demand, 0.30))
    if discount is not None:
        signals.append((min(100.0, max(0.0, discount / 60.0 * 100.0)), 0.25))
    price = _v119_num(item.get("current_price"))
    if price is not None:
        price_score = 100.0 if price <= 50 else 90.0 if price <= 100 else 75.0 if price <= 200 else 60.0
        signals.append((price_score, 0.15))
    if rating is not None:
        signals.append((min(100.0, max(0.0, rating / 5.0 * 100.0)), 0.15))
    if not signals:
        return old_score
    total_weight = sum(w for _, w in signals)
    fresh = sum(v * w for v, w in signals) / total_weight
    if old_score is None:
        return round(fresh, 2)
    return round((old_score * 0.50) + (fresh * 0.50), 2)


def _v119_enrich_ml(items):
    enriched = []
    for original in list(items or []):
        item = dict(original or {})
        row = _v119_row(item)
        sold = _v119_sold(row, item)
        rating = _v119_rating(row, item)
        current = _v119_num(row.get("price") or row.get("current_price"))
        old = _v119_num(row.get("original_price") or item.get("old_price"))
        if current is not None:
            item["current_price"] = current
        if old is not None:
            item["old_price"] = old
        discount = _v119_num(item.get("discount_rate"))
        if discount is None and old and current and old > current:
            discount = round((old-current) / old * 100.0, 2)
            item["discount_rate"] = discount
        if sold is not None:
            item["sold_quantity"] = sold
            item["sales"] = sold
            item["sales_count"] = sold
        if rating is not None:
            item["rating"] = rating
            item["rating_score"] = round(rating / 5.0 * 100.0, 2)
        # Não confundir tarifa de venda do Mercado Livre com comissão de afiliado.
        item.setdefault("commission_rate", None)
        item.setdefault("commission_value", None)
        item.setdefault("earnings", None)
        item["commission_source"] = "não disponível no catálogo público"
        available = sum(x is not None for x in (sold, rating, discount, current))
        confidence = "alta" if available >= 4 else "média" if available >= 2 else "baixa"
        item["data_confidence"] = confidence
        item["confidence"] = confidence
        item["score_provisional"] = sold is None or rating is None
        item["demand_index"] = round(min(100.0, (__import__("math").log1p(sold) / __import__("math").log1p(10000)) * 100.0), 2) if sold is not None else None
        item["opportunity_score"] = _v119_rescore(item, row, sold, rating, discount)
        enriched.append(item)
    return enriched


def _v119_mix(items, limit):
    return _v11_marketplace_mix(_v119_enrich_ml(items), limit)


def _v119_central(payload: dict):
    body = dict(payload or {})
    selected = str(body.get("marketplaces") or "both").lower().strip()
    if selected not in {"both", "mercadolivre", "shopee"}:
        selected = "both"
    try:
        limit = max(5, min(20, int(body.get("limit") or 10)))
    except Exception:
        limit = 10

    if selected == "shopee":
        sh_body = dict(body)
        sh_body["include_meli"] = False
        result = dict(_V119_ORIGINAL_CENTRAL(sh_body))
        items = list(result.get("items") or result.get("opportunities") or [])
        items = items[:limit]
        diagnostics = list(result.get("diagnostic") or [])
        diagnostics.append(f"Filtro: somente Shopee · retorno={len(items)}")
        result["mode"] = "shopee"
        result["engine"] = "OFERTA IA V11.9"
        result["items"] = items
        result["opportunities"] = items
        result["returned"] = len(items)
        result["diagnostic"] = diagnostics
        result["message"] = " · ".join(diagnostics)
        return result

    if selected == "mercadolivre":
        ml_result = _V119_ORIGINAL_ML({"niche": body.get("niche") or "", "limit": limit})
        items = _v119_enrich_ml(list(ml_result.get("items") or ml_result.get("opportunities") or []))[:limit]
        diagnostics = list(ml_result.get("diagnostic") or [])
        diagnostics.append(f"Filtro: somente Mercado Livre · retorno={len(items)}")
        result = dict(ml_result)
        result["mode"] = "mercadolivre"
        result["engine"] = "OFERTA IA V11.9"
        result["items"] = items
        result["opportunities"] = items
        result["returned"] = len(items)
        result["diagnostic"] = diagnostics
        result["message"] = " · ".join(diagnostics)
        return result

    # Ambos: reaproveita o fluxo multimarketplace estável da V11.8 e enriquece ML.
    result = dict(_V119_ORIGINAL_CENTRAL(body))
    items = list(result.get("items") or result.get("opportunities") or [])
    items = _v119_mix(items, limit)
    diagnostics = list(result.get("diagnostic") or [])
    ml_count = sum(1 for x in items if str(x.get("marketplace") or "").lower() == "mercadolivre")
    sh_count = sum(1 for x in items if str(x.get("marketplace") or "").lower() == "shopee")
    diagnostics.append(f"V11.9: Mercado Livre={ml_count} · Shopee={sh_count} · retorno={len(items)} · dados ML enriquecidos")
    result["mode"] = "completo"
    result["engine"] = "OFERTA IA V11.9"
    result["items"] = items
    result["opportunities"] = items
    result["returned"] = len(items)
    result["diagnostic"] = diagnostics
    result["message"] = " · ".join(diagnostics)
    return result

for _route in getattr(app, "routes", []):
    if getattr(_route, "path", None) == "/api/opportunities-central" and "POST" in (getattr(_route, "methods", set()) or set()):
        _route.endpoint = _v119_central
        try:
            _route.dependant.call = _v119_central
        except Exception:
            pass

# UI: seletor exclusivo, com Ambos como padrão. O JS intercepta o payload
# existente para não depender da estrutura interna do formulário V11.8.
try:
    _V119_UI = r'''<style>
#v119-market-filter{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0 14px;padding:10px;border-radius:12px;background:rgba(127,127,127,.10);align-items:center}
#v119-market-filter .v119-title{font-weight:700;margin-right:4px}
#v119-market-filter label{display:inline-flex;align-items:center;gap:6px;padding:7px 10px;border:1px solid rgba(127,127,127,.28);border-radius:9px;cursor:pointer;user-select:none}
#v119-market-filter input{accent-color:currentColor}
#v119-market-filter label.v119-active{font-weight:700;box-shadow:0 0 0 1px currentColor inset}
</style>
<div id="v119-market-filter" aria-label="Marketplace">
  <span class="v119-title">Marketplace:</span>
  <label><input type="checkbox" name="v119_market" value="both" checked> Ambos</label>
  <label><input type="checkbox" name="v119_market" value="mercadolivre"> Mercado Livre</label>
  <label><input type="checkbox" name="v119_market" value="shopee"> Shopee</label>
</div>
<script>
(function(){
  const box=document.getElementById('v119-market-filter'); if(!box) return;
  const inputs=[...box.querySelectorAll('input[name=v119_market]')];
  function selected(){const x=inputs.find(i=>i.checked);return x?x.value:'both'}
  function paint(){inputs.forEach(i=>i.closest('label').classList.toggle('v119-active',i.checked))}
  inputs.forEach(i=>i.addEventListener('change',function(){inputs.forEach(x=>{if(x!==i)x.checked=false});if(!inputs.some(x=>x.checked))inputs[0].checked=true;paint();localStorage.setItem('oferta_ia_marketplace',selected())}));
  const saved=localStorage.getItem('oferta_ia_marketplace'); if(saved&&inputs.some(i=>i.value===saved)){inputs.forEach(i=>i.checked=i.value===saved)} paint();
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
    if "id=\"v119-market-filter\"" not in HTML and "</body>" in HTML:
        HTML = HTML.replace("</body>", _V119_UI + "</body>")
except Exception:
    pass

print("[V11.9] Mercado Livre enriquecido + filtro exclusivo Ambos/Mercado Livre/Shopee; padrão=Ambos", flush=True)
