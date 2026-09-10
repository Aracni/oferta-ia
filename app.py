"""OFERTA IA application loader.

V11.5: resolvedor independente do Mercado Livre + garimpo central sempre
consulta Mercado Livre junto com Shopee e garante diversidade no ranking final.
"""
import re
import time
import threading
import urllib.request

_SOURCE = "https://raw.githubusercontent.com/Aracni/oferta-ia/41a35a18c9a59a737e5bef91ef0cc1f74d3e3525/app.py"

try:
    with urllib.request.urlopen(_SOURCE, timeout=20) as response:
        source = response.read().decode("utf-8")
except Exception as exc:
    raise RuntimeError(f"Não foi possível carregar o núcleo do OFERTA IA: {exc}") from exc

source = source.replace("api.mercadolivre.com", "api.mercadolibre.com")
exec(compile(source, _SOURCE, "exec"), globals(), globals())

# ---------------------------------------------------------------------------
# V11.5 — RESOLVEDOR INDEPENDENTE DE PRODUCT + GARIMPO MULTIMARKETPLACE
# ---------------------------------------------------------------------------
_V11_CORE_LOG = _v93_log
_V11_ORIGINAL_FETCH_JSON = _v9_fetch_json
_V11_ITEM_INDEX = {}
_V11_PRODUCT_INDEX = {}
_V11_CATALOG_CACHE = {}
_V11_CATALOG_TTL = 300
_V11_LOCK = threading.RLock()
_V11_VERSION = "11.5"


def _v11_log(stage, message, trace=None, **kwargs):
    if stage == "VALIDATE" and message == "Candidatos resolvidos":
        try:
            valid = int(kwargs.get("valid") or 0)
            active = int(kwargs.get("active") or 0)
            if valid > active:
                kwargs["active"] = valid
                kwargs["active_source"] = "catalog/PRODUCT"
        except Exception:
            pass
    return _V11_CORE_LOG(stage, message, trace=trace, **kwargs)

_v93_log = _v11_log


def _v11_num(value):
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


def _v11_site_from_id(value):
    m = re.match(r"^(ML[A-Z])", str(value or "").upper())
    return m.group(1) if m else "MLB"


def _v11_rows(payload):
    if not isinstance(payload, dict):
        return []
    for key in ("results", "items", "publications"):
        rows = payload.get(key)
        if isinstance(rows, list):
            return rows
    return []


def _v11_remember_product(product):
    if not isinstance(product, dict):
        return
    pid = product.get("id") or product.get("catalog_product_id")
    if not pid:
        return
    with _V11_LOCK:
        _V11_PRODUCT_INDEX[str(pid)] = dict(product)
        winner = product.get("buy_box_winner")
        if isinstance(winner, dict) and winner.get("item_id"):
            item_id = str(winner["item_id"])
            row = dict(winner)
            row["id"] = item_id
            row["item_id"] = item_id
            row.setdefault("product_id", pid)
            row.setdefault("title", product.get("name") or product.get("family_name") or "")
            row.setdefault("permalink", product.get("permalink") or "")
            _V11_ITEM_INDEX[item_id] = row


def _v11_remember_items(product_id, payload):
    rows = _v11_rows(payload)
    if not rows:
        return
    with _V11_LOCK:
        product = dict(_V11_PRODUCT_INDEX.get(str(product_id), {}))
    for row in rows:
        if not isinstance(row, dict):
            continue
        item_id = row.get("item_id") or row.get("id")
        if not item_id:
            continue
        item_id = str(item_id)
        normalized = dict(row)
        normalized["id"] = item_id
        normalized["item_id"] = item_id
        normalized.setdefault("product_id", product_id)
        normalized.setdefault("title", product.get("name") or product.get("family_name") or "")
        normalized.setdefault("permalink", product.get("permalink") or "")
        if normalized.get("price") is None:
            normalized["price"] = _v11_num(normalized.get("current_price"))
        with _V11_LOCK:
            _V11_ITEM_INDEX[item_id] = normalized


