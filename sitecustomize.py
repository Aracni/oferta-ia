"""Carrega o patch V10.6 automaticamente no boot do Python/Render."""
try:
    import app as _oferta_app
    import v106_patch as _v106
    _v106.install(_oferta_app)
except Exception:
    # Nunca impedir o boot do OFERTA IA por causa do patch.
    pass
