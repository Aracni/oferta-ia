"""OFERTA IA application loader.

A versão integral do aplicativo permanece congelada no commit-base conhecido.
Este carregador restaura essa versão em memória para que os patches de runtime
possam evoluir sem duplicar o arquivo monolítico no repositório.
"""
import html as _html
import json
import re
import time
import urllib.request
import threading

_SOURCE = "https://raw.githubusercontent.com/Aracni/oferta-ia/41a35a18c9a59a737e5bef91ef0cc1f74d3e3525/app.py"

try:
    with urllib.request.urlopen(_SOURCE, timeout=20) as response:
        source = response.read().decode("utf-8")
except Exception as exc:
    raise RuntimeError(f"Não foi possível carregar o núcleo do OFERTA IA: {exc}") from exc

# PATCH V10.18 — normalização do hostname do Mercado Livre no núcleo congelado.
# O log de produção confirmou que o código efetivamente executado ainda estava
# montando api.mercadolivre.com. A API oficial usa api.mercadolibre.com.
# Corrigimos o texto do núcleo ANTES do exec, garantindo que o endereço correto
# seja usado desde a própria construção da URL, inclusive nos logs.
source = source.replace("api.mercadolivre.com", "api.mercadolibre.com")

exec(compile(source, _SOURCE, "exec"), globals(), globals())

# PATCH V10.17 — estabilidade de rede/DNS no Render.
# O teste V10.16 mostrou que trends/highlights funcionam, mas dezenas de chamadas
# simultâneas a /products/{id} falharam com NameResolutionError no mesmo instante.
# Evitamos o pico de resolução DNS usando um pequeno lock somente nas chamadas
# de catálogo e fazemos retries curtos para erros transitórios de conexão/DNS.
# Mantemos o circuit breaker da busca pública e a recuperação de preço da V10.16.
_OFERTA_ORIGINAL_FETCH_JSON = _v9_fetch_json
_OFERTA_PUBLIC_CACHE = {}
_OFERTA_PUBLIC_CACHE_TTL = 300
_OFERTA_SEARCH_CACHE = {}
_OFERTA_SEARCH_CACHE_TTL = 300
_OFERTA_PAGE_CACHE = {}
_OFERTA_PAGE_CACHE_TTL = 300
_OFERTA_SEARCH_BLOCKED = False
_OFERTA_CATALOG_LOCK = threading.Lock()


def _oferta_public_catalog_url(url):
    return ("/items/" in url or "/products/" in url) and "/applications/" not in url


def _oferta_fetch_json_optimized(token, url, params=None, timeout=10, trace=None, stage="HTTP"):
    if not _oferta_public_catalog_url(url):
        return _OFERTA_ORIGINAL_FETCH_JSON(token, url, params, timeout, trace, stage)
    safe_params = dict(params or {})
    cache_key = (url, tuple(sorted((str(k), str(v)) for k, v in safe_params.items())))
    cached = _OFERTA_PUBLIC_CACHE.get(cache_key)
    if cached and time.time() - cached[0] <= _OFERTA_PUBLIC_CACHE_TTL:
        _v93_log(stage, "Catálogo atendido pelo cache", trace=trace, url=url)
        return cached[1], cached[2]

    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json", "User-Agent": "OFERTA-IA/10.17"}
    attempts = 3
    last_error = None
    with _OFERTA_CATALOG_LOCK:
        for attempt in range(1, attempts + 1):
            try:
                _v93_log(stage, "Consulta de catálogo com autorização", trace=trace, url=url, attempt=attempt)
                response = requests.get(url, params=safe_params, headers=headers, timeout=min(int(timeout or 5), 5))
                try:
                    data = response.json()
                except Exception:
                    data = {}
                status = response.status_code
                if response.ok:
                    _OFERTA_PUBLIC_CACHE[cache_key] = (time.time(), data, status)
                    _v93_log(stage, "Consulta de catálogo OK", trace=trace, http=status, attempt=attempt)
                    return data, status
                if status in (429, 500, 502, 503, 504):
                    last_error = f"HTTP {status}"
                    if attempt < attempts:
                        time.sleep(0.35 * attempt)
                        continue
                _v93_log("ERROR", "Consulta de catálogo falhou", trace=trace, http=status, attempt=attempt, error=str((data or {}).get("message") or response.text[:300])[:300])
                return data, status
            except Exception as exc:
                last_error = str(exc)
                text = last_error.lower()
                transient = any(marker in text for marker in ("name or service not known", "temporary failure in name resolution", "failed to resolve", "connection reset", "connection aborted", "connect timeout", "connection timed out"))
                if transient and attempt < attempts:
                    _v93_log("RETRY", "Falha transitória de rede no catálogo; tentando novamente", trace=trace, attempt=attempt, error=last_error[:220])
                    time.sleep(0.45 * attempt)
                    continue
                break

    _v93_log("ERROR", "Falha na consulta de catálogo", trace=trace, error=(last_error or "erro desconhecido")[:300])
    return None, None


