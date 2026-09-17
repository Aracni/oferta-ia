"""OFERTA IA V12.9 + V13 — diagnóstico OAuth sob demanda e fonte autorizada de vendas."""
import threading
import urllib.request

_LOCK = threading.Lock()
_DONE = False
_V13_URL = "https://raw.githubusercontent.com/Aracni/oferta-ia/c34c8dc7f72f28ab8d5eaa999159d56b16873b27/ml_authorized_sales_v13.py"


def _load_v13():
    try:
        with urllib.request.urlopen(_V13_URL, timeout=20) as response:
            source = response.read().decode("utf-8")
        exec(compile(source, _V13_URL, "exec"), globals(), globals())
        return globals().get("install")
    except Exception as exc:
        print(f"[V13][WARN] carregamento da fonte autorizada: {type(exc).__name__}: {str(exc)[:260]}", flush=True)
        return None


def install(app):
    try:
        from starlette.requests import Request

        @app.middleware("http")
        async def _meli_runtime_probe(request: Request, call_next):
            global _DONE
            path = request.url.path
            if path == "/api/opportunities-central" and not _DONE:
                with _LOCK:
                    if not _DONE:
                        try:
                            runner = globals().get("_run_probe")
                            if callable(runner):
                                result = runner()
                                def status(name):
                                    part = result.get(name) or {}
                                    return part.get("status")
                                print(
                                    "[V12.9] OAuth ML sob demanda: "
                                    f"record={result.get('connection_record')} token={result.get('access_token_present')} "
                                    f"refresh={result.get('refresh_token_present')} users_me={status('user')} "
                                    f"app={status('application')} grants={status('grants')}", flush=True,
                                )
                        except Exception as exc:
                            print(f"[V12.9][WARN] OAuth sob demanda: {type(exc).__name__}: {str(exc)[:240]}", flush=True)
                        finally:
                            _DONE = True
            return await call_next(request)
        print("[V12.9] diagnóstico OAuth sob demanda instalado", flush=True)

        installer = _load_v13()
        if callable(installer):
            installer(app)
            print("[BOOT] fonte autorizada de vendas V13 instalada", flush=True)
    except Exception as exc:
        print(f"[V12.9][WARN] instalação: {type(exc).__name__}: {str(exc)[:240]}", flush=True)
