"""Boot resiliente do OFERTA IA."""
import os
import pathlib
import time
import urllib.request
from fastapi.responses import JSONResponse
from starlette.requests import Request
import app as oferta_app
import v106_patch

v106_patch.install(oferta_app.app)
try:
    import supabase_secret_compat_v1
    supabase_secret_compat_v1.install(oferta_app)
    print("[BOOT] compatibilidade Supabase sb_secret_* carregada", flush=True)
except Exception as exc:
    print(f"[BOOT][WARN] compatibilidade Supabase: {type(exc).__name__}: {str(exc)[:300]}", flush=True)

o ferta_app.app._get_connection = oferta_app._get_connection
