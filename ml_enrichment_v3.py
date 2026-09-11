"""OFERTA IA V11.11.6 — enriquecimento confiável do Mercado Livre."""
import math
import time
import urllib.parse
from fastapi import Body

_V111_PRODUCT_CACHE = {}
_V111_REVIEWS_CACHE = {}
_V111_PRODUCT_TTL = 300
_V111_REVIEWS_TTL = 300
_V111_REVIEWS_BLOCKED = False
_V111_STATS = {"product_ok": 0, "product_fail": 0, "sold_found": 0, "rating_found": 0, "reviews_ok": 0, "reviews_blocked": 0}


def _v111_num(value):
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


def _v111_cache_get(cache, key, ttl):
    entry = cache.get(key)
    if not entry:
        return None
    if time.time() - entry[0] > ttl:
        cache.pop(key, None)
        return None
    return entry[1]


def _v111_product(pid, token):
    pid = str(pid or "").upper().strip()
    if not pid or not token:
        return None
    cached = _v111_cache_get(_V111_PRODUCT_CACHE, pid, _V111_PRODUCT_TTL)
    if cached is not None:
        return cached
    try:
        data, status = _v11_fetch_json(token, f"https://api.mercadolibre.com/products/{pid}", timeout=8, stage="ENRICH_V11_11")
        if isinstance(data, dict) and status and 200 <= int(status) < 300:
            _V111_PRODUCT_CACHE[pid] = (time.time(), data)
            _V111_STATS["product_ok"] += 1
            try:
                _v11_remember_product(data)
            except Exception:
                pass
            return data
    except Exception:
        pass
    _V111_STATS["product_fail"] += 1
    return None


def _v111_sold(product, winner, row, item):
    for obj in (winner, product, row, item):
        if not isinstance(obj, dict):
            continue
        value = _v111_num(obj.get("sold_quantity"))
        if value is not None and value >= 0:
            return int(value), "products/buy_box_winner" if obj is winner or obj is product else "catalog"
    return None, None


def _v111_item_id(product, winner, row, item):
    for obj in (winner, row, item, product):
        if not isinstance(obj, dict):
            continue
        for key in ("item_id", "id"):
            value = str(obj.get(key) or "").strip().upper()
            if value.startswith("MLB") and value[3:].isdigit() and len(value) > 6:
                return value
    return None


def _v111_reviews(item_id, product_id, token):
    global _V111_REVIEWS_BLOCKED
    if not item_id or not token or _V111_REVIEWS_BLOCKED:
        return None
    key = f"{item_id}|{product_id}"
    cached = _v111_cache_get(_V111_REVIEWS_CACHE, key, _V111_REVIEWS_TTL)
    if cached is not None:
        return cached
    query = urllib.parse.urlencode({"catalog_product_id": product_id}) if product_id else ""
    url = f"https://api.mercadolibre.com/reviews/item/{item_id}"
    if query:
        url += "?" + query
    try:
        data, status = _v11_fetch_json(token, url, timeout=5, stage="REVIEWS_V11_11")
        status = int(status or 0)
        if isinstance(data, dict) and 200 <= status < 300:
            _V111_REVIEWS_CACHE[key] = (time.time(), data)
            _V111_STATS["reviews_ok"] += 1
            return data
        if status in (401, 403):
            _V111_REVIEWS_BLOCKED = True
            _V111_STATS["reviews_blocked"] += 1
    except Exception:
        pass
    return None


def _v111_rating(product, winner, row, item, reviews):
    if isinstance(reviews, dict):
        for key in ("rating_average", "stars"):
            value = _v111_num(reviews.get(key))
            if value is not None and 0 < value <= 5:
                total = None
                paging = reviews.get("paging")
                if isinstance(paging, dict):
                    total = _v111_num(paging.get("total"))
                return value, int(total) if total is not None and total >= 0 else None, "reviews"
    for obj in (winner, product, row, item):
        if not isinstance(obj, dict):
            continue
        for key in ("rating", "product_rating", "review_rating"):
            value = _v111_num(obj.get(key))
            if value is not None and 0 < value <= 5:
                return value, None, "catalog"
    return None, None, None


def _v111_discount(item, winner):
    current = _v111_num(item.get("current_price"))
    if current is None:
        current = _v111_num(winner.get("price")) if isinstance(winner, dict) else None
    old = _v111_num(item.get("old_price"))
    if old is None and isinstance(winner, dict):
        old = _v111_num(winner.get("original_price"))
    discount = _v111_num(item.get("discount_rate"))
    if discount is None and old and current and old > current:
        discount = round((old - current) / old * 100.0, 2)
    return current, old, discount


def _v111_score(item, sold, rating, discount):
    old_score = _v111_num(item.get("opportunity_score"))
    signals = []
    if sold is not None:
        demand = min(100.0, math.log1p(max(0, sold)) / math.log1p(10000) * 100.0)
        signals.append((demand, 0.35))
    if rating is not None:
        signals.append((rating / 5.0 * 100.0, 0.20))
    if discount is not None:
        signals.append((min(100.0, max(0.0, discount / 60.0 * 100.0)), 0.25))
    price = _v111_num(item.get("current_price"))
    if price is not None:
        signals.append((100.0 if price <= 50 else 90.0 if price <= 100 else 75.0 if price <= 200 else 60.0, 0.20))
    if not signals:
        return old_score
    total = sum(weight for _, weight in signals)
    fresh = sum(value * weight for value, weight in signals) / total
    if old_score is None:
        return round(fresh, 2)
    return round(old_score * 0.35 + fresh * 0.65, 2)


