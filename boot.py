"""Inicializacao explicita do OFERTA IA com patch V10.6."""
import os
import app as oferta_app
import v106_patch

v106_patch.install(oferta_app)

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        oferta_app.app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "10000")),
    )