def _v11_best_catalog_row(product_id, payload):
    rows = _v11_rows(payload)
    if not rows:
        return None
    with _V11_LOCK:
        product = dict(_V11_PRODUCT_INDEX.get(str(product_id), {}))
    best = None
    best_price = None
    for row in rows:
        if not isinstance(row, dict):
            continue
        iid = row.get("item_id") or row.get("id")
        price = _v11_num(row.get("price") or row.get("current_price"))
        title = row.get("title") or product.get("name") or product.get("family_name") or ""
        if not iid or price is None or price <= 0:
            continue
        try:
            if _looks_like_accessory(title):
                continue
        except Exception:
            pass
        status = str(row.get("status") or "active").lower()
        if status not in {"active", ""}:
            continue
        if best is None or best_price is None or price < best_price:
            best = dict(row)
            best_price = price
    return best


def _v11_normalize_offer(product_id, detail, offer, rank_position=None, query=""):
    if not isinstance(offer, dict):
        return None
    iid = offer.get("item_id") or offer.get("id")
    price = _v11_num(offer.get("price") or offer.get("current_price"))
    if not iid or price is None or price <= 0:
        return None
    title = offer.get("title") or (detail or {}).get("name") or (detail or {}).get("family_name") or "Produto Mercado Livre"
    if _looks_like_accessory(title):
        return None
    status = str(offer.get("status") or "active").lower()
    if status not in {"active", ""}:
        return None
    old = _v11_num(offer.get("original_price"))
    image = offer.get("secure_thumbnail") or offer.get("thumbnail")
    if not image and isinstance(detail, dict):
        pics = detail.get("pictures") or []
        if pics and isinstance(pics[0], dict):
            image = pics[0].get("secure_url") or pics[0].get("url")
    url = offer.get("permalink") or (detail or {}).get("permalink")
    if not isinstance(url, str) or not url.startswith("http"):
        url = f"https://www.mercadolivre.com.br/p/{product_id}"
    seller = offer.get("seller") if isinstance(offer.get("seller"), dict) else {}
    p = {
        "item_id": str(iid),
        "name": title,
        "url": url,
        "current_price": price,
        "old_price": old,
        "discount_rate": round((old - price) / old * 100, 2) if old and old > price else None,
        "category": (detail or {}).get("domain_id") or (detail or {}).get("category_id"),
        "image_url": image,
        "seller_id": offer.get("seller_id") or seller.get("id"),
        "store": str(seller.get("nickname") or offer.get("seller_nickname") or "Mercado Livre"),
        "marketplace": "mercadolivre",
        "catalog_product_id": str(product_id),
        "product_id": str(product_id),
        "rating": offer.get("rating"),
        "condition": offer.get("condition") or offer.get("item_condition") or "new",
        "rank_position": rank_position,
        "discovery_query": query,
        "data_confidence": "alta",
    }
    return p


def _v11_catalog_to_item(token, product_id, rank_position=None, query=""):
    pid = str(product_id or "").upper()
    if not pid:
        return None

    detail, status = _v11_fetch_json(token, f"https://api.mercadolibre.com/products/{pid}", timeout=10)
    if not isinstance(detail, dict) or not (status and 200 <= int(status) < 300):
        _v93_log("CATALOG_V11", "PRODUCT sem detalhe utilizável", product_id=pid, http=status)
        return None

    winner = detail.get("buy_box_winner")
    if isinstance(winner, dict):
        p = _v11_normalize_offer(pid, detail, winner, rank_position, query)
        if p:
            p["highlight_type"] = "PRODUCT"
            _v11_log("CATALOG_V11", "PRODUCT resolvido pelo buy_box_winner", product_id=pid, item_id=p["item_id"], price=p["current_price"])
            return p

    items_data, items_status = _v11_fetch_json(
        token,
        f"https://api.mercadolibre.com/products/{pid}/items",
        {"limit": 50},
        timeout=10,
    )
    if not (items_status and 200 <= int(items_status) < 300):
        _v93_log("CATALOG_V11", "Lista de ofertas indisponível", product_id=pid, http=items_status)
        return None

    _v11_remember_items(pid, items_data)
    best = _v11_best_catalog_row(pid, items_data)
    if not best:
        _v93_log("CATALOG_V11", "PRODUCT sem oferta válida no catálogo", product_id=pid, rows=len(_v11_rows(items_data)))
        return None

    p = _v11_normalize_offer(pid, detail, best, rank_position, query)
    if p:
        p["highlight_type"] = "PRODUCT"
        _v93_log("CATALOG_V11", "PRODUCT resolvido por oferta do catálogo", product_id=pid, item_id=p["item_id"], price=p["current_price"])
    return p

