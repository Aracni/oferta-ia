"""OFERTA IA application loader.

A versão integral do aplicativo permanece congelada no commit-base conhecido.
Este carregador restaura essa versão em memória para que os patches de runtime
possam evoluir sem duplicar o arquivo monolítico no repositório.
"""
import time
import urllib.request

# O valor anterior era um BLOB SHA, não um commit/ref do GitHub.
# Por isso o raw.githubusercontent.com respondia 404 no Render.
_SOURCE = "https://raw.githubusercontent.com/Aracni/oferta-ia/41a35a18c9a59a737e5bef91ef0cc1f74d3e3525/app.py"

try:
    with urllib.request.urlopen(_SOURCE, timeout=20) as response:
        source = response.read().decode("utf-8")
except Exception as exc:
    raise RuntimeError(f"Não foi possível carregar o núcleo do OFERTA IA: {exc}") from exc

exec(compile(source, _SOURCE, "exec"), globals(), globals())

# PATCH V10.8 — usa o token válido também nas consultas de catálogo.
# O V10.7 removeu o Authorization ao tentar tornar endpoints de catálogo
# "públicos", mas o Mercado Livre está respondendo 401/403 para essas rotas.
# Mantemos cache e timeout curto, porém enviamos o Bearer token recebido.
_OFERTA_ORIGINAL_FETCH_JSON = _v9_fetch_json
_OFERTA_PUBLIC_CACHE = {}
_OFERTA_PUBLIC_CACHE_TTL = 300


def _oferta_public_catalog_url(url):
    return (
        "/items/" in url
        or "/products/" in url
    ) and "/applications/" not in url


def _oferta_fetch_json_optimized(token, url, params=None, timeout=10, trace=None, stage="HTTP"):
    # Endpoints protegidos e todos os demais continuam usando exatamente
    # o comportamento original do núcleo.
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
                "User-Agent": "OFERTA-IA/10.8",
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

        _v93_log(
            "ERROR",
            "Consulta de catálogo falhou",
            trace=trace,
            http=status,
            error=str((data or {}).get("message") or response.text[:300])[:300],
        )
        return data, status
    except Exception as exc:
        _v93_log("ERROR", "Falha na consulta de catálogo", trace=trace, error=str(exc)[:300])
        return None, None


_v9_fetch_json = _oferta_fetch_json_optimized

# PATCH V10.9 — resolve o vencedor do catálogo diretamente.
# O /products/{product_id} já traz buy_box_winner com item_id e preço.
# A implementação antiga fazia mais duas consultas (/products/.../items e
# /items/{id}) para cada PRODUCT e acabava descartando todos os candidatos.
# Usamos os dados oficiais do vencedor quando já estão completos; só caímos
# para a validação do ITEM quando o vencedor não traz preço suficiente.
_OFERTA_ORIGINAL_CATALOG_TO_ITEM = _v9_catalog_to_item


def _oferta_catalog_to_item_resilient(token, product_id, rank_position=None, query=""):
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
    if isinstance(winner, dict):
        item_id = winner.get("item_id") or winner.get("id")
        price = winner.get("price")
        try:
            price = float(price) if price not in (None, "") else None
        except Exception:
            price = None

        title = detail.get("name") or winner.get("title") or "Produto Mercado Livre"
        if item_id and price and price > 0 and not _looks_like_accessory(title):
            permalink = detail.get("permalink") or winner.get("permalink")
            if permalink and str(permalink).startswith("http"):
                old = winner.get("original_price")
                try:
                    old = float(old) if old not in (None, "") else None
                except Exception:
                    old = None
                item = {
                    "item_id": str(item_id),
                    "name": title,
                    "url": permalink,
                    "current_price": price,
                    "old_price": old,
                    "discount_rate": round((old - price) / old * 100, 2) if old and old > price else None,
                    "category": winner.get("category_id") or detail.get("domain_id"),
                    "image_url": (detail.get("pictures") or [{}])[0].get("url") if isinstance(detail.get("pictures"), list) and detail.get("pictures") else None,
                    "seller_id": winner.get("seller_id"),
                    "rating": None,
                    "marketplace": "mercadolivre",
                    "rank_position": rank_position,
                    "discovery_query": query,
                    "catalog_product_id": product_id,
                }
                if not item["image_url"] and isinstance(detail.get("pictures"), list) and detail.get("pictures"):
                    first = detail["pictures"][0]
                    if isinstance(first, dict):
                        item["image_url"] = first.get("secure_url") or first.get("url")
                return item

    # Fallback somente quando o detalhe do produto não trouxe um vencedor útil.
    # A função original mantém a compatibilidade com os demais formatos.
    try:
        return _OFERTA_ORIGINAL_CATALOG_TO_ITEM(token, product_id, rank_position, query)
    except Exception:
        return None


_v9_catalog_to_item = _oferta_catalog_to_item_resilient
