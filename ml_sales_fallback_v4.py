"""V11.11.4 — fallback de vendas do Mercado Livre.

Complementa o enriquecimento sem inventar dados: quando /products/{id} não
entrega sold_quantity, consulta /products/{id}/items e procura sold_quantity
nas ofertas retornadas. Avaliações continuam dependendo de /reviews/item.
"""
import math

_V114_STATS = {"item_requests": 0, "sold_found": 0, "sold_from_items": 0}


def _v114_num(value):
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


def _v114_walk_sold(value):
    if isinstance(value, dict):
        sold = _v114_num(value.get("sold_quantity"))
        if sold is not None and sold >= 0:
            return int(sold)
        for key in ("results", "items", "offers", "children", "products", "buy_box_winner"):
            if key in value:
                found = _v114_walk_sold(value.get(key))
                if found is not None:
                    return found
    elif isinstance(value, list):
        for entry in value:
            found = _v114_walk_sold(entry)
            if found is not None:
                return found
    return None


def _v114_product_items(pid, token):
    if not pid or not token:
        return None
    try:
        data, status = _v11_fetch_json(
            token,
            f"https://api.mercadolibre.com/products/{pid}/items",
            timeout=6,
            stage="ENRICH_V11_11_ITEMS",
        )
        _V114_STATS["item_requests"] += 1
        if isinstance(data, (dict, list)) and status and 200 <= int(status) < 300:
            return data
    except Exception:
        pass
    return None


def _v114_rescore(item):
    score = item.get("opportunity_score")
    try:
        old = float(score) if score is not None else 0.0
    except Exception:
        old = 0.0
    sold = _v114_num(item.get("sold_quantity"))
    rating = _v114_num(item.get("rating"))
    discount = _v114_num(item.get("discount_rate"))
    price = _v114_num(item.get("current_price"))
    signals = []
    if sold is not None:
        signals.append((min(100.0, math.log1p(max(0, sold)) / math.log1p(10000) * 100.0, 0.45))
    if rating is not None:
        signals.append((rating / 5.0 * 100.0, 0.20))
    if discount is not None:
        signals.append((min(100.0, max(0.0, discount / 60.0 * 100.0)), 0.20))
    if price is not None:
        signals.append((100.0 if price <= 50 else 90.0 if price <= 100 else 75.0 if price <= 200 else 60.0, 0.15))
    if not signals:
        return score
    total = sum(w for _, _, w in signals)
    fresh = sum(v * w for v, _, w in signals) / total
    return round(old * 0.35 + fresh * 0.65, 2) if score is not None else round(fresh, 2)


_original_enrich_v114 = _v119_enrich_ml


def _v114_enrich_ml(items):
    enriched = _original_enrich_v114(items)
    try:
        token = _v9_valid_meli_token()
    except Exception:
        token = None
    for item in enriched:
        if not isinstance(item, dict) or item.get("sold_quantity") is not None:
            continue
        pid = str(item.get("catalog_product_id") or item.get("product_id") or "").upper().strip()
        if not pid or not token:
            continue
        data = _v114_product_items(pid, token)
        sold = _v114_walk_sold(data)
        if sold is None:
            continue
        _V114_STATS["sold_found"] += 1
        _V114_STATS["sold_from_items"] += 1
        item["sold_quantity"] = sold
        item["sales"] = sold
        item["sales_count"] = sold
        item["sales_source"] = "products/{id}/items"
        item["demand_index"] = round(min(100.0, math.log1p(max(0, sold)) / math.log1p(10000) * 100.0), 2)
        item["score_provisional"] = item.get("rating") is None
        item["data_confidence"] = "alta" if item.get("rating") is not None and item.get("discount_rate") is not None else "média"
        item["confidence"] = item["data_confidence"]
        item["opportunity_score"] = _v114_rescore(item)
        item["enrichment_version"] = "V11.11.4"
    return enriched


_v119_enrich_ml = _v114_enrich_ml

_original_central_v114 = _v111_central


def _v114_central(payload):
    result = _original_central_v114(payload)
    if isinstance(result, dict):
        diagnostic = list(result.get("diagnostic") or [])
        diagnostic.append(
            "V11.11.4 vendas ML: "
            f"items_requests={_V114_STATS['item_requests']} "
            f"sold_fallback={_V114_STATS['sold_from_items']}"
        )
        result["diagnostic"] = diagnostic
        result["message"] = " · ".join(diagnostic)
    return result

for _route in getattr(app, "routes", []):
    if getattr(_route, "path", None) == "/api/opportunities-central" and "POST" in (getattr(_route, "methods", set()) or set()):
        _route.endpoint = _v114_central
        try:
            from fastapi.dependencies.utils import get_dependant
            from fastapi.routing import request_response
            _route.dependant = get_dependant(path=_route.path, call=_v114_central)
            _route.app = request_response(_route.get_route_handler())
            try:
                import meli_fast as _meli_fast
                _base = _route.app
                async def _v114_route_app(scope, receive, send, _original=_base):
                    return await _meli_fast._asgi(scope, receive, send, _original)
                _route.app = _v114_route_app
            except Exception:
                pass
        except Exception as exc:
            print(f"[V11.11.4][ERRO] rota: {type(exc).__name__}: {str(exc)[:300]}", flush=True)
        break

print("[V11.11.4] fallback de vendas via /products/{id}/items ativo", flush=True)
