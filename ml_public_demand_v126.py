"""OFERTA IA V12.6 — sinal público de demanda via busca do Mercado Livre."""
import math
import re
import urllib.parse

_V126_PUBLIC_STATS = {"requests": 0, "found": 0, "errors": 0, "matched": 0}


def _v126_item_id(obj):
    if not isinstance(obj, dict):
        return None
    for key in ("item_id", "meli_item_id", "id"):
        value = str(obj.get(key) or "").strip().upper()
        if re.fullmatch(r"MLB[0-9]+", value):
            return value
    for key in ("url", "permalink", "link", "product_url"):
        value = str(obj.get(key) or "")
        match = re.search(r"(MLB[0-9]+)", value, re.I)
        if match:
            return match.group(1).upper()
    return None


def _v126_public_search(title, token):
    if not title or not token:
        return None
    try:
        query = urllib.parse.quote(str(title)[:180])
        url = f"https://api.mercadolibre.com/sites/MLB/search?q={query}&limit=50"
        data, status = _v11_fetch_json(token, url, timeout=7, stage="PUBLIC_DEMAND_V12_6")
        _V126_PUBLIC_STATS["requests"] += 1
        if not isinstance(data, dict) or not (200 <= int(status or 0) < 300):
            _V126_PUBLIC_STATS["errors"] += 1
            return None
        results = data.get("results")
        return results if isinstance(results, list) else None
    except Exception:
        _V126_PUBLIC_STATS["errors"] += 1
        return None


def _v126_enrich(items):
    try:
        token = _v9_valid_meli_token()
    except Exception:
        token = None
    enriched = _v119_enrich_ml(items)
    for item in enriched:
        if not isinstance(item, dict) or item.get("sold_quantity") is not None:
            continue
        item_id = _v126_item_id(item)
        title = str(item.get("title") or item.get("name") or "").strip()
        if not token or not item_id or not title:
            continue
        results = _v126_public_search(title, token)
        if not results:
            continue
        for result in results:
            if not isinstance(result, dict) or _v126_item_id(result) != item_id:
                continue
            _V126_PUBLIC_STATS["matched"] += 1
            value = result.get("sold_quantity")
            try:
                if value in (None, ""):
                    continue
                sold = int(float(value))
                if sold < 0:
                    continue
            except Exception:
                continue
            item["sold_quantity"] = sold
            item["sales"] = sold
            item["sales_count"] = sold
            item["sales_source"] = "public_search"
            item["demand_source"] = "public_search"
            item["demand_index"] = round(min(100.0, math.log1p(sold) / math.log1p(10000) * 100.0), 2)
            item["data_confidence"] = "média" if item.get("rating") is None else "alta"
            item["confidence"] = item["data_confidence"]
            rescore = globals().get("_v115_rescore")
            if callable(rescore):
                item["opportunity_score"] = rescore(item)
            item["enrichment_version"] = "V12.6-public-demand"
            _V126_PUBLIC_STATS["found"] += 1
            break
    print(f"[V12.6] demanda pública: requests={_V126_PUBLIC_STATS['requests']} matched={_V126_PUBLIC_STATS['matched']} found={_V126_PUBLIC_STATS['found']} errors={_V126_PUBLIC_STATS['errors']}", flush=True)
    return enriched


_v119_enrich_ml = _v126_enrich
print("[V12.6] sinal público de demanda ativo | sem inventar vendas", flush=True)
