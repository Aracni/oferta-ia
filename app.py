"""OFERTA IA application loader.

V11.2 mantém o resolvedor independente do Mercado Livre e corrige o
contador diagnóstico de candidatos ativos no caminho PRODUCT/catalog.
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
# V11.2 — DIAGNÓSTICO + RESOLVEDOR INDEPENDENTE
# ---------------------------------------------------------------------------
# O núcleo histórico não incrementa o contador `active` no caminho PRODUCT /
# catálogo, embora um candidato que chega a `valid` já tenha passado pela
# validação de ativo. Interceptamos somente a mensagem diagnóstica final para
# que o log reflita a realidade, sem alterar a regra de validação.
_V11_CORE_LOG = _v93_log


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

_V11_ORIGINAL_FETCH_JSON = _v9_fetch_json
_V11_ITEM_INDEX = {}
_V11_PRODUCT_INDEX = {}
_V11_CATALOG_CACHE = {}
_V11_CATALOG_TTL = 300
_V11_LOCK = threading.RLock()
_V11_VERSION = "11.2"


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
    if not isinstance(payload, dict):
        return
    rows = payload.get("results")
    if not isinstance(rows, list):
        rows = payload.get("items")
    if not isinstance(rows, list):
        return
    product = _V11_PRODUCT_INDEX.get(str(product_id), {})
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

    return {
        "id": str(item_id),
        "item_id": str(item_id),
        "site_id": site_id,
        "title": title,
        "name": title,
        "seller_id": row.get("seller_id"),
        "category_id": row.get("category_id"),
        "price": price,
        "base_price": price,
        "current_price": price,
        "original_price": original,
        "currency_id": row.get("currency_id") or "BRL",
        "available_quantity": row.get("available_quantity") or 1,
        "initial_quantity": row.get("initial_quantity") or row.get("available_quantity") or 1,
        "sold_quantity": row.get("sold_quantity") or 0,
        "permalink": permalink,
        "thumbnail": row.get("thumbnail") or row.get("secure_thumbnail"),
        "catalog_product_id": row.get("product_id"),
        "product_id": row.get("product_id"),
        "status": row.get("status") or "active",
        "active": True,
        "condition": row.get("condition") or "new",
        "buying_mode": row.get("buying_mode") or "buy_it_now",
        "listing_type_id": row.get("listing_type_id") or "gold_special",
        "listing_type": row.get("listing_type") or row.get("listing_type_id") or "gold_special",
        "accepts_mercadopago": True,
        "shipping": row.get("shipping") or {},
    }


def _v11_public_search(token, item_id, trace=None):
    try:
        site = _v11_site_from_id(item_id)
        url = f"https://api.mercadolibre.com/sites/{site}/search"
        params = {"q": str(item_id), "limit": 10}
        response = requests.get(
            url,
            params=params,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json", "User-Agent": "OFERTA-IA/11.2"},
            timeout=5,
        )
        data = response.json() if response.content else {}
        for candidate in (data or {}).get("results", []) if isinstance(data, dict) else []:
            if str(candidate.get("id")) == str(item_id):
                return candidate, response.status_code
    except Exception as exc:
        try:
            _v93_log("ERROR", "Fallback público do ITEM falhou", trace=trace, error=str(exc)[:220])
        except Exception:
            pass
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
            data = _v11_synthetic_item(item_id)
            try:
                _v93_log("CATALOG_V11", "ITEM resolvido pelo índice do catálogo; /items/{id} bloqueado", trace=trace, item_id=item_id, http=200)
            except Exception:
                pass
            return data, 200

        if url_text.rstrip("/").lower().endswith("/items/" + item_id.lower()):
            data, status = _v11_public_search(token, item_id, trace=trace)
            if data is not None:
                with _V11_LOCK:
                    _V11_ITEM_INDEX[item_id] = dict(data)
                try:
                    _v93_log("CATALOG_V11", "ITEM recuperado por busca pública; /items/{id} bloqueado", trace=trace, item_id=item_id, http=status or 200)
                except Exception:
                    pass
                return data, status or 200

        try:
            _v93_log("CATALOG_V11", "ITEM sem dados no índice; requisição /items/{id} bloqueada", trace=trace, item_id=item_id, http=403)
        except Exception:
            pass
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
        with _V11_LOCK:
            _V11_CATALOG_CACHE[key] = (time.time(), data, status)
        m = re.search(r"/products/(ML[A-Z][0-9]+)(?:/|$)", url_text, re.I)
        pid = m.group(1).upper() if m else None
        if pid:
            if url_text.rstrip("/").lower().endswith("/items"):
                _v11_remember_items(pid, data)
            else:
                _v11_remember_product(data)
    return data, status


_v9_fetch_json = _v11_fetch_json

try:
    if "_meli_get" in globals():
        _V11_ORIGINAL_MELI_GET = _meli_get

        def _v11_meli_get(token, url, params=None, timeout=10):
            data, status = _v11_fetch_json(token, url, params, timeout)
            return data, status

        _meli_get = _v11_meli_get
except Exception:
    pass

print("[V11.2] resolvedor independente ativo: /items/{id} bloqueado; diagnóstico VALIDATE corrigido para PRODUCT/catalog", flush=True)
