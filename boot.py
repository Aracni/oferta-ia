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

# Última etapa da UI: move o seletor já existente para dentro do formulário
# de Oportunidades, sem middleware nem alteração da rota raiz.
import ui_fix
ui_fix.install(oferta_app)

print('[V11.11] boot estável; enriquecimento ML V11.11 + UI Marketplace ativa', flush=True)

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        oferta_app.app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "10000")),
    )
