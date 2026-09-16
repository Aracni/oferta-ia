"""OFERTA IA V12.9 — diagnóstico OAuth sob demanda, nunca no boot."""
import threading

_LOCK = threading.Lock()
_DONE = False


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
                                    f"record={result.get('connection_record')} "
                                    f"token={result.get('access_token_present')} "
                                    f"refresh={result.get('refresh_token_present')} "
                                    f"users_me={status('user')} app={status('application')} grants={status('grants')}",
                                    flush=True,
                                )
                                for name in ("user", "application", "grants"):
                                    part = result.get(name) or {}
                                    if part.get("status", 0) >= 400:
                                        print(f"[V12.9] OAuth ML {name}: status={part.get('status')} error={part.get('error')}", flush=True)
                        except Exception as exc:
                            print(f"[V12.9][WARN] OAuth sob demanda: {type(exc).__name__}: {str(exc)[:240]}", flush=True)
                        finally:
                            _DONE = True
            return await call_next(request)
        print("[V12.9] diagnóstico OAuth sob demanda instalado", flush=True)
    except Exception as exc:
        print(f"[V12.9][WARN] instalação: {type(exc).__name__}: {str(exc)[:240]}", flush=True)
