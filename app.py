"""OFERTA IA V11.10.1.
Preserva o seletor seguro de marketplace e melhora o enriquecimento do Mercado Livre.
"""
import math
import time
import urllib.request

_BASE = "https://raw.githubusercontent.com/Aracni/oferta-ia/639b53c7e97152b2756e70eef2940454ae3420d7/app.py"
try:
    with urllib.request.urlopen(_BASE, timeout=20) as response:
        source = response.read().decode("utf-8")
except Exception as exc:
    raise RuntimeError(f"Não foi possível carregar o núcleo V11.9 do OFERTA IA: {exc}") from exc

exec(compile(source, _BASE, "exec"), globals(), globals())

# ============================================================
# V11.10.1 — ENRIQUECIMENTO ML
# ============================================================
_V110_REVIEW_CACHE = {}
_V110_REVIEW_TTL = 900
_V110_PRODUCT_CACHE = {}
_V110_PRODUCT_TTL = 300


def _v110_cache_get(cache, key, ttl):
    entry = cache.get(key)
    if not entry:
        return None
    if time.time() - entry[0] > ttl:
        cache.pop(key, None)
        return None
    return entry[1]


def _v110_public_product(pid, token):
    pid = str(pid or "").upper()
    if not pid or not token:
        return None
    cached = _v110_cache_get(_V110_PRODUCT_CACHE, pid, _V110_PRODUCT_TTL)
    if cached is not None:
        return cached
    try:
        with _V11_LOCK:
            product = dict(_V11_PRODUCT_INDEX.get(pid, {}))
        if not product:
            data, status = _v11_fetch_json(
                token,
                f"https://api.mercadolibre.com/products/{pid}",
                timeout=8,
                stage="CATALOG",
            )
            if isinstance(data, dict) and status and 200 <= int(status) < 300:
                product = data
                _v11_remember_product(data)
        _V110_PRODUCT_CACHE[pid] = (time.time(), product or {})
        return product or None
    except Exception:
        return None


def _v110_reviews(item_id, catalog_product_id, token):
    iid = str(item_id or "").upper()
    pid = str(catalog_product_id or "").upper()
    if not iid or not token:
        return None
    key = f"{iid}:{pid}"
    cached = _v110_cache_get(_V110_REVIEW_CACHE, key, _V110_REVIEW_TTL)
    if cached is not None:
        return cached
    try:
        params = {"limit": 1}
        if pid:
            params["catalog_product_id"] = pid
        data, status = _v11_fetch_json(
            token,
            f"https://api.mercadolibre.com/reviews/item/{iid}",
            params=params,
            timeout=7,
            stage="REVIEWS",
        )
        if isinstance(data, dict) and status and 200 <= int(status) < 300:
            paging = data.get("paging") if isinstance(data.get("paging"), dict) else {}
            result = {
                "rating_average": data.get("rating_average"),
                "review_total": paging.get("total"),
            }
            _V110_REVIEW_CACHE[key] = (time.time(), result)
            return result
    except Exception as exc:
        print(f"[V11.10.1] reviews indisponível para {iid}: {str(exc)[:120]}", flush=True)
    _V110_REVIEW_CACHE[key] = (time.time(), {})
    return None


