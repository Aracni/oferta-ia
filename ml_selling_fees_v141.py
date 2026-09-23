"""OFERTA IA V14.1 — tarifa oficial de venda do Mercado Livre.

Usa /sites/MLB/listing_prices como fonte oficial de custo de venda.
Não chama isso de comissão de afiliado: são tarifas do vendedor.
Cacheia consultas para não degradar o garimpo.
"""
import time
import urllib.parse
import requests

_V141_FEE_CACHE = {}
_V141_FEE_TTL = 900
_V141_FEE_TIMEOUT = 2.5


def _v141_num(v):
    try:
        return float(v) if v not in (None, "") else None
    except Exception:
        return None


def _v141_token():
    try:
        return _v9_valid_meli_token()
    except Exception:
        return None


def _v141_get(key):
    entry = _V141_FEE_CACHE.get(key)
    if not entry:
        return None
    if time.time() - entry[0] > _V141_FEE_TTL:
        _V141_FEE_CACHE.pop(key, None)
        return None
    return entry[1]


def _v141_quote(price, category_id=None, listing_type_id=None, token=None):
    if not token or price is None:
        return None
    category_id = str(category_id or "").strip().upper()
    listing_type_id = str(listing_type_id or "").strip()
    if not category_id or not listing_type_id:
        return None
    key = f"{price:.2f}|{category_id}|{listing_type_id}"
    cached = _v141_get(key)
    if cached is not None:
        return cached
    params = {
        "price": f"{price:.2f}",
        "category_id": category_id,
        "listing_type_id": listing_type_id,
    }
    url = "https://api.mercadolibre.com/sites/MLB/listing_prices?" + urllib.parse.urlencode(params)
    try:
        r = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json", "User-Agent": "OFERTA-IA/14.1"},
            timeout=_V141_FEE_TIMEOUT,
        )
        data = r.json() if r.content else None
        if not (200 <= int(r.status_code or 0) < 300):
            _V141_FEE_CACHE[key] = (time.time(), None)
            return None
        rows = data if isinstance(data, list) else [data]
        row = next((x for x in rows if isinstance(x, dict) and str(x.get("listing_type_id") or "") == listing_type_id), None)
        if not isinstance(row, dict):
            _V141_FEE_CACHE[key] = (time.time(), None)
            return None
        details = row.get("sale_fee_details") if isinstance(row.get("sale_fee_details"), dict) else {}
        result = {
            "rate": _v141_num(details.get("percentage_fee")),
            "amount": _v141_num(row.get("sale_fee_amount")),
            "fixed_fee": _v141_num(details.get("fixed_fee")),
            "listing_type_id": row.get("listing_type_id"),
            "listing_type_name": row.get("listing_type_name"),
            "source": "Mercado Livre /listing_prices",
        }
        _V141_FEE_CACHE[key] = (time.time(), result)
        return result
    except Exception as exc:
        _V141_FEE_CACHE[key] = (time.time(), None)
        print(f"[V14.1] tarifa ML indisponível: {type(exc).__name__}", flush=True)
        return None


def _v141_enrich(items):
    previous = globals().get("_v119_enrich_ml")
    base = list(previous(items) if callable(previous) else items or [])
    token = _v141_token()
    applied = 0
    for item in base:
        if not isinstance(item, dict) or str(item.get("marketplace") or "").lower() != "mercadolivre":
            continue
        price = _v141_num(item.get("current_price"))
        category = item.get("category_id") or item.get("category")
        listing = item.get("listing_type_id") or item.get("listing_type")
        quote = _v141_quote(price, category, listing, token)
        if not quote:
            continue
        if quote.get("rate") is not None:
            item["meli_selling_fee_rate"] = quote["rate"]
        if quote.get("amount") is not None:
            item["meli_selling_fee_amount"] = quote["amount"]
        if quote.get("fixed_fee") is not None:
            item["meli_selling_fixed_fee"] = quote["fixed_fee"]
        item["meli_selling_fee_source"] = quote["source"]
        item["meli_listing_type_name"] = quote.get("listing_type_name")
        applied += 1
    print(f"[V14.1] tarifas oficiais aplicadas={applied}/{len(base)}", flush=True)
    return base


_v119_enrich_ml = _v141_enrich
print("[V14.1] tarifa oficial ML /listing_prices ativa; não confundir com comissão de afiliado", flush=True)
