"""Inicialização automática do OFERTA IA.

O Render pode iniciar diretamente com `uvicorn app:app`, sem executar boot.py.
Quando PORT está presente, o app é carregado e os patches de inicialização são instalados antes que o uvicorn reutilize o módulo já carregado.
"""
import os

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
except Exception:
    pass

if os.environ.get("PORT"):
    try:
        import app as _oferta_app

        # V10.20/V10.21: este é o patch crítico. Instale-o primeiro para que
        # qualquer falha em outro patch não impeça a substituição de
        # _product_from_catalog usada diretamente pelo núcleo congelado.
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
