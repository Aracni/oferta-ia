"""V11.11.11 — fallback de vendas via item vencedor do catálogo.

Quando /products/{id} não expõe sold_quantity, usa o item_id do buy_box_winner
para consultar /items/{item_id}, sem inventar vendas e com consultas paralelas.
"""
import math
from concurrent.futures import ThreadPoolExecutor, as_completed

_V116_STATS = {"item_requests": 0, "sold_found": 0, "errors": 0, "forbidden": 0}
_V116_MAX_WORKERS = 5


def _v116_num(value):
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


def _v116_item_id(product):
    if not isinstance(product, dict):
        return None
    winner = product.get("buy_box_winner")
    if isinstance(winner, dict):
        value = str(winner.get("item_id") or "").upper().strip()
        if value.startswith("MLB") and value[3:].isdigit():
            return value
    return None


def _v116_item(item_id, token):
    if not item_id or not token:
        return item_id, None, None
    try:
        data, status = _v11_fetch_json(
            token,
            f"https://api.mercadolibre.com/items/{item_id}",
            timeout=6,
            stage="ENRICH_V11_11_ITEM_SALES",
        )
        return item_id, data if isinstance(data, dict) else None, int(status or 0)
    except Exception:
        return item_id, None, None


def _v116_rescore(item):
    old_score = _v116_num(item.get("opportunity_score"))
    sold = _v116_num(item.get("sold_quantity"))
    rating = _v116_num(item.get("rating"))
    discount = _v116_num(item.get("discount_rate"))
    price = _v116_num(item.get("current_price"))
    signals = []
    if sold is not None:
        signals.append((min(100.0, math.log1p(max(0, sold)) / math.log1p(10000) * 100.0), 0.45))
    if rating is not None:
        signals.append((rating / 5.0 * 100.0, 0.20))
    if discount is not None:
        signals.append((min(100.0, max(0.0, discount / 60.0 * 100.0)), 0.20))
    if price is not None:
        signals.append((100.0 if price <= 50 else 90.0 if price <= 100 else 75.0 if price <= 200 else 60.0, 0.15))
    if not signals:
        return old_score
    total = sum(weight for _, weight in signals)
    fresh = sum(value * weight for value, weight in signals) / total
    return round(old_score * 0.35 + fresh * 0.65, 2) if old_score is not None else round(fresh, 2)


_original_enrich_v116 = _v119_enrich_ml


def _v116_enrich_ml(items):
    global _V116_STATS
    _V116_STATS = {"item_requests": 0, "sold_found": 0, "errors": 0, "forbidden": 0}
    enriched = _original_enrich_v116(items)
    try:
        token = _v9_valid_meli_token()
    except Exception:
        token = None

    pending = {}
    for item in enriched:
        if not isinstance(item, dict) or item.get("sold_quantity") is not None:
            continue
        pid = str(item.get("catalog_product_id") or item.get("product_id") or "").upper().strip()
        if not pid or not token:
            continue
        try:
            product = _v111_product(pid, token)
        except Exception:
            product = None
        item_id = _v116_item_id(product)
        if item_id:
            pending[item_id] = pid

    results = {}
    if pending:
        with ThreadPoolExecutor(max_workers=min(_V116_MAX_WORKERS, len(pending))) as pool:
            futures = [pool.submit(_v116_item, item_id, token) for item_id in pending]
            for future in as_completed(futures):
                item_id, data, status = future.result()
                _V116_STATS["item_requests"] += 1
                if status in (401, 403):
                    _V116_STATS["forbidden"] += 1
                elif status is None or not (200 <= int(status) < 300):
                    _V116_STATS["errors"] += 1
                results[item_id] = data

    # Reaproveita a associação produto -> item vencedor sem alterar candidatos.
    for item in enriched:
        if not isinstance(item, dict) or item.get("sold_quantity") is not None:
            continue
        pid = str(item.get("catalog_product_id") or item.get("product_id") or "").upper().strip()
        if not pid:
            continue
        product = _v111_product(pid, token) if token else None
        item_id = _v116_item_id(product)
        data = results.get(item_id)
        sold = _v116_num(data.get("sold_quantity")) if isinstance(data, dict) else None
        if sold is None or sold < 0:
            continue
        sold = int(sold)
        _V116_STATS["sold_found"] += 1
        item["sold_quantity"] = sold
        item["sales"] = sold
        item["sales_count"] = sold
        item["sales_source"] = "items/{item_id}"
        item["demand_index"] = round(min(100.0, math.log1p(max(0, sold)) / math.log1p(10000) * 100.0), 2)
        item["score_provisional"] = item.get("rating") is None
        item["data_confidence"] = "alta" if item.get("rating") is not None and item.get("discount_rate") is not None else "média"
        item["confidence"] = item["data_confidence"]
        item["opportunity_score"] = _v116_rescore(item)
        item["enrichment_version"] = "V11.11.11"

    print(
        "[V11.11.11] fallback item winner: "
        f"requests={_V116_STATS['item_requests']} "
        f"sold_found={_V116_STATS['sold_found']} "
        f"errors={_V116_STATS['errors']} forbidden={_V116_STATS['forbidden']} "
        f"workers={_V116_MAX_WORKERS}",
        flush=True,
    )
    return enriched


_v119_enrich_ml = _v116_enrich_ml
print("[V11.11.11] fallback item winner ativo | /items/{item_id}", flush=True)
