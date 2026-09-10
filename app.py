"""OFERTA IA application loader.

A versão integral do aplicativo permanece congelada no commit-base conhecido.
Este carregador restaura essa versão em memória para que os patches de runtime
possam evoluir sem duplicar o arquivo monolítico no repositório.
"""
import time
import urllib.request

_SOURCE = "https://raw.githubusercontent.com/Aracni/oferta-ia/41a35a18c9a59a737e5bef91ef0cc1f74d3e3525/app.py"

try:
    with urllib.request.urlopen(_SOURCE, timeout=20) as response:
        source = response.read().decode("utf-8")
except Exception as exc:
    raise RuntimeError(f"Não foi possível carregar o núcleo do OFERTA IA: {exc}") from exc

exec(compile(source, _SOURCE, "exec"), globals(), globals())

# PATCH V10.12 — catálogo sem cascata.
# O ranking já entrega PRODUCT IDs. Para cada PRODUCT fazemos somente
# /products/{id}. Nunca caímos automaticamente em /products/{id}/items
# ou /items/{id}; essas consultas adicionais estavam gerando 403/429 e
# consumindo o orçamento de requisições. ITEM continua sendo validado por
# /items/{id}, pois nesse caso o ranking já forneceu uma publicação real.
_OFERTA_ORIGINAL_FETCH_JSON = _v9_fetch_json
_OFERTA_PUBLIC_CACHE = {}
_OFERTA_PUBLIC_CACHE_TTL = 300


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
        response = requests.get(
            url,
            params=safe_params,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "User-Agent": "OFERTA-IA/10.12",
            },
            timeout=min(int(timeout or 5), 5),
        )
        try:
            data = response.json()
        except Exception:
            data = {}
        status = response.status_code
        if response.ok:
            _OFERTA_PUBLIC_CACHE[cache_key] = (time.time(), data, status)
            _v93_log(stage, "Consulta de catálogo OK", trace=trace, http=status)
            return data, status
        _v93_log("ERROR", "Consulta de catálogo falhou", trace=trace, http=status,
                  error=str((data or {}).get("message") or response.text[:300])[:300])
        return data, status
    except Exception as exc:
        _v93_log("ERROR", "Falha na consulta de catálogo", trace=trace, error=str(exc)[:300])
        return None, None


_v9_fetch_json = _oferta_fetch_json_optimized

# PATCH V10.12 — resolver PRODUCT estritamente pelo PDP.
# Não chama mais o resolver antigo, porque ele obrigatoriamente dispara
# /products/{id}/items e depois /items/{id} quando o Buy Box não está presente.
def _oferta_catalog_to_item_strict(token, product_id, rank_position=None, query=""):
    detail, status = _v9_fetch_json(
        token,
        f"https://api.mercadolibre.com/products/{product_id}",
        timeout=6,
        trace=None,
        stage="CATALOG",
    )
    if not isinstance(detail, dict):
        return None

    winner = detail.get("buy_box_winner")
    title = detail.get("name") or "Produto Mercado Livre"
    if _looks_like_accessory(title):
        return None

    def number(value):
        try:
            return float(value) if value not in (None, "") else None
        except Exception:
            return None

    item_id = None
    price = None
    old = None
    seller_id = None
    permalink = detail.get("permalink")
    image_url = None

    if isinstance(winner, dict):
        item_id = winner.get("item_id") or winner.get("id")
        price = number(winner.get("price"))
        old = number(winner.get("original_price"))
        seller_id = winner.get("seller_id")
        permalink = winner.get("permalink") or permalink

    # Se o Buy Box não existir, usamos o menor preço oficial exposto pelo PDP.
    if price is None:
        price_range = detail.get("buy_box_winner_price_range")
        if isinstance(price_range, dict):
            minimum = price_range.get("min")
            if isinstance(minimum, dict):
                price = number(minimum.get("price"))

    if price is None or price <= 0:
        _v93_log("CATALOG", "Produto rejeitado sem preço utilizável", trace=None, product_id=product_id)
        return None

    # PDPs ativos normalmente têm permalink. Se a API não entregar, usamos
    # uma URL de produto estável baseada no ID, sem precisar buscar um ITEM.
    if not isinstance(permalink, str) or not permalink.startswith("http"):
        permalink = f"https://www.mercadolivre.com.br/p/{product_id}"

    pictures = detail.get("pictures")
    if isinstance(pictures, list) and pictures:
        first = pictures[0]
        if isinstance(first, dict):
            image_url = first.get("secure_url") or first.get("url")

    active = str(detail.get("status", "active")).lower() == "active"
    if not active:
        _v93_log("CATALOG", "Produto rejeitado por status", trace=None,
                  product_id=product_id, product_status=detail.get("status"))
        return None

    return {
        "item_id": str(item_id or product_id),
        "name": title,
        "url": permalink,
        "current_price": price,
        "old_price": old,
        "discount_rate": round((old - price) / old * 100, 2) if old and old > price else None,
        "category": detail.get("domain_id"),
        "image_url": image_url,
        "seller_id": seller_id,
        "rating": None,
        "marketplace": "mercadolivre",
        "rank_position": rank_position,
        "discovery_query": query,
        "catalog_product_id": str(product_id),
        "catalog_only": not bool(item_id),
    }


_v9_catalog_to_item = _oferta_catalog_to_item_strict
