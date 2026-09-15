"""OFERTA IA V12.5 — sinais de mercado do Mercado Livre.

Versão com namespace próprio para não colidir com variáveis/funções dos fallbacks
de vendas carregados no mesmo namespace do app.py.
"""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

_V125_MARKET_HIGHLIGHT_CACHE = {}
_V125_MARKET_HIGHLIGHT_TTL = 900
_V125_MARKET_MAX_WORKERS = 5
_V125_MARKET_STATS = {"highlight_requests": 0, "highlight_ok": 0, "highlight_404": 0, "highlight_errors": 0}


def _v125_market_num(value):
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


def _v125_market_cache_get(key):
    entry = _V125_MARKET_HIGHLIGHT_CACHE.get(key)
    if not entry:
        return None
    if time.time() - entry[0] > _V125_MARKET_HIGHLIGHT_TTL:
        _V125_MARKET_HIGHLIGHT_CACHE.pop(key, None)
        return None
    return entry[1]


def _v125_market_highlight(pid, token):
    pid = str(pid or "").upper().strip()
    if not pid or not token:
        return None, None
    cached = _v125_market_cache_get(pid)
    if cached is not None:
        return cached
    try:
        data, status = _v11_fetch_json(
            token,
            f"https://api.mercadolibre.com/highlights/MLB/product/{pid}",
            timeout=5,
            stage="MARKET_SIGNALS_V12_5",
        )
        status = int(status or 0)
        _V125_MARKET_STATS["highlight_requests"] += 1
        if isinstance(data, dict) and 200 <= status < 300:
            result = (data.get("position"), data)
            _V125_MARKET_HIGHLIGHT_CACHE[pid] = (time.time(), result)
            _V125_MARKET_STATS["highlight_ok"] += 1
            return result
        if status == 404:
            _V125_MARKET_STATS["highlight_404"] += 1
        else:
            _V125_MARKET_STATS["highlight_errors"] += 1
    except Exception:
        _V125_MARKET_STATS["highlight_requests"] += 1
        _V125_MARKET_STATS["highlight_errors"] += 1
    _V125_MARKET_HIGHLIGHT_CACHE[pid] = (time.time(), (None, None))
    return None, None


def _v125_market_winner_signals(product, item):
    winner = product.get("buy_box_winner") if isinstance(product, dict) else None
    winner = winner if isinstance(winner, dict) else {}
    candidate_item_id = str(item.get("item_id") or item.get("ml_item_id") or "").upper().strip()
    winner_item_id = str(winner.get("item_id") or "").upper().strip()
    shipping = winner.get("shipping") if isinstance(winner.get("shipping"), dict) else {}
    tags = shipping.get("tags") if isinstance(shipping.get("tags"), list) else []
    tags_text = " ".join(str(x).lower() for x in tags)
    logistic = str(shipping.get("logistic_type") or "").lower().strip()
    free_shipping = bool(shipping.get("free_shipping")) or "free_shipping" in tags_text or "mandatory_free_shipping" in tags_text
    fulfillment = logistic in {"fulfillment", "full"} or "fulfillment" in tags_text
    official_store = winner.get("official_store_id") not in (None, "", 0, "0")
    reputation = str((winner.get("seller") or {}).get("reputation_level_id") or winner.get("reputation_level_id") or "").upper().strip()
    available = _v125_market_num(winner.get("available_quantity"))
    price = _v125_market_num(winner.get("price"))
    original_price = _v125_market_num(winner.get("original_price"))
    deals = winner.get("deal_ids") if isinstance(winner.get("deal_ids"), list) else []
    pressure = 0
    if reputation in {"GREEN", "MERCADO_LIDER"}:
        pressure += 25
    elif reputation:
        pressure += 15
    if fulfillment:
        pressure += 30
    if free_shipping:
        pressure += 20
    if official_store:
        pressure += 15
    if deals:
        pressure += 10
    pressure = min(100, pressure)
    return {
        "catalog_winner_item_id": winner_item_id or None,
        "catalog_winner": bool(candidate_item_id and winner_item_id and candidate_item_id == winner_item_id),
        "winner_seller_id": winner.get("seller_id"),
        "winner_reputation_level": reputation or None,
        "winner_official_store": official_store,
        "winner_free_shipping": free_shipping,
        "winner_fulfillment": fulfillment,
        "winner_logistic_type": logistic or None,
        "winner_available_quantity": int(available) if available is not None and available >= 0 else None,
        "winner_price": price,
        "winner_original_price": original_price,
        "winner_deal_count": len(deals),
        "competition_pressure": pressure,
    }


def _v125_market_rescore(item):
    base = _v125_market_num(item.get("opportunity_score"))
    if base is None:
        return None
    position = _v125_market_num(item.get("best_seller_position"))
    if position is not None and 1 <= position <= 20:
        base += 8.0 * (21.0 - position) / 20.0
    if item.get("catalog_winner"):
        base += 3.0
    return round(min(100.0, max(0.0, base)), 2)


_original_market_enrich = _v119_enrich_ml


def _v125_market_enrich(items):
    global _V125_MARKET_STATS
    _V125_MARKET_STATS = {key: 0 for key in _V125_MARKET_STATS}
    enriched = _original_market_enrich(items)
    try:
        token = _v9_valid_meli_token()
    except Exception:
        token = None
    pending = []
    seen = set()
    products = {}
    for item in enriched:
        if not isinstance(item, dict):
            continue
        pid = str(item.get("catalog_product_id") or item.get("product_id") or "").upper().strip()
        if not pid or not token or pid in seen:
            continue
        seen.add(pid)
        product = _v111_product(pid, token)
        if isinstance(product, dict):
            products[pid] = product
        pending.append(pid)
    highlights = {}
    if pending and token:
        with ThreadPoolExecutor(max_workers=min(_V125_MARKET_MAX_WORKERS, len(pending))) as pool:
            futures = {pool.submit(_v125_market_highlight, pid, token): pid for pid in pending}
            for future in as_completed(futures):
                pid = futures[future]
                try:
                    position, data = future.result()
                except Exception:
                    position, data = None, None
                highlights[pid] = (position, data)
    for item in enriched:
        if not isinstance(item, dict):
            continue
        pid = str(item.get("catalog_product_id") or item.get("product_id") or "").upper().strip()
        product = products.get(pid)
        if not product:
            continue
        position, highlight = highlights.get(pid, (None, None))
        if position is not None:
            try:
                item["best_seller_position"] = int(position)
            except Exception:
                item["best_seller_position"] = None
            if isinstance(highlight, dict):
                item["best_seller_dimension"] = highlight.get("dimension")
                item["best_seller_label"] = highlight.get("label")
            item["best_seller"] = True
        else:
            item["best_seller_position"] = None
            item["best_seller_dimension"] = None
            item["best_seller_label"] = None
            item["best_seller"] = False
        item.update(_v125_market_winner_signals(product, item))
        item["market_signal_version"] = "V12.5"
        item["opportunity_score"] = _v125_market_rescore(item)
    print(
        "[V12.5] sinais de mercado: "
        f"highlights_requests={_V125_MARKET_STATS['highlight_requests']} "
        f"ok={_V125_MARKET_STATS['highlight_ok']} "
        f"not_ranked={_V125_MARKET_STATS['highlight_404']} "
        f"errors={_V125_MARKET_STATS['highlight_errors']} workers={_V125_MARKET_MAX_WORKERS}",
        flush=True,
    )
    return enriched


_v119_enrich_ml = _v125_market_enrich
print("[V12.5] sinais de mercado isolados ativos | sem colisão com fallbacks de vendas", flush=True)