_v9_catalog_to_item = _v11_catalog_to_item


def _v11_enrich_product_payload(pid, data, token, trace=None):
    if not isinstance(data, dict):
        return data
    winner = data.get("buy_box_winner")
    winner_price = _v11_num(winner.get("price")) if isinstance(winner, dict) else None
    winner_id = winner.get("item_id") if isinstance(winner, dict) else None
    price_range = data.get("buy_box_winner_price_range")
    if isinstance(winner, dict) and winner_id and winner_price is None and isinstance(price_range, dict):
        minimum = price_range.get("min")
        minimum_price = minimum.get("price") if isinstance(minimum, dict) else minimum
        minimum_price = _v11_num(minimum_price)
        if minimum_price is not None and minimum_price > 0:
            enriched = dict(data)
            ew = dict(winner)
            ew["price"] = minimum_price
            enriched["buy_box_winner"] = ew
            return enriched
    if winner_id and winner_price is not None:
        return data
    try:
        items_data, items_status = _V11_ORIGINAL_FETCH_JSON(
            token, f"https://api.mercadolibre.com/products/{pid}/items", {"limit": 50}, 12, trace, "CATALOG"
        )
        if items_status and 200 <= int(items_status) < 300:
            _v11_remember_items(pid, items_data)
            best = _v11_best_catalog_row(pid, items_data)
            if best:
                enriched = dict(data)
                enriched["buy_box_winner"] = best
                return enriched
    except Exception as exc:
        _v93_log("CATALOG_V11", "Falha ao enriquecer produto sem winner utilizável", trace=trace, product_id=pid, error=str(exc)[:180])
    return data


def _v11_synthetic_item(item_id):
    with _V11_LOCK:
        row = dict(_V11_ITEM_INDEX.get(str(item_id), {}))
    if not row:
        return None
    price = _v11_num(row.get("price") or row.get("current_price"))
    original = _v11_num(row.get("original_price"))
    title = row.get("title") or row.get("name") or ""
    site_id = row.get("site_id") or _v11_site_from_id(item_id)
    permalink = row.get("permalink")
    if not isinstance(permalink, str) or not permalink.startswith("http"):
        permalink = f"https://produto.mercadolivre.com.br/{item_id}"
    seller = row.get("seller") if isinstance(row.get("seller"), dict) else {}
    return {
        "id": str(item_id), "item_id": str(item_id), "site_id": site_id,
        "title": title, "name": title,
        "seller_id": row.get("seller_id") or seller.get("id"),
        "category_id": row.get("category_id"),
        "price": price, "base_price": price, "current_price": price,
        "original_price": original, "currency_id": row.get("currency_id") or "BRL",
        "available_quantity": row.get("available_quantity") or 1,
        "initial_quantity": row.get("initial_quantity") or row.get("available_quantity") or 1,
        "sold_quantity": row.get("sold_quantity") or 0,
        "permalink": permalink, "thumbnail": row.get("thumbnail") or row.get("secure_thumbnail"),
        "catalog_product_id": row.get("product_id"), "product_id": row.get("product_id"),
        "status": row.get("status") or "active", "active": True,
        "condition": row.get("condition") or row.get("item_condition") or "new",
        "buying_mode": row.get("buying_mode") or "buy_it_now",
        "listing_type_id": row.get("listing_type_id") or "gold_special",
        "listing_type": row.get("listing_type") or row.get("listing_type_id") or "gold_special",
        "accepts_mercadopago": True, "shipping": row.get("shipping") or {},
    }


