"""OFERTA IA — compatibilidade com chaves secretas novas do Supabase.

As novas chaves sb_secret_* são opacas e devem chegar ao Data API pelo
header `apikey`, não como `Authorization: Bearer ...`. O supabase-py de
algumas versões pode deixar a chave também no Authorization, fazendo o
PostgREST tentar interpretá-la como JWT e gerar PGRST303.
"""


def install(app_module):
    key = str(
        getattr(app_module, "SUPABASE_KEY", None)
        or getattr(app_module, "SUPABASE_SECRET_KEY", None)
        or ""
    ).strip()
    if not key.startswith("sb_secret_"):
        print("[SUPABASE_COMPAT] chave legacy ou ausente; nenhuma alteração necessária", flush=True)
        return False

    client = getattr(app_module, "supabase", None)
    postgrest = getattr(client, "postgrest", None)
    session = getattr(postgrest, "session", None)
    headers = getattr(session, "headers", None)
    if headers is None:
        print("[SUPABASE_COMPAT][WARN] sessão PostgREST não encontrada", flush=True)
        return False

    headers["apikey"] = key
    # A secret key nova NÃO é JWT. Se permanecer aqui, o PostgREST tenta
    # validar a chave como Bearer e pode retornar PGRST303/JWT issued at future.
    try:
        headers.pop("Authorization", None)
    except Exception:
        pass

    print("[SUPABASE_COMPAT] sb_secret_* configurada como apikey (Authorization removido)", flush=True)
    return True
