"""Inicialização automática do OFERTA IA.

O Render pode iniciar diretamente com `uvicorn app:app`, sem executar boot.py.
Este arquivo é carregado pelo Python antes do uvicorn quando o diretório do app
está no sys.path. A ativação do patch de catálogo NÃO depende de PORT, porque em
alguns ambientes de execução o Render só injeta PORT depois da inicialização.
"""
import os

# Marcador extremamente cedo para confirmar no log do Render que este módulo foi carregado.
print("[SITE] sitecustomize carregado", flush=True)

# Compatibilidade Mercado Livre: a API oficial usa api.mercadolibre.com.
try:
    import requests
    from urllib.parse import urlsplit, urlunsplit

    _oferta_original_session_request = requests.sessions.Session.request

    def _oferta_normalized_session_request(self, method, url, *args, **kwargs):
        try:
            parts = urlsplit(str(url))
            if parts.hostname == "api.mercadolivre.com":
                netloc = "api.mercadolibre.com"
                if parts.port:
                    netloc += f":{parts.port}"
                url = urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
        except Exception:
            pass
        return _oferta_original_session_request(self, method, url, *args, **kwargs)

    requests.sessions.Session.request = _oferta_normalized_session_request
    print("[SITE] hostname Mercado Livre normalizado", flush=True)
except Exception as exc:
    print(f"[SITE][AVISO] normalização de hostname não ativada: {type(exc).__name__}: {exc}", flush=True)

# V10.22 — não condicionar a ativação ao PORT.
# O log V10.21 não exibiu nenhum marcador [SITE]/[CATALOG], embora o código
# estivesse no branch correto. Isso indica que o bloco condicionado por PORT não
# foi executado (ou sitecustomize não chegou a ser observado). Agora o marcador
# inicial torna o diagnóstico inequívoco e a ativação é independente de PORT.
try:
    import app as _oferta_app

    # Patch crítico primeiro: substitui a função realmente usada pelo núcleo.
    import meli_catalog_patch as _meli_catalog_patch
    _meli_catalog_patch.install(_oferta_app)
    print("[SITE] CATALOG V10.20 instalado antes dos demais patches", flush=True)

    # Os patches auxiliares são isolados: uma falha neles não pode derrubar
    # o resolver de catálogo.
    try:
        import v106_patch as _v106
        _v106.install(_oferta_app)
    except Exception as exc:
        print(f"[SITE][AVISO] v106_patch não ativado: {type(exc).__name__}: {exc}", flush=True)

    try:
        _oferta_app.app._get_connection = _oferta_app._get_connection
        _oferta_app.app._save_connection = _oferta_app._save_connection
    except Exception as exc:
        print(f"[SITE][AVISO] helpers de persistência não mapeados: {type(exc).__name__}: {exc}", flush=True)

    try:
        import meli_auto as _meli_auto
        _meli_auto.install(_oferta_app.app)
    except Exception as exc:
        print(f"[SITE][AVISO] meli_auto não ativado: {type(exc).__name__}: {exc}", flush=True)

    print("[SITE] OFERTA IA + catálogo V10.20 ativados", flush=True)
except Exception as exc:
    print(
        f"[SITE][ERRO CRÍTICO] App/patch de catálogo não puderam ser ativados: {type(exc).__name__}: {exc}",
        flush=True,
    )