def _v11_public_search(token, item_id, trace=None):
    try:
        site = _v11_site_from_id(item_id)
        response = requests.get(
            f"https://api.mercadolibre.com/sites/{site}/search",
            params={"q": str(item_id), "limit": 10},
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json", "User-Agent": "OFERTA-IA/11.5"},
            timeout=5,
        )
        data = response.json() if response.content else {}
        for candidate in (data or {}).get("results", []) if isinstance(data, dict) else []:
            if str(candidate.get("id")) == str(item_id):
                return candidate, response.status_code
    except Exception as exc:
        _v93_log("ERROR", "Fallback público do ITEM falhou", trace=trace, error=str(exc)[:220])
    return None, None


def _v11_fetch_json(token, url, params=None, timeout=10, trace=None, stage="HTTP"):
    url_text = str(url or "")
    lower_url = url_text.lower()
    item_match = re.search(r"/items/(ML[A-Z][0-9]+)(?:/|$)", url_text, re.I)
    if item_match and "/products/" not in lower_url:
        item_id = item_match.group(1).upper()
        with _V11_LOCK:
            cached = _V11_ITEM_INDEX.get(item_id)
        if cached:
            return _v11_synthetic_item(item_id), 200
        if url_text.rstrip("/").lower().endswith("/items/" + item_id.lower()):
            data, status = _v11_public_search(token, item_id, trace=trace)
            if data is not None:
                with _V11_LOCK:
                    _V11_ITEM_INDEX[item_id] = dict(data)
                _v93_log("CATALOG_V11", "ITEM recuperado por busca pública; /items/{id} bloqueado", trace=trace, item_id=item_id, http=status or 200)
                return data, status or 200
        _v93_log("CATALOG_V11", "ITEM sem dados no índice; requisição /items/{id} bloqueada", trace=trace, item_id=item_id, http=403)
        return {"id": item_id, "status": "unavailable", "active": False}, 403

    is_catalog = "/products/" in lower_url
    if not is_catalog:
        return _V11_ORIGINAL_FETCH_JSON(token, url, params, timeout, trace, stage)

    safe_params = dict(params or {})
    key = (url_text, tuple(sorted((str(k), str(v)) for k, v in safe_params.items())))
    now = time.time()
    with _V11_LOCK:
        cached = _V11_CATALOG_CACHE.get(key)
    if cached and now - cached[0] <= _V11_CATALOG_TTL:
        return cached[1], cached[2]

    data, status = _V11_ORIGINAL_FETCH_JSON(token, url, safe_params, timeout, trace, stage)
    if data is not None and isinstance(status, int) and 200 <= status < 300:
        m = re.search(r"/products/(ML[A-Z][0-9]+)(?:/|$)", url_text, re.I)
        pid = m.group(1).upper() if m else None
        if pid and not url_text.rstrip("/").lower().endswith("/items"):
            data = _v11_enrich_product_payload(pid, data, token, trace=trace)
        with _V11_LOCK:
            _V11_CATALOG_CACHE[key] = (time.time(), data, status)
        if pid:
            if url_text.rstrip("/").lower().endswith("/items"):
                _v11_remember_items(pid, data)
            else:
                _v11_remember_product(data)
    return data, status

_v9_fetch_json = _v11_fetch_json

try:
    if "_meli_get" in globals():
        def _v11_meli_get(token, url, params=None, timeout=10):
            return _v11_fetch_json(token, url, params, timeout)
        _meli_get = _v11_meli_get
except Exception:
    pass

