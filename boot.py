"""Inicialização explícita do OFERTA IA.

Use este arquivo no Start Command do Render para garantir que os patches
sejam instalados antes de o servidor HTTP começar a atender requisições.
"""
import os
import app as oferta_app
import v106_patch

# Motor central: Mercado Livre entra automaticamente nas oportunidades.
v106_patch.install(oferta_app.app)

# Disponibiliza os helpers internos de persistência ao módulo automático.
oferta_app.app._get_connection = oferta_app._get_connection
o ferta_app.app._save_connection = oferta_app._save_connection

# Renovação/validação automática do OAuth do Mercado Livre.
import meli_auto
meli_auto.install(oferta_app.app)

# V10.9 — evita que enriquecimento lento/bloqueado do Mercado Livre atrase o garimpo.
import meli_fast
meli_fast.install(oferta_app.app)

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        oferta_app.app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "10000")),
    )
