"""OFERTA IA application loader.

A versão integral do aplicativo permanece congelada no commit-base conhecido.
Este carregador restaura essa versão em memória para que os patches de runtime
possam evoluir sem duplicar o arquivo monolítico no repositório.
"""
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

# PATCH V10.5 — alguns endpoints públicos de catálogo do Mercado Livre
# estão devolvendo 403 quando recebem o access_token da aplicação. A busca
# de catálogo continua autorizada, mas a validação pública de /items/{id}
# pode ser feita sem autenticação. Para não transformar esses 403 em perda
# silenciosa de todos os candidatos, repetimos somente esses recursos sem
# o header Authorization. Endpoints privados continuam protegidos.
_oferta_original_fetch_json = _v9_fetch_json


def _oferta_fetch_json_public_catalog(token, url, params=None, timeout=10, trace=None, stage="HTTP"):
    data, status = _oferta_original_fetch_json(token, url, params, timeout, trace, stage)
    if status != 403:
        return data, status

    public_catalog = (
        "/items/" in url
        or "/products/" in url
    ) and "/applications/" not in url

    if not public_catalog:
        return data, status

    try:
        safe_params = dict(params or {})
        _v93_log(
            stage,
            "HTTP 403 em catálogo; tentando consulta pública sem token",
            trace=trace,
            url=url,
        )
        response = requests.get(
            url,
            params=safe_params,
            headers={
                "Accept": "application/json",
                "User-Agent": "OFERTA-IA/10.5",
            },
            timeout=timeout,
        )
        try:
            public_data = response.json()
        except Exception:
            public_data = {}
        if response.ok:
            _v93_log(
                stage,
                "Consulta pública do catálogo OK",
                trace=trace,
                http=response.status_code,
            )
            return public_data, response.status_code
        _v93_log(
            "ERROR",
            "Consulta pública do catálogo também falhou",
            trace=trace,
            http=response.status_code,
            error=str((public_data or {}).get("message") or response.text[:300])[:300],
        )
    except Exception as exc:
        _v93_log(
            "ERROR",
            "Falha na consulta pública do catálogo",
            trace=trace,
            error=str(exc)[:300],
        )

    return data, status


_v9_fetch_json = _oferta_fetch_json_public_catalog
