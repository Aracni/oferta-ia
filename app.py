"""OFERTA IA V11.10.
Mantém o seletor seguro da V11.9 e melhora o enriquecimento do Mercado Livre
usando dados públicos do catálogo e avaliações.
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
    if not pid:
        return None
    cached = _v110_cache_get(_V110_PRODUCT_CACHE, pid, _V110_PRODUCT_TTL)
    if cached is not None:
        return cached
    try:
        with _V11_LOCK:
            product = dict(_V11_PRODUCT_INDEX.get(pid, {}))
        if not product:
            data, status = _v11_fetch_json(token, f"https://api.mercadolibre.com/products/{pid}", timeout=8, stage="CATALOG")
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
    if not iid:
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
            result = {
                "rating_average": data.get("rating_average"),
                "review_total": ((data.get("paging") or {}).get("total") if isinstance(data.get("paging"), dict) else None),
            }
            _V110_REVIEW_CACHE[key] = (time.time(), result)
            return result
    except Exception as exc:
        print(f"[V11.10] reviews indisponível para {iid}: {str(exc)[:120]}", flush=True)
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
        pid = str(item.get("catalog_product_id") or item.get("product_id") or row.get("product_id") or "").upper()
        product = _v110_public_product(pid, token) if token and pid else None
        winner = product.get("buy_box_winner") if isinstance(product, dict) else None
        winner = winner if isinstance(winner, dict) else {}

        sold = _v119_sold(row, item)
        if sold is None:
            sold = _v119_sold(winner, {})
        if sold is None and isinstance(product, dict):
            sold = _v119_sold(product, {})
        if sold is not None:
            item["sold_quantity"] = int(sold)
            item["sales"] = int(sold)
            item["sales_count"] = int(sold)

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

        current = _v119_num(item.get("current_price"))
        if current is None:
            current = _v119_num(winner.get("price")) or _v119_num((product or {}).get("buy_box_winner_price_range", {}).get("min", {}).get("price") if isinstance((product or {}).get("buy_box_winner_price_range"), dict) and isinstance((product or {}).get("buy_box_winner_price_range", {}).get("min"), dict) else None)
            if current is not None:
                item["current_price"] = current
        old = _v119_num(item.get("old_price")) or _v119_num(winner.get("original_price"))
        if old is not None:
            item["old_price"] = old
        discount = _v119_num(item.get("discount_rate"))
        if discount is None and old and current and old > current:
            discount = round((old - current) / old * 100.0, 2)
            item["discount_rate"] = discount

        available = sum(x is not None for x in (sold, rating, review_total, discount, current))
        item["data_confidence"] = "alta" if available >= 4 else "média" if available >= 2 else "baixa"
        item["confidence"] = item["data_confidence"]
        item["score_provisional"] = available < 3
        item["demand_index"] = round(min(100.0, math.log1p(max(0, sold)) / math.log1p(10000) * 100.0), 2) if sold is not None else None
        if review_total is not None:
            item["review_demand_signal"] = round(min(100.0, math.log1p(max(0, review_total)) / math.log1p(5000) * 100.0), 2)

        # Comissão de afiliado continua separada e desconhecida sem integração própria.
        item.setdefault("commission_rate", None)
        item.setdefault("commission_value", None)
        item.setdefault("earnings", None)
        item["commission_source"] = "não disponível no catálogo público"

        # Recalcula o score com vendas/avaliações quando disponíveis.
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
            item["opportunity_score"] = round((old_score * 0.35 + fresh * 0.65) if old_score is not None else fresh, 2)

        enriched.append(item)
    return enriched


# Substitui apenas o enriquecimento ML. O seletor da V11.9 permanece intacto.
_v119_enrich_ml = _v110_enrich_ml

print("[V11.10] Mercado Livre: vendas + avaliações públicas + reviews_count; seletor V11.9 preservado", flush=True)
