"""Inicialização automática do OFERTA IA.

O Render pode iniciar diretamente com `uvicorn app:app`, sem executar boot.py.
Quando PORT está presente, o app é carregado e os patches de inicialização são instalados antes que o uvicorn reutilize o módulo já carregado.
"""
import os

if os.environ.get("PORT"):
    try:
        import app as _oferta_app
        import v106_patch as _v106
        _v106.install(_oferta_app)

        # Disponibiliza ao patch automático somente os helpers internos de
        # persistência já existentes no app.py. Nenhum segredo é exposto.
        _oferta_app.app._get_connection = _oferta_app._get_connection
        _oferta_app.app._save_connection = _oferta_app._save_connection

        import meli_auto as _meli_auto
        _meli_auto.install(_oferta_app.app)
        print("[SITE] OFERTA IA V10.8 + Mercado Livre automático ativados", flush=True)
    except Exception as exc:
        print(
            f"[SITE][AVISO] Patches automáticos não puderam ser ativados: {type(exc).__name__}: {exc}",
            flush=True,
        )
