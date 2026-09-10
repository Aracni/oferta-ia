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

# PATCH V10.6 — acelera o garimpo do Mercado Livre.
# Os logs mostraram que /items/{id} e /products/{id}/items estavam retornando
# 403 com o token da aplicação. O código anterior fazia primeiro a chamada
# autenticada e só depois repetia a mesma consulta sem token. Isso duplicava
# requisições e aumentava bastante o tempo da pesquisa.
#
# Para recursos de catálogo, tentamos diretamente a consulta pública. Mantemos
# produtos privados/protegidos fora deste caminho. Também usamos um cache curto
# para evitar repetir a mesma consulta durante o mesmo garimpo.
_OFERTA_PUBLIC_CACHE = {}
_OFERTA_PUBLIC_CACHE_TTL = 300


def _oferta_public_catalog_url(url):
    return (
        "/items/" in url
        or "/products/" in url
    ) and "/applications/" not in url


def _oferta_fetch_json_optimized(token, url, params=None, timeout=10, trace=None, stage="HTTP"):
    if not _oferta_public_catalog_url(url):
        return _v9_fetch_json(token, url, params, timeout, trace, stage)

    safe_params = dict(params or {})
    cache_key = (url, tuple(sorted((str(k), str(v)) for k, v in safe_params.items())))
    cached = _OFERTA_PUBLIC_CACHE.get(cache_key)
    if cached and time.time() - cached[0] <= _OFERTA_PUBLIC_CACHE_TTL:
        _v93_log(stage, "Catálogo atendido pelo cache", trace=trace, url=url)
        return cached[1], cached[2]

    try:
        _v93_log(stage, "Consulta pública direta do catálogo", trace=trace, url=url)
        response = requests.get(
            url,
            params=safe_params,
            headers={
                "Accept": "application/json",
                "User-Agent": "OFERTA-IA/10.6",
            },
            # Catálogo público não deve segurar o garimpo por vários segundos.
            timeout=min(int(timeout or 5), 5),
        )
        try:
            data = response.json()
        except Exception:
            data = {}
        status = response.status_code
        if response.ok:
            _OFERTA_PUBLIC_CACHE[cache_key] = (time.time(), data, status)
            _v93_log(stage, "Consulta pública do catálogo OK", trace=trace, http=status)
            return data, status

        _v93_log(
            "ERROR",
            "Consulta pública do catálogo falhou",
            trace=trace,
            http=status,
            error=str((data or {}).get("message") or response.text[:300])[:300],
        )
        return data, status
    except Exception as exc:
        _v93_log("ERROR", "Falha na consulta pública do catálogo", trace=trace, error=str(exc)[:300])
        return None, None


_v9_fetch_json = _oferta_fetch_json_optimized