def _v110_enrich_ml(items):
    enriched = []
    try:
        token = _v9_valid_meli_token()
    except Exception:
        token = None

    for original in list(items or []):
        item = dict(original or {})
        row = _v119_row(item)
        pid = str(
            item.get("catalog_product_id")
            or item.get("product_id")
            or row.get("product_id")
            or ""
        ).upper()
        product = _v110_public_product(pid, token) if token and pid else None
        winner = product.get("buy_box_winner") if isinstance(product, dict) else None
        winner = winner if isinstance(winner, dict) else {}

        # 1. Vendas: tenta item, oferta vencedora e produto.
        sold = _v119_sold(row, item)
        if sold is None:
            sold = _v119_sold(winner, {})
        if sold is None and isinstance(product, dict):
            sold = _v119_sold(product, {})
        if sold is not None:
            item["sold_quantity"] = int(sold)
            item["sales"] = int(sold)
            item["sales_count"] = int(sold)

        # 2. Avaliações: usa o endpoint público de reviews quando possível.
        rating = _v119_rating(row, item)
        review_total = None
        if token and item.get("item_id"):
            review = _v110_reviews(item.get("item_id"), pid, token)
            if isinstance(review, dict):
                rating = _v119_num(review.get("rating_average")) or rating
                review_total = _v119_num(review.get("review_total"))
        if rating is not None:
            item["rating"] = rating
            item["rating_score"] = round(rating / 5.0 * 100.0, 2)
        if review_total is not None:
            item["review_count"] = int(review_total)

        # 3. Preços e desconto.
        current = _v119_num(item.get("current_price"))
        if current is None:
            current = _v119_num(winner.get("price"))
        if current is None and isinstance(product, dict):
            rng = product.get("buy_box_winner_price_range")
            if isinstance(rng, dict) and isinstance(rng.get("min"), dict):
                current = _v119_num(rng["min"].get("price"))
        if current is not None:
            item["current_price"] = current

        old = _v119_num(item.get("old_price"))
        if old is None:
            old = _v119_num(winner.get("original_price"))
        if old is not None:
            item["old_price"] = old

        discount = _v119_num(item.get("discount_rate"))
        if discount is None and old and current and old > current:
            discount = round((old - current) / old * 100.0, 2)
            item["discount_rate"] = discount

        # 4. Indicadores de demanda e confiança.
        available = sum(x is not None for x in (sold, rating, review_total, discount, current))
        item["data_confidence"] = "alta" if available >= 4 else "média" if available >= 2 else "baixa"
        item["confidence"] = item["data_confidence"]
        item["score_provisional"] = available < 3
        item["demand_index"] = (
            round(min(100.0, math.log1p(max(0, sold)) / math.log1p(10000) * 100.0), 2)
            if sold is not None else None
        )
        if review_total is not None:
            item["review_demand_signal"] = round(
                min(100.0, math.log1p(max(0, review_total)) / math.log1p(5000) * 100.0), 2
            )

        # Comissão de afiliado NÃO é inferida a partir da tarifa de venda do ML.
        item.setdefault("commission_rate", None)
        item.setdefault("commission_value", None)
        item.setdefault("earnings", None)
        item["commission_source"] = "não disponível no catálogo público"

        # 5. Score: dados reais de demanda/reputação passam a pesar mais.
        old_score = _v119_num(item.get("opportunity_score"))
        signals = []
        if sold is not None:
            signals.append((item["demand_index"], 0.30))
        if rating is not None:
            signals.append((rating / 5.0 * 100.0, 0.20))
        if review_total is not None:
            signals.append((item["review_demand_signal"], 0.10))
        if discount is not None:
            signals.append((min(100.0, max(0.0, discount / 60.0 * 100.0)), 0.20))
        if current is not None:
            signals.append((100.0 if current <= 50 else 90.0 if current <= 100 else 75.0 if current <= 200 else 60.0, 0.10))
        if signals:
            total = sum(w for _, w in signals)
            fresh = sum(v * w for v, w in signals) / total
            item["opportunity_score"] = round(
                (old_score * 0.35 + fresh * 0.65) if old_score is not None else fresh,
                2,
            )

        enriched.append(item)
    return enriched


_v119_enrich_ml = _v110_enrich_ml

# ============================================================
# V11.10.1 — SELETOR PRESERVADO
# ============================================================
try:
    _V112_SAFE_UI = r'''<style>
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

    _needle = '<p class="hint">Você não precisa informar um produto. Deixe o nicho vazio para procurar oportunidades em várias categorias. O resultado aparece primeiro; o aprofundamento acontece somente nos melhores candidatos.</p>'
    if 'id="oferta-market-filter"' not in HTML:
        if _needle in HTML:
            HTML = HTML.replace(_needle, _needle + _V112_SAFE_UI, 1)
        elif '</body>' in HTML:
            HTML = HTML.replace('</body>', _V112_SAFE_UI + '</body>', 1)
except Exception as exc:
    print(f"[V11.10.1] UI seletor não aplicada: {exc}", flush=True)

print("[V11.10.1] seletor Marketplace preservado + enriquecimento ML ativo", flush=True)
