"""OFERTA IA V12.6 — demanda pública do Mercado Livre, sem inventar vendas.

Prioriza a busca autenticada com o access token já renovado pelo meli_auto.
Se a API aceitar sem token, usa o fallback público. Nunca transforma ausência
de sold_quantity em zero.
"""
import math
import re
import urllib.parse
import requests

_V126_PUBLIC_STATS = {"requests": 0, "found": 0, "errors": 0, "matched": 0, "unauth_ok": 0, "token_ok": 0, "status_403": 0, "status_other": 0}


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


def _v126_public_search(title, token):
    """Retorna resultados de busca; autenticada primeiro, pública depois."""
    _V126_PUBLIC_STATS["requests"] += 1
    query = urllib.parse.urlencode({"q": str(title or "")[:180], "limit": 50})
    url = f"https://api.mercadolibre.com/sites/MLB/search?{query}"

    # 1) Primeiro tenta com o access token já validado/renovado.
    if token:
        try:
            data, status = _v11_fetch_json(token, url, timeout=6, stage="PUBLIC_DEMAND_V12_6_AUTH")
            status = int(status or 0)
            if isinstance(data, dict) and 200 <= status < 300:
                _V126_PUBLIC_STATS["token_ok"] += 1
                return list(data.get("results") or [])
            _v126_status_record(status)
        except Exception as exc:
            print(f"[V12.6][PUBLIC_SEARCH][AUTH] falha={type(exc).__name__}", flush=True)

    # 2) Fallback sem token: útil quando a busca pública estiver liberada.
    try:
        response = requests.get(
            url,
            headers={"Accept": "application/json", "User-Agent": "OFERTA-IA/12.6"},
            timeout=6,
        )
        status = int(response.status_code or 0)
        if response.ok:
            data = response.json()
            if isinstance(data, dict):
                _V126_PUBLIC_STATS["unauth_ok"] += 1
                return list(data.get("results") or [])
        _v126_status_record(status)
    except Exception as exc:
        print(f"[V12.6][PUBLIC_SEARCH][UNAUTH] falha={type(exc).__name__}", flush=True)

    _V126_PUBLIC_STATS["errors"] += 1
    return []


_V126_PREVIOUS_ENRICH = globals().get("_v119_enrich_ml")


def _v126_enrich(items):
    enriched = list(_V126_PREVIOUS_ENRICH(items) if callable(_V126_PREVIOUS_ENRICH) else items or [])

    # Garante que o access token possa ser renovado antes da busca pública.
    token = None
    try:
        ensure = getattr(app, "_meli_auto_ensure", None)
        if callable(ensure):
            ok, reason = ensure(False)
            if not ok:
                print(f"[V12.6][AUTH] conexão indisponível: {reason}", flush=True)
        token = _v9_valid_meli_token()
    except Exception:
        token = None

    for item in enriched:
        if not isinstance(item, dict):
            continue
        if item.get("sold_quantity") is not None:
            continue

        title = item.get("title") or item.get("name") or item.get("product_name")
        if not title:
            continue
        item_id = _v126_item_id(item)
        catalog_id = _v126_catalog_id(item)
        results = _v126_public_search(title, token)
        if not results:
            continue

        chosen = None
        if item_id:
            for row in results:
                if _v126_item_id(row) == item_id:
                    chosen = row
                    break
        if chosen is None and catalog_id:
            for row in results:
                row_catalog = _v126_catalog_id(row)
                if row_catalog and row_catalog == catalog_id:
                    chosen = row
                    break
        if chosen is None:
            wanted = _v126_norm_title(title)
            if wanted:
                for row in results:
                    if _v126_norm_title(row.get("title")) == wanted:
                        chosen = row
                        break
        if chosen is None:
            continue

        _V126_PUBLIC_STATS["matched"] += 1
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
        item["sales_source"] = "public_search"
        item["demand_source"] = "public_search"
        item["demand_index"] = round(min(100.0, math.log1p(sold) / math.log1p(10000) * 100.0), 2)
        item["confidence"] = "alta" if sold > 0 else item.get("confidence") or "média"
        try:
            resc = globals().get("_v115_rescore")
            if callable(resc):
                item["opportunity_score"] = resc(item)
        except Exception:
            pass
        item["score_provisional"] = False if item.get("rating") is not None else True
        item["enrichment_version"] = "V12.6-public-demand"
        _V126_PUBLIC_STATS["found"] += 1

    print(
        "[V12.6] demanda pública: "
        f"requests={_V126_PUBLIC_STATS['requests']} "
        f"matched={_V126_PUBLIC_STATS['matched']} "
        f"found={_V126_PUBLIC_STATS['found']} "
        f"errors={_V126_PUBLIC_STATS['errors']} "
        f"auth_ok={_V126_PUBLIC_STATS['token_ok']} "
        f"public_ok={_V126_PUBLIC_STATS['unauth_ok']} "
        f"403={_V126_PUBLIC_STATS['status_403']} "
        f"other={_V126_PUBLIC_STATS['status_other']}",
        flush=True,
    )
    return enriched


_v119_enrich_ml = _v126_enrich
print("[V12.6] sinal público de demanda ativo | auth primeiro + fallback público | diagnóstico HTTP")
