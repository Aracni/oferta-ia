"""OFERTA IA V12.5 — vendas diretas pelo item MLB.

O enriquecimento anterior prioriza catalog_product_id. Muitos candidatos do
Mercado Livre são anúncios comuns e chegam sem esse vínculo. Este patch usa o
item_id MLB já presente no candidato (ou na URL) como fonte primária de vendas.
Ausência continua sendo None; zero só é aceito quando a API realmente devolve
sold_quantity=0.
"""
import re
import math

_V125_DIRECT_STATS = {"requests": 0, "found": 0, "zero": 0, "errors": 0}


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
    if not item_id or not token:
        return None, None, None
    try:
        data, status = _v11_fetch_json(
            token,
            f"https://api.mercadolibre.com/items/{item_id}",
            timeout=7,
            stage="ENRICH_V12_5_DIRECT_ITEM",
        )
        _V125_DIRECT_STATS["requests"] += 1
        status = int(status or 0)
        if isinstance(data, dict) and 200 <= status < 300:
            value = data.get("sold_quantity")
            try:
                if value not in (None, ""):
                    sold = int(float(value))
                    if sold >= 0:
                        return sold, item_id, "items/{id}"
            except Exception:
                pass
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
        item["opportunity_score"] = _v125_rescore(item) if callable(globals().get("_v125_rescore")) else item.get("opportunity_score")
        item["enrichment_version"] = "V12.5-direct-item"
    print(
        "[V12.5] vendas diretas por ITEM: "
        f"requests={_V125_DIRECT_STATS['requests']} "
        f"found={_V125_DIRECT_STATS['found']} "
        f"zero_real={_V125_DIRECT_STATS['zero']} "
        f"errors={_V125_DIRECT_STATS['errors']}",
        flush=True,
    )
    return enriched


_v119_enrich_ml = _v125_direct_enrich
print("[V12.5] fallback direto por item MLB ativo | vendas reais sem catálogo", flush=True)
