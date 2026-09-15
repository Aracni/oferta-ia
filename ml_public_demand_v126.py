"""OFERTA IA V12.6 — recuperação de vendas via itens de catálogo, com fallback seguro.

Usa primeiro o endpoint de itens do catálogo, que já está respondendo 200 no OFERTA IA.
Só aceita sold_quantity explicitamente retornado pela API. Nunca inventa vendas.
A busca /sites/MLB/search fica como fallback e não repete chamadas 403.
"""
import math
import re
import urllib.parse
import requests

_V126_PUBLIC_STATS = {"requests": 0, "found": 0, "errors": 0, "matched": 0, "catalog_ok": 0, "unauth_ok": 0, "token_ok": 0, "status_403": 0, "status_other": 0}


def _v126_item_id(obj):
    if not isinstance(obj, dict):
        return None
    for key in ("item_id", "meli_item_id", "id", "product_id"):
        value = str(obj.get(key) or "").upper().strip()
        match = re.search(r"\bMLB(\d{6,})\b", value)
        if match:
            return "MLB" + match.group(1)
    for key in ("url", "permalink", "link"):
        value = str(obj.get(key) or "")
        match = re.search(r"\bMLB(\d{6,})\b", value.upper())
        if match:
            return "MLB" + match.group(1)
    return None


def _v126_catalog_id(obj):
    if not isinstance(obj, dict):
        return None
    for key in ("catalog_product_id", "product_id", "user_product_id"):
        value = str(obj.get(key) or "").upper().strip()
        match = re.search(r"\bMLB(\d{6,})\b", value)
        if match:
            return "MLB" + match.group(1)
    for key in ("url", "permalink", "link"):
        value = str(obj.get(key) or "")
        match = re.search(r"/p/(MLB\d{6,})", value.upper())
        if match:
            return match.group(1)
    return None


def _v126_norm_title(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _v126_status_record(status):
    try:
        status = int(status or 0)
    except Exception:
        status = 0
    if status == 403:
        _V126_PUBLIC_STATS["status_403"] += 1
    elif status and not (200 <= status < 300):
        _V126_PUBLIC_STATS["status_other"] += 1


def _v126_catalog_items(catalog_id, token):
    """Endpoint que já foi observado como HTTP 200 no próprio OFERTA IA."""
    if not catalog_id or not token:
        return []
    url = f"https://api.mercadolibre.com/products/{catalog_id}/items"
    try:
        data, status = _v11_fetch_json(token, url, timeout=6, stage="CATALOG_ITEMS_V12_6")
        status = int(status or 0)
        if isinstance(data, dict) and 200 <= status < 300:
            _V126_PUBLIC_STATS["catalog_ok"] += 1
            return list(data.get("results") or [])
        _v126_status_record(status)
    except Exception as exc:
        print(f"[V12.6][CATALOG_ITEMS] falha={type(exc).__name__}", flush=True)
    return []


def _v126_public_search(title):
    """Fallback público sem token; uma única tentativa, sem retry de 403."""
    _V126_PUBLIC_STATS["requests"] += 1
    query = urllib.parse.urlencode({"q": str(title or "")[:180], "limit": 50})
    url = f"https://api.mercadolibre.com/sites/MLB/search?{query}"
    try:
        response = requests.get(url, headers={"Accept": "application/json", "User-Agent": "OFERTA-IA/12.6"}, timeout=4)
        status = int(response.status_code or 0)
        if response.ok:
            data = response.json()
            if isinstance(data, dict):
                _V126_PUBLIC_STATS["unauth_ok"] += 1
                return list(data.get("results") or [])
        _v126_status_record(status)
    except Exception as exc:
        print(f"[V12.6][PUBLIC_SEARCH] falha={type(exc).__name__}", flush=True)
    _V126_PUBLIC_STATS["errors"] += 1
    return []


_V126_PREVIOUS_ENRICH = globals().get("_v119_enrich_ml")


def _v126_enrich(items):
    enriched = list(_V126_PREVIOUS_ENRICH(items) if callable(_V126_PREVIOUS_ENRICH) else items or [])
    token = None
    try:
        ensure = getattr(app, "_meli_auto_ensure", None)
        if callable(ensure):
            ensure(False)
        token = _v9_valid_meli_token()
    except Exception:
        token = None

    for item in enriched:
        if not isinstance(item, dict) or item.get("sold_quantity") is not None:
            continue
        title = item.get("title") or item.get("name") or item.get("product_name")
        item_id = _v126_item_id(item)
        catalog_id = _v126_catalog_id(item)
        chosen = None

        # Caminho principal: o log desta execução mostrou que este endpoint retorna 200.
        if catalog_id and token:
            rows = _v126_catalog_items(catalog_id, token)
            if rows:
                if item_id:
                    chosen = next((row for row in rows if _v126_item_id(row) == item_id), None)
                if chosen is None:
                    chosen = next((row for row in rows if row.get("sold_quantity") is not None), None)
                if chosen is not None:
                    _V126_PUBLIC_STATS["matched"] += 1

        # Fallback: busca pública somente se o catálogo não trouxe sold_quantity.
        if chosen is None and title:
            results = _v126_public_search(title)
            if results:
                if item_id:
                    chosen = next((row for row in results if _v126_item_id(row) == item_id), None)
                if chosen is None and catalog_id:
                    chosen = next((row for row in results if _v126_catalog_id(row) == catalog_id), None)
                if chosen is None:
                    wanted = _v126_norm_title(title)
                    chosen = next((row for row in results if wanted and _v126_norm_title(row.get("title")) == wanted), None)
                if chosen is not None:
                    _V126_PUBLIC_STATS["matched"] += 1

        if not isinstance(chosen, dict):
            continue
        sold = chosen.get("sold_quantity")
        try:
            sold = int(float(sold)) if sold is not None else None
        except Exception:
            sold = None
        if sold is None or sold < 0:
            continue

        item["sold_quantity"] = sold
        item["sales"] = sold
        item["sales_count"] = sold
        item["sales_source"] = "catalog_items" if catalog_id else "public_search"
        item["demand_source"] = item["sales_source"]
        item["demand_index"] = round(min(100.0, math.log1p(sold) / math.log1p(10000) * 100.0), 2)
        item["confidence"] = "alta" if sold > 0 else item.get("confidence") or "média"
        try:
            resc = globals().get("_v115_rescore")
            if callable(resc):
                item["opportunity_score"] = resc(item)
        except Exception:
            pass
        item["score_provisional"] = False if item.get("rating") is not None else True
        item["enrichment_version"] = "V12.6-catalog-sales"
        _V126_PUBLIC_STATS["found"] += 1

    print(
        "[V12.6] vendas/demanda: "
        f"requests={_V126_PUBLIC_STATS['requests']} catalog_ok={_V126_PUBLIC_STATS['catalog_ok']} "
        f"matched={_V126_PUBLIC_STATS['matched']} found={_V126_PUBLIC_STATS['found']} "
        f"errors={_V126_PUBLIC_STATS['errors']} public_ok={_V126_PUBLIC_STATS['unauth_ok']} "
        f"403={_V126_PUBLIC_STATS['status_403']} other={_V126_PUBLIC_STATS['status_other']}",
        flush=True,
    )
    return enriched


_v119_enrich_ml = _v126_enrich
print("[V12.6] vendas: prioriza products/{catalog}/items | fallback público sem retry 403")
