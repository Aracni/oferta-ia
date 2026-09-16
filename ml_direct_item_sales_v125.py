"""OFERTA IA V12.5 — vendas diretas pelo item MLB.

Prioriza uma leitura pública do anúncio e, se necessário, usa OAuth com
include_attributes=all. Só grava sold_quantity quando o Mercado Livre
realmente devolve o campo; ausência continua como None.
"""
import re
import math
import requests

_V125_DIRECT_STATS = {"requests": 0, "found": 0, "zero": 0, "errors": 0, "public_ok": 0, "auth_ok": 0}


def _v125_extract_item_id(obj):
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


def _v125_direct_sold(item, token):
    item_id = _v125_extract_item_id(item)
    if not item_id:
        return None, None, None

    # 1) Tentativa pública: não depende da sessão OAuth e não expõe credenciais.
    _V125_DIRECT_STATS["requests"] += 1
    try:
        response = requests.get(
            f"https://api.mercadolibre.com/items/{item_id}",
            headers={"Accept": "application/json", "User-Agent": "OFERTA-IA/12.8"},
            timeout=7,
        )
        if response.ok:
            data = response.json() if response.content else None
            _V125_DIRECT_STATS["public_ok"] += 1
            if isinstance(data, dict) and data.get("sold_quantity") is not None:
                try:
                    sold = int(float(data.get("sold_quantity")))
                    if sold >= 0:
                        return sold, item_id, "items/{id}/public"
                except Exception:
                    pass
    except Exception:
        pass

    # 2) OAuth: usa o mesmo token já conectado no OFERTA IA.
    if not token:
        return None, item_id, None
    try:
        data, status = _v11_fetch_json(
            token,
            f"https://api.mercadolibre.com/items/{item_id}?include_attributes=all",
            timeout=7,
            stage="ENRICH_V12_5_DIRECT_ITEM_FULL",
        )
        status = int(status or 0)
        if isinstance(data, dict) and 200 <= status < 300:
            _V125_DIRECT_STATS["auth_ok"] += 1
            value = data.get("sold_quantity")
            if value is not None:
                sold = int(float(value))
                if sold >= 0:
                    return sold, item_id, "items/{id}?include_attributes=all"
        if status >= 400:
            _V125_DIRECT_STATS["errors"] += 1
    except Exception:
        _V125_DIRECT_STATS["errors"] += 1
    return None, item_id, None


_original_v125_direct_enrich = _v119_enrich_ml


def _v125_direct_enrich(items):
    try:
        token = _v9_valid_meli_token()
    except Exception:
        token = None
    enriched = _original_v125_direct_enrich(items)
    for item in enriched:
        if not isinstance(item, dict) or item.get("sold_quantity") is not None:
            continue
        sold, item_id, source = _v125_direct_sold(item, token)
        if sold is None:
            continue
        _V125_DIRECT_STATS["found"] += 1
        if sold == 0:
            _V125_DIRECT_STATS["zero"] += 1
        item["item_id"] = item_id
        item["sold_quantity"] = sold
        item["sales"] = sold
        item["sales_count"] = sold
        item["sales_source"] = source
        item["demand_index"] = round(
            min(100.0, math.log1p(max(0, sold)) / math.log1p(10000) * 100.0), 2
        )
        item["score_provisional"] = item.get("rating") is None
        rescore = globals().get("_v115_rescore")
        if callable(rescore):
            item["opportunity_score"] = rescore(item)
        item["enrichment_version"] = "V12.8-direct-item-public-full"
    print(
        "[V12.8] vendas diretas por ITEM: "
        f"requests={_V125_DIRECT_STATS['requests']} "
        f"found={_V125_DIRECT_STATS['found']} "
        f"zero_real={_V125_DIRECT_STATS['zero']} "
        f"errors={_V125_DIRECT_STATS['errors']} "
        f"public_ok={_V125_DIRECT_STATS['public_ok']} auth_ok={_V125_DIRECT_STATS['auth_ok']}",
        flush=True,
    )
    return enriched


_v119_enrich_ml = _v125_direct_enrich
print("[V12.8] item MLB: público primeiro + OAuth include_attributes=all; vendas somente se reais", flush=True)
