"""Inicialização explícita do OFERTA IA."""
import os
import app as oferta_app
import v106_patch

v106_patch.install(oferta_app.app)

oferta_app.app._get_connection = oferta_app._get_connection
oferta_app.app._save_connection = oferta_app._save_connection

import meli_auto
meli_auto.install(oferta_app.app)

import meli_fast
meli_fast.install(oferta_app.app)

# A interface Marketplace agora é montada diretamente no HTML pelo
# ml_enrichment_v2.py. Não interceptamos nem reconstruímos a rota /.
print('[V11.10.11] boot estável; sem wrapper ASGI da rota raiz', flush=True)

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        oferta_app.app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "10000")),
    )
