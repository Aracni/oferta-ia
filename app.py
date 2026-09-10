"""OFERTA IA application loader.

A versão integral do aplicativo permanece congelada no commit-base conhecido.
Este carregador restaura essa versão em memória para que os patches de runtime
possam evoluir sem duplicar o arquivo monolítico no repositório.
"""
import re
import time
import urllib.request

_SOURCE = "https://raw.githubusercontent.com/Aracni/oferta-ia/41a35a18c9a59a737e5bef91ef0cc1f74d3e3525/app.py"

try:
    with urllib.request.urlopen(_SOURCE, timeout=20) as response:
        source = response.read().decode("utf-8")
except Exception as exc:
    raise RuntimeError(f"Não foi possível carregar o núcleo do OFERTA IA: {exc}") from exc

exec(compile(source, _SOURCE, "exec"), globals(), globals())

# PATCH V10.15 — catálogo sem cascata + recuperação por página pública.
# O endpoint /sites/MLB/search continua devolvendo 403 no ambiente do Render.
# Portanto, quando o PDP da API não expõe preço, usamos a própria página pública
# do produto como segunda rota, sem token e sem voltar para /products/{id}/items.
_OFERTA_ORIGINAL_FETCH_JSON = _v9_fetch_json
_OFERTA_PUBLIC_CACHE = {}
_OFERTA_PUBLIC_CACHE_TTL = 300
_OFERTA_SEARCH_CACHE = {}
_OFERTA_SEARCH_CACHE_TTL = 300
_OFERTA_PAGE_CACHE = {}
_OFERTA_PAGE_CACHE_TTL = 300


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

    try:
        _v93_log(stage, "Consulta de catálogo com autorização", trace=trace, url=url)
        response = requests.get(url, params=safe_params, headers={"Authorization": f"Bearer {token}", "Accept": "application/json", "User-Agent": "OFERTA-IA/10.15"}, timeout=min(int(timeout or 5), 5))
        try:
            data = response.json()
        except Exception:
            data = {}
        status = response.status_code
        if response.ok:
            _OFERTA_PUBLIC_CACHE[cache_key] = (time.time(), data, status)
            _v93_log(stage, "Consulta de catálogo OK", trace=trace, http=status)
            return data, status
        _v93_log("ERROR", "Consulta de catálogo falhou", trace=trace, http=status, error=str((data or {}).get("message") or response.text[:300])[:300])
        return data, status
    except Exception as exc:
        _v93_log("ERROR", "Falha na consulta de catálogo", trace=trace, error=str(exc)[:300])
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


def _oferta_extract_page_product(html, fallback_title="", fallback_url="", product_id=""):
    if not isinstance(html, str) or not html:
        return None

    title = fallback_title
    title_patterns = [
        r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)',
        r'<h1[^>]*>(.*?)</h1>',
        r'"title"\s*:\s*"([^"\n]{4,220})"',
    ]
    for pattern in title_patterns:
        m = re.search(pattern, html, re.I | re.S)
        if m:
            candidate = re.sub(r"<[^>]+>", " ", m.group(1))
            candidate = re.sub(r"\s+", " ", candidate).strip()
            if len(candidate) >= 4:
                title = candidate
                break

    price = None
    price_patterns = [
        r'"price"\s*:\s*([0-9]+(?:\.[0-9]+)?)',
        r'"amount"\s*:\s*([0-9]+(?:\.[0-9]+)?)',
        r'itemprop=["\']price["\'][^>]+content=["\']([0-9]+(?:\.[0-9]+)?)',
        r'R\$\s*([0-9]{1,6}(?:\.[0-9]{3})*(?:,[0-9]{2})?)',
    ]
    for pattern in price_patterns:
        for m in re.finditer(pattern, html, re.I | re.S):
            raw = m.group(1).replace(".", "").replace(",", ".") if "," in m.group(1) else m.group(1)
            value = _oferta_number(raw)
            if value is not None and 0 < value < 1000000:
                price = value
                break
        if price is not None:
            break

    if price is None:
        return None

    image = None
    m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', html, re.I | re.S)
    if m:
        image = m.group(1).strip()

    item_id = product_id
    id_match = re.search(r'MLB[-_]?([0-9]{6,})', html, re.I)
    if id_match:
        item_id = "MLB" + id_match.group(1)

    return {"item_id": str(item_id or ""), "name": title or fallback_title or "Produto Mercado Livre", "url": fallback_url or (f"https://www.mercadolivre.com.br/p/{product_id}" if product_id else ""), "current_price": price, "old_price": None, "discount_rate": None, "category": None, "image_url": image, "seller_id": None, "rating": None, "marketplace": "mercadolivre"}


