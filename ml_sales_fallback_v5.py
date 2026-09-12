"""V11.11.10 — fallback de vendas otimizado do Mercado Livre.

Melhora o V11.11.9 em dois pontos: consulta os produtos em paralelo para
reduzir a latência do endpoint e usa a maior venda encontrada entre as
ofertas do catálogo, em vez de confiar na primeira oferta retornada.
"""
import math
from concurrent.futures import ThreadPoolExecutor, as_completed

_V115_STATS = {"item_requests": 0, "sold_found": 0, "sold_from_items": 0, "errors": 0}
_V115_MAX_WORKERS = 5


def _v115_num(value):
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


def _v115_walk_sold(value):
    """Retorna o MAIOR sold_quantity encontrado em toda a árvore."""
    values = []
    if isinstance(value, dict):
        sold = _v115_num(value.get("sold_quantity"))
        if sold is not None and sold >= 0:
            values.append(int(sold))
        for key in ("results", "items", "offers", "children", "products", "buy_box_winner"):
            if key in value:
                found = _v115_walk_sold(value.get(key))
                if found is not None:
                    values.append(found)
    elif isinstance(value, list):
        for entry in value:
            found = _v115_walk_sold(entry)
            if found is not None:
                values.append(found)
    return max(values) if values else None


def _v115_product_items(pid, token):
    if not pid or not token:
        return pid, None, None
    try:
        data, status = _v11_fetch_json(
            token,
            f"https://api.mercadolibre.com/products/{pid}/items",
            timeout=6,
            stage="ENRICH_V11_11_ITEMS",
        )
        if isinstance(data, (dict, list)) and status and 200 <= int(status) < 300:
            return pid, data, int(status)
        return pid, None, int(status or 0)
    except Exception:
        return pid, None, None


def _v115_rescore(item):
    score = item.get("opportunity_score")
    try:
        old = float(score) if score is not None else 0.0
    except Exception:
        old = 0.0
    sold = _v115_num(item.get("sold_quantity"))
    rating = _v115_num(item.get("rating"))
    discount = _v115_num(item.get("discount_rate"))
    price = _v115_num(item.get("current_price"))
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
        return score
    total = sum(weight for _, weight in signals)
    fresh = sum(value * weight for value, weight in signals) / total
    return round(old * 0.35 + fresh * 0.65, 2) if score is not None else round(fresh, 2)


_original_enrich_v115 = _v119_enrich_ml


def _v115_enrich_ml(items):
    _V115_STATS.update({"item_requests": 0, "sold_found": 0, "sold_from_items": 0, "errors": 0})
    enriched = _original_enrich_v115(items)
    try:
        token = _v9_valid_meli_token()
    except Exception:
        token = None
    pending = []
    seen = set()
    for item in enriched:
        if not isinstance(item, dict) or item.get("sold_quantity") is not None:
            continue
        pid = str(item.get("catalog_product_id") or item.get("product_id") or "").upper().strip()
        if pid and token and pid not in seen:
            seen.add(pid)
            pending.append(pid)
    results = {}
    if pending:
        with ThreadPoolExecutor(max_workers=min(_V115_MAX_WORKERS, len(pending))) as pool:
            futures = [pool.submit(_v115_product_items, pid, token) for pid in pending]
            for future in as_completed(futures):
                pid, data, status = future.result()
                _V115_STATS["item_requests"] += 1
                if status is None or not (200 <= int(status) < 300):
                    _V115_STATS["errors"] += 1
                results[pid] = data
    for item in enriched:
        if not isinstance(item, dict) or item.get("sold_quantity") is not None:
            continue
        pid = str(item.get("catalog_product_id") or item.get("product_id") or "").upper().strip()
        if not pid:
            continue
        sold = _v115_walk_sold(results.get(pid))
        if sold is None:
            continue
        _V115_STATS["sold_found"] += 1
        _V115_STATS["sold_from_items"] += 1
        item["sold_quantity"] = sold
        item["sales"] = sold
        item["sales_count"] = sold
        item["sales_source"] = "products/{id}/items:max"
        item["demand_index"] = round(min(100.0, math.log1p(max(0, sold)) / math.log1p(10000) * 100.0), 2)
        item["score_provisional"] = item.get("rating") is None
        item["data_confidence"] = "alta" if item.get("rating") is not None and item.get("discount_rate") is not None else "média"
        item["confidence"] = item["data_confidence"]
        item["opportunity_score"] = _v115_rescore(item)
        item["enrichment_version"] = "V11.11.10"
    print(
        "[V11.11.10] fallback vendas: "
        f"requests={_V115_STATS['item_requests']} "
        f"sold_found={_V115_STATS['sold_found']} "
        f"errors={_V115_STATS['errors']} workers={_V115_MAX_WORKERS}",
        flush=True,
    )
    return enriched


_v119_enrich_ml = _v115_enrich_ml
print("[V11.11.10] fallback de vendas otimizado ativo | paralelo + maior sold_quantity", flush=True)
