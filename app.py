"""OFERTA IA V11.11.
Loader determinístico do núcleo V11.9; os patches de runtime são instalados
pelo boot.py depois que todas as rotas-base estiverem montadas.
"""
import time
import urllib.request

_BASE = "https://raw.githubusercontent.com/Aracni/oferta-ia/639b53c7e97152b2756e70eef2940454ae3420d7/app.py"


def _load_remote(url, label):
    last_error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                return response.read().decode("utf-8")
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(1.0 * (attempt + 1))
    raise RuntimeError(f"Não foi possível carregar {label} do OFERTA IA: {last_error}") from last_error


source = _load_remote(_BASE, "o núcleo V11.9")
exec(compile(source, _BASE, "exec"), globals(), globals())

print('[V11.11] núcleo carregado; patches de runtime serão instalados pelo boot', flush=True)