def _oferta_fetch_public_page(title, permalink, product_id):
    url = permalink if isinstance(permalink, str) and permalink.startswith("http") else f"https://www.mercadolivre.com.br/p/{product_id}"
    cached = _OFERTA_PAGE_CACHE.get(url)
    if cached and time.time() - cached[0] <= _OFERTA_PAGE_CACHE_TTL:
        return cached[1]
    try:
        _v93_log("PAGE", "Consulta da página pública iniciada", trace=None, product_id=product_id)
        response = requests.get(url, headers={"Accept": "text/html,application/xhtml+xml", "Accept-Language": "pt-BR,pt;q=0.9", "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36"}, timeout=8, allow_redirects=True)
        if response.ok:
            result = _oferta_extract_page_product(response.text, title, response.url, product_id)
            _OFERTA_PAGE_CACHE[url] = (time.time(), result)
            if result:
                _v93_log("PAGE", "Produto recuperado pela página pública", trace=None, product_id=product_id, price=result.get("current_price"))
            else:
                _v93_log("PAGE", "Página pública sem preço utilizável", trace=None, product_id=product_id, http=response.status_code)
            return result
        _OFERTA_PAGE_CACHE[url] = (time.time(), None)
        _v93_log("PAGE", "Página pública recusada", trace=None, product_id=product_id, http=response.status_code)
    except Exception as exc:
        _OFERTA_PAGE_CACHE[url] = (time.time(), None)
        _v93_log("PAGE", "Falha na página pública", trace=None, product_id=product_id, error=str(exc)[:200])
    return None


def _oferta_search_public_listing(token, title, query="", rank_position=None, permalink=None, product_id=None):
    if rank_position is not None:
        try:
            if int(rank_position) > 25:
                return None
        except Exception:
            pass

    # Primeiro tentamos a busca pública somente para compatibilidade. O Render
    # pode continuar bloqueando este endpoint; nesse caso caímos para a página.
    search_text = (title or query or "").strip()[:120]
    if search_text:
        cache_key = search_text.lower()
        cached = _OFERTA_SEARCH_CACHE.get(cache_key)
        if cached and time.time() - cached[0] <= _OFERTA_SEARCH_CACHE_TTL:
            if cached[1]:
                return cached[1]
        try:
            _v93_log("SEARCH", "Busca pública iniciada", trace=None, query=search_text[:80])
            response = requests.get("https://api.mercadolibre.com/sites/MLB/search", params={"q": search_text, "limit": 5}, headers={"Accept": "application/json", "User-Agent": "OFERTA-IA/10.15"}, timeout=4)
            try:
                payload = response.json()
            except Exception:
                payload = {}
            result = _oferta_pick_search_item(payload, source_title=title)
            _OFERTA_SEARCH_CACHE[cache_key] = (time.time(), result)
            if result:
                _v93_log("SEARCH", "Publicação recuperada pela busca", trace=None, query=search_text[:80], item_id=result.get("item_id"), price=result.get("current_price"))
                return result
            _v93_log("SEARCH", "Busca pública sem publicação utilizável", trace=None, query=search_text[:80], http=response.status_code)
        except Exception as exc:
            _v93_log("SEARCH", "Falha na busca pública", trace=None, query=search_text[:80], error=str(exc)[:200])

    # Rota principal de recuperação quando a API de busca está bloqueada.
    return _oferta_fetch_public_page(title, permalink, product_id)


def _oferta_catalog_to_item_strict(token, product_id, rank_position=None, query=""):
    detail, status = _v9_fetch_json(token, f"https://api.mercadolibre.com/products/{product_id}", timeout=6, trace=None, stage="CATALOG")
    if not isinstance(detail, dict):
        return None

    winner = detail.get("buy_box_winner")
    title = detail.get("name") or "Produto Mercado Livre"
    if _looks_like_accessory(title):
        return None

    item_id = None
    price = None
    old = None
    seller_id = None
    permalink = detail.get("permalink")
    image_url = None

    if isinstance(winner, dict):
        item_id = winner.get("item_id") or winner.get("id")
        price = _oferta_number(winner.get("price"))
        old = _oferta_number(winner.get("original_price"))
        seller_id = winner.get("seller_id")
        permalink = winner.get("permalink") or permalink

    if price is None:
        price_range = detail.get("buy_box_winner_price_range")
        if isinstance(price_range, dict):
            minimum = price_range.get("min")
            if isinstance(minimum, dict):
                price = _oferta_number(minimum.get("price"))

    active = str(detail.get("status", "active")).lower() == "active"
    if not active:
        _v93_log("CATALOG", "Produto rejeitado por status", trace=None, product_id=product_id, product_status=detail.get("status"))
        return None

    if price is None or price <= 0:
        _v93_log("CATALOG", "PDP sem preço; tentando recuperação pública", trace=None, product_id=product_id)
        recovered = _oferta_search_public_listing(token, title, query, rank_position, permalink=permalink, product_id=product_id)
        if recovered:
            recovered.update({"rank_position": rank_position, "discovery_query": query, "catalog_product_id": str(product_id), "catalog_only": False})
            return recovered
        _v93_log("CATALOG", "Produto rejeitado sem preço utilizável", trace=None, product_id=product_id)
        return None

    if not isinstance(permalink, str) or not permalink.startswith("http"):
        permalink = f"https://www.mercadolivre.com.br/p/{product_id}"

    pictures = detail.get("pictures")
    if isinstance(pictures, list) and pictures:
        first = pictures[0]
        if isinstance(first, dict):
            image_url = first.get("secure_url") or first.get("url")

    discount = round((old - price) / old * 100, 2) if old and old > price else None
    return {"item_id": str(item_id or product_id), "name": title, "url": permalink, "current_price": price, "old_price": old, "discount_rate": discount, "category": detail.get("domain_id"), "image_url": image_url, "seller_id": seller_id, "rating": None, "marketplace": "mercadolivre", "rank_position": rank_position, "discovery_query": query, "catalog_product_id": str(product_id), "catalog_only": not bool(item_id)}


_v9_catalog_to_item = _oferta_catalog_to_item_strict