def _v111_enrich_ml(items):
    global _V111_STATS
    _V111_STATS = {key: 0 for key in _V111_STATS}
    enriched = []
    try:
        token = _v9_valid_meli_token()
    except Exception:
        token = None
    for original in list(items or []):
        item = dict(original or {})
        row = _v119_row(item)
        pid = str(item.get("catalog_product_id") or item.get("product_id") or row.get("catalog_product_id") or row.get("product_id") or "").upper().strip()
        product = _v111_product(pid, token) if token and pid else None
        winner = product.get("buy_box_winner") if isinstance(product, dict) else None
        winner = winner if isinstance(winner, dict) else {}
        item_id = _v111_item_id(product, winner, row, item)
        reviews = _v111_reviews(item_id, pid, token) if item_id and token else None
        sold, sold_source = _v111_sold(product, winner, row, item)
        rating, review_count, rating_source = _v111_rating(product, winner, row, item, reviews)
        if sold is not None:
            _V111_STATS["sold_found"] += 1
        if rating is not None:
            _V111_STATS["rating_found"] += 1
        current, old, discount = _v111_discount(item, winner)
        if current is not None:
            item["current_price"] = current
        if old is not None:
            item["old_price"] = old
        if discount is not None:
            item["discount_rate"] = discount
        if sold is not None:
            item["sold_quantity"] = sold
            item["sales"] = sold
            item["sales_count"] = sold
            item["sales_source"] = sold_source
            item["demand_index"] = round(min(100.0, math.log1p(max(0, sold)) / math.log1p(10000) * 100.0), 2)
        else:
            item["sold_quantity"] = None
            item["sales"] = None
            item["sales_count"] = None
            item["sales_source"] = None
            item["demand_index"] = None
        if rating is not None:
            item["rating"] = rating
            item["rating_score"] = round(rating / 5.0 * 100.0, 2)
            item["rating_source"] = rating_source
        else:
            item["rating"] = None
            item["rating_score"] = None
            item["rating_source"] = None
        item["review_count"] = review_count
        available = sum(value is not None for value in (sold, rating, discount, current))
        confidence = "alta" if available >= 4 else "média" if available >= 2 else "baixa"
        item["data_confidence"] = confidence
        item["confidence"] = confidence
        item["score_provisional"] = sold is None or rating is None
        item["commission_rate"] = None
        item["commission_value"] = None
        item["earnings"] = None
        item["commission_source"] = "não disponível no catálogo público"
        item["opportunity_score"] = _v111_score(item, sold, rating, discount)
        item["enrichment_version"] = "V11.11.6"
        enriched.append(item)
    return enriched


_v119_enrich_ml = _v111_enrich_ml
_original_central = _v119_central


def _v111_central(payload: dict = Body(default={} )):
    try:
        result = _original_central(payload)
        if not isinstance(result, dict):
            raise RuntimeError("O motor central retornou uma resposta inválida.")
    except Exception as exc:
        message = f"{type(exc).__name__}: {str(exc)[:500]}"
        try:
            _append_log(app, "ERROR", "V11.11 motor central falhou", error=message)
        except Exception:
            pass
        print(f"[V11.11][ERRO] Motor central: {message}", flush=True)
        return {
            "status": "error",
            "items": [],
            "opportunities": [],
            "returned": 0,
            "candidates_found": 0,
            "diagnostic": [f"V11.11 ERRO REAL: {message}"],
            "message": f"⚠️ V11.11 encontrou um erro: {message}",
        }
    diagnostics = list(result.get("diagnostic") or [])
    diagnostics.append("V11.11 ML: " + f"products_ok={_V111_STATS['product_ok']} sold={_V111_STATS['sold_found']} rating={_V111_STATS['rating_found']} reviews_ok={_V111_STATS['reviews_ok']} reviews_403={_V111_STATS['reviews_blocked']}")
    result["diagnostic"] = diagnostics
    result["message"] = " · ".join(diagnostics)
    return result


for _route in getattr(app, "routes", []):
    if getattr(_route, "path", None) == "/api/opportunities-central" and "POST" in (getattr(_route, "methods", set()) or set()):
        _route.endpoint = _v111_central
        try:
            from fastapi.dependencies.utils import get_dependant
            from fastapi.routing import request_response
            _route.dependant = get_dependant(path=_route.path, call=_v111_central)
            _base_route_app = request_response(_route.get_route_handler())
            try:
                import meli_fast as _meli_fast
                async def _v111_route_app(scope, receive, send, _original=_base_route_app):
                    return await _meli_fast._asgi(scope, receive, send, _original)
                _route.app = _v111_route_app
            except Exception:
                _route.app = _base_route_app
            print("[V11.11.6] rota central reconstruída com BODY JSON + endpoint V11.11", flush=True)
        except Exception as exc:
            print(f"[V11.11.6][ERRO] reconstrução da rota: {type(exc).__name__}: {str(exc)[:500]}", flush=True)
        break

print("[V11.11.6] enriquecimento ML ativo | /products + reviews | BODY JSON corrigido | comissão não inventada", flush=True)