_v9_fetch_json = _oferta_fetch_json_optimized


def _oferta_number(value):
    try:
        return float(value) if value not in (None, "") else None
    except Exception:
        return None


def _oferta_tokens(text):
    text = str(text or "").lower()
    return {token for token in re.findall(r"[a-z0-9à-ÿ]{3,}", text) if token not in {"para", "com", "sem", "por", "uma", "the", "and"}}


def _oferta_search_relevant(source_title, result_title):
    source = _oferta_tokens(source_title)
    result = _oferta_tokens(result_title)
    if not source or not result:
        return False
    overlap = source & result
    if not overlap:
        return False
    if len(source) <= 2:
        return len(overlap) >= 1
    return len(overlap) >= 2 or len(overlap) / len(source) >= 0.25


def _oferta_pick_search_item(payload, source_title=""):
    if not isinstance(payload, dict):
        return None
    results = payload.get("results")
    if not isinstance(results, list):
        return None
    for item in results:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or ""
        if _looks_like_accessory(title):
            continue
        if source_title and not _oferta_search_relevant(source_title, title):
            continue
        item_id = item.get("id")
        price = _oferta_number(item.get("price"))
        permalink = item.get("permalink")
        status = str(item.get("status", "active")).lower()
        if not item_id or price is None or price <= 0 or status not in {"active", ""}:
            continue
        if not isinstance(permalink, str) or not permalink.startswith("http"):
            permalink = f"https://produto.mercadolivre.com.br/{item_id}"
        pictures = item.get("thumbnail") or item.get("secure_thumbnail")
        seller = item.get("seller")
        seller_id = seller.get("id") if isinstance(seller, dict) else None
        return {"item_id": str(item_id), "name": title, "url": permalink, "current_price": price, "old_price": _oferta_number(item.get("original_price")), "discount_rate": None, "category": item.get("category_id"), "image_url": pictures, "seller_id": seller_id, "rating": None, "marketplace": "mercadolivre"}
    return None


def _oferta_clean_text(value):
    if value is None:
        return ""
    text = _html.unescape(str(value))
    text = text.replace("\\u0022", '"').replace("\\u002F", "/").replace("\\/", "/")
    text = re.sub(r"\\x([0-9a-fA-F]{2})", lambda m: chr(int(m.group(1), 16)), text)
    return text


def _oferta_structured_price(obj, depth=0):
    if depth > 5 or obj is None:
        return None
    if isinstance(obj, dict):
        for key in ("price", "lowPrice", "min_price", "sale_price", "current_price"):
            if key in obj:
                value = _oferta_number(obj.get(key))
                if value is not None and 0 < value < 1000000:
                    return value
        offers = obj.get("offers")
        value = _oferta_structured_price(offers, depth + 1)
        if value is not None:
            return value
        for key in ("data", "props", "pageProps", "initialState", "state", "product", "item"):
            if key in obj:
                value = _oferta_structured_price(obj.get(key), depth + 1)
                if value is not None:
                    return value
    elif isinstance(obj, list):
        for child in obj[:30]:
            value = _oferta_structured_price(child, depth + 1)
            if value is not None:
                return value
    return None


def _oferta_extract_page_product(html, fallback_title="", fallback_url="", product_id=""):
    if not isinstance(html, str) or not html:
        return None
    raw_html = html
    decoded = _oferta_clean_text(html)
    title = fallback_title
    title_patterns = [
        r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)',
        r'<h1[^>]*>(.*?)</h1>',
        r'"title"\s*:\s*"([^"\n]{4,220})"',
    ]
    for pattern in title_patterns:
        m = re.search(pattern, decoded, re.I | re.S)
        if m:
            candidate = re.sub(r"<[^>]+>", " ", m.group(1))
            candidate = re.sub(r"\s+", " ", _html.unescape(candidate)).strip()
            if len(candidate) >= 4:
                title = candidate
                break

    price = None
    price_source = None
    for block in re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', decoded, re.I | re.S):
        block = block.strip()
        try:
            payload = json.loads(block)
            price = _oferta_structured_price(payload)
        except Exception:
            try:
                price = _oferta_structured_price(json.loads(_html.unescape(block)))
            except Exception:
                price = None
        if price is not None:
            price_source = "jsonld"
            break
