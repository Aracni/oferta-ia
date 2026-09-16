"""OFERTA IA V12.6 — recuperação de vendas via produto de catálogo.

Tenta primeiro a leitura pública do produto de catálogo/PDP. Quando o endpoint
exige autorização, tenta a sessão OAuth existente. Só aceita sold_quantity
explicitamente retornado pela API. Nunca inventa vendas.
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


def _v126_public_get(url, stage):
    """GET sem Authorization: útil para recursos realmente públicos."""
    _V126_PUBLIC_STATS["requests"] += 1
    try:
        response = requests.get(
            url,
            headers={"Accept": "application/json", "User-Agent": "OFERTA-IA/12.6"},
            timeout=6,
        )
        status = int(response.status_code or 0)
        _v126_status_record(status)
        if response.ok:
            data = response.json()
            if isinstance(data, dict):
                _V126_PUBLIC_STATS["unauth_ok"] += 1
                return data, status
        return None, status
    except Exception as exc:
        print(f"[V12.6][{stage}] falha={type(exc).__name__}", flush=True)
        _V126_PUBLIC_STATS["errors"] += 1
        return None, None


def _v126_catalog_product(catalog_id, token):
    """Detalhe da PDP: primeiro sem token; depois com OAuth."""
    if not catalog_id:
        return None
    url = f"https://api.mercadolibre.com/products/{catalog_id}"

    # Primeiro, não envia credencial. Se a PDP for pública, aproveitamos.
    data, status = _v126_public_get(url, "CATALOG_PRODUCT_PUBLIC")
    if isinstance(data, dict) and data.get("sold_quantity") is not None:
        _V126_PUBLIC_STATS["catalog_ok"] += 1
        return data

    # Se o recurso exigir autorização, usa a conexão OAuth do OFERTA IA.
    if not token:
        return None
    try:
        data, status = _v11_fetch_json(token, url, timeout=6, stage="CATALOG_PRODUCT_V12_6")
        status = int(status or 0)
        if isinstance(data, dict) and 200 <= status < 300:
            _V126_PUBLIC_STATS["catalog_ok"] += 1
            _V126_PUBLIC_STATS["token_ok"] += 1
            if data.get("sold_quantity") is not None:
                return data
        _v126_status_record(status)
    except Exception as exc:
        print(f"[V12.6][CATALOG_PRODUCT_AUTH] falha={type(exc).__name__}", flush=True)
    return None


def _v126_catalog_items(catalog_id, token):
    """Lista da PDP; primeiro pública, depois autenticada."""
    if not catalog_id:
        return []
    url = f"https://api.mercadolibre.com/products/{catalog_id}/items"

    data, status = _v126_public_get(url, "CATALOG_ITEMS_PUBLIC")
    if isinstance(data, dict):
        rows = list(data.get("results") or [])
        if rows:
            _V126_PUBLIC_STATS["catalog_ok"] += 1
            return rows

    if not token:
        return []
    try:
        data, status = _v11_fetch_json(token, url, timeout=6, stage="CATALOG_ITEMS_V12_6")
        status = int(status or 0)
        if isinstance(data, dict) and 200 <= status < 300:
            _V126_PUBLIC_STATS["catalog_ok"] += 1
            _V126_PUBLIC_STATS["token_ok"] += 1
            return list(data.get("results") or [])
        _v126_status_record(status)
    except Exception as exc:
        print(f"[V12.6][CATALOG_ITEMS_AUTH] falha={type(exc).__name__}", flush=True)
    return []


def _v126_public_search(title):
    """Fallback público de busca; uma única tentativa, sem retry de 403."""
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

        if catalog_id:
            chosen = _v126_catalog_product(catalog_id, token)

        if chosen is None and catalog_id:
            rows = _v126_catalog_items(catalog_id, token)
            if rows:
                if item_id:
                    row = next((r for r in rows if _v126_item_id(r) == item_id and r.get("sold_quantity") is not None), None)
                    if row is not None:
                        chosen = row
                if chosen is None:
                    chosen = next((r for r in rows if r.get("sold_quantity") is not None), None)
                if chosen is not None:
                    _V126_PUBLIC_STATS["matched"] += 1

        if chosen is None and title:
            results = _v126_public_search(title)
            if results:
                if item_id:
                    chosen = next((row for row in results if _v126_item_id(row) == item_id and row.get("sold_quantity") is not None), None)
                if chosen is None and catalog_id:
                    chosen = next((row for row in results if _v126_catalog_id(row) == catalog_id and row.get("sold_quantity") is not None), None)
                if chosen is None:
                    wanted = _v126_norm_title(title)
                    chosen = next((row for row in results if wanted and _v126_norm_title(row.get("title")) == wanted and row.get("sold_quantity") is not None), None)
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
        item["sales_source"] = "catalog_product" if catalog_id else "public_search"
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
        item["enrichment_version"] = "V12.6-catalog-product-sales"
        _V126_PUBLIC_STATS["found"] += 1

    print(
        "[V12.6] vendas/demanda: "
        f"requests={_V126_PUBLIC_STATS['requests']} catalog_ok={_V126_PUBLIC_STATS['catalog_ok']} "
        f"matched={_V126_PUBLIC_STATS['matched']} found={_V126_PUBLIC_STATS['found']} "
        f"errors={_V126_PUBLIC_STATS['errors']} public_ok={_V126_PUBLIC_STATS['unauth_ok']} "
        f"token_ok={_V126_PUBLIC_STATS['token_ok']} 403={_V126_PUBLIC_STATS['status_403']} other={_V126_PUBLIC_STATS['status_other']}",
        flush=True,
    )
    return enriched


_v119_enrich_ml = _v126_enrich
print("[V12.6] vendas: catálogo público sem token + OAuth quando permitido + fallback seguro", flush=True)