# ---------------------------------------------------------------------------
# O garimpo central antigo usava modo rápido por padrão. Isso fazia a UI
# consultar somente Shopee. V11.5 torna o modo completo explícito na própria
# interface e, adicionalmente, força include_meli=true no endpoint central.
# ---------------------------------------------------------------------------
_V11_ORIGINAL_OPPORTUNITIES_CENTRAL = opportunities_central


def _v11_marketplace_mix(items, limit):
    items = list(items or [])
    if not items:
        return []
    limit = max(1, int(limit or 10))
    ml = [x for x in items if str(x.get("marketplace") or "").lower() == "mercadolivre"]
    sh = [x for x in items if str(x.get("marketplace") or "").lower() == "shopee"]
    other = [x for x in items if x not in ml and x not in sh]
    ranked = sorted(items, key=lambda x: float(x.get("opportunity_score") or 0), reverse=True)

    # Se ambos providers entregarem candidatos, reserva até 2 vagas para ML
    # e até 2 para Shopee, sem sacrificar o ranking do restante.
    picks = []
    seen = set()
    for group in (ml[:2], sh[:2]):
        for item in group:
            key = f"{item.get('marketplace')}:{item.get('item_id') or item.get('url') or item.get('name')}"
            if key not in seen and len(picks) < limit:
                picks.append(item)
                seen.add(key)
    for item in ranked:
        key = f"{item.get('marketplace')}:{item.get('item_id') or item.get('url') or item.get('name')}"
        if key not in seen and len(picks) < limit:
            picks.append(item)
            seen.add(key)
    picks.sort(key=lambda x: float(x.get("opportunity_score") or 0), reverse=True)
    return picks[:limit]


def _v11_opportunities_central(payload: dict):
    body = dict(payload or {})
    body["include_meli"] = True
    result = _V11_ORIGINAL_OPPORTUNITIES_CENTRAL(body)
    items = result.get("items") or result.get("opportunities") or []
    try:
        limit = max(5, min(20, int(body.get("limit") or 10)))
    except Exception:
        limit = 10
    mixed = _v11_marketplace_mix(items, limit)
    diagnostic = list(result.get("diagnostic") or [])
    ml_count = sum(1 for x in items if str(x.get("marketplace") or "").lower() == "mercadolivre")
    sh_count = sum(1 for x in items if str(x.get("marketplace") or "").lower() == "shopee")
    diagnostic.append(f"V11.5: Mercado Livre={ml_count} · Shopee={sh_count}")
    result["mode"] = "completo"
    result["items"] = mixed
    result["opportunities"] = mixed
    result["returned"] = len(mixed)
    result["diagnostic"] = diagnostic
    result["message"] = " · ".join(diagnostic)
    return result

for _route in getattr(app, "routes", []):
    if getattr(_route, "path", None) == "/api/opportunities-central" and "POST" in (getattr(_route, "methods", set()) or set()):
        _route.endpoint = _v11_opportunities_central

# Atualiza a mensagem e o payload da interface, que antes informavam
# incorretamente que o Mercado Livre não era consultado no modo padrão.
try:
    HTML = HTML.replace(
        "status.textContent='⚡ Modo rápido: Shopee primeiro. Mercado Livre não bloqueia o garimpo.';",
        "status.textContent='⚡ Modo completo: Shopee + Mercado Livre. Aguarde a análise dos dois marketplaces.';"
    )
    HTML = HTML.replace(
        "body:JSON.stringify({niche:$('opportunityNiche').value.trim(),limit:Number($('opportunityLimit').value||10)})",
        "body:JSON.stringify({niche:$('opportunityNiche').value.trim(),limit:Number($('opportunityLimit').value||10),include_meli:true})"
    )
except Exception:
    pass

print("[V11.5] Mercado Livre + Shopee ativos no garimpo central; PRODUCT via catálogo; /items/{id} bloqueado; ranking com diversidade", flush=True)
