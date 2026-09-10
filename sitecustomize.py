"""Inicialização automática do OFERTA IA.

O Render pode iniciar diretamente com `uvicorn app:app`, sem executar boot.py.
Quando PORT está presente, o app é carregado e o patch V10.8 é instalado antes
que o uvicorn reutilize o módulo já carregado.
"""
import os

if os.environ.get("PORT"):
    try:
        import app as _oferta_app
        import v106_patch as _v106
        _v106.install(_oferta_app)
        print("[SITE] OFERTA IA V10.8 ativado antes do uvicorn", flush=True)
    except Exception as exc:
        print(f"[SITE][AVISO] V10.8 não pôde ser ativado: {type(exc).__name__}: {exc}", flush=True)
