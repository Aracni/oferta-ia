"""V11.11.5 — UI do seletor + diagnóstico legível de erros HTTP."""
import re

_SELECTOR = r'''<div id="oferta-market-filter" style="margin:10px 0;padding:10px;border:1px solid rgba(255,255,255,.12);border-radius:10px">
  <strong>Marketplace</strong>
  <label style="margin-left:12px"><input type="radio" name="oferta_marketplace" value="both"> Ambos — padrão</label>
  <label style="margin-left:12px"><input type="radio" name="oferta_marketplace" value="mercadolivre"> Mercado Livre</label>
  <label style="margin-left:12px"><input type="radio" name="oferta_marketplace" value="shopee"> Shopee</label>
</div>
<script>
(function(){
  const key = "oferta_marketplace";
  function selected(){
    const el = document.querySelector('input[name="oferta_marketplace"]:checked');
    return el ? el.value : (localStorage.getItem(key) || "both");
  }
  function apply(){
    const value = localStorage.getItem(key) || "both";
    document.querySelectorAll('input[name="oferta_marketplace"]').forEach(function(el){el.checked = el.value === value;});
  }
  document.querySelectorAll('input[name="oferta_marketplace"]').forEach(function(el){
    el.addEventListener("change", function(){localStorage.setItem(key, el.value);});
  });
  apply();
  const originalFetch = window.fetch;
  if (!window.__ofertaMarketplaceFetchWrapped) {
    window.__ofertaMarketplaceFetchWrapped = true;
    window.fetch = function(input, init){
      try {
        const url = typeof input === "string" ? input : (input && input.url) || "";
        if (url.includes("/api/opportunities-central") && init && init.body && typeof init.body === "string") {
          const body = JSON.parse(init.body);
          body.marketplaces = selected();
          init = Object.assign({}, init, {body: JSON.stringify(body)});
        }
      } catch(e) {}
      return originalFetch.call(this, input, init);
    };
  }
})();
</script>
'''

_ERROR_HELPER = r'''<script>
(function(){
  // O núcleo antigo fazia Error(d.detail). Quando detail é objeto/array,
  // o navegador transforma isso em "[object Object]". Mostramos o conteúdo real.
  window.ofertaFormatError = function(detail, status){
    if (typeof detail === "string" && detail.trim()) return detail;
    if (detail && typeof detail === "object") {
      if (typeof detail.message === "string" && detail.message.trim()) return detail.message;
      if (typeof detail.error === "string" && detail.error.trim()) return detail.error;
      try { return JSON.stringify(detail); } catch(e) {}
    }
    return "HTTP " + status + " — erro inesperado";
  };
  window.jsonFetch = async function(url, opts={}){
    const r = await fetch(url, opts);
    let d = {};
    try { d = await r.json(); } catch(e) {}
    if (!r.ok) throw Error(window.ofertaFormatError(d && d.detail, r.status));
    return d;
  };
})();
</script>
'''


def install(app):
    html = getattr(app, "HTML", None)
    if not isinstance(html, str):
        raise RuntimeError("V11.11.5: HTML da aplicação não encontrado")

    html = re.sub(
        r'<div id="(?:oferta-market-filter|v119-market-filter)"[\s\S]*?</script>\s*',
        '',
        html,
        flags=re.IGNORECASE,
    )

    block = _SELECTOR.strip() + "\n"
    anchors = [
        r'<input\s+id=["\']opportunityNiche["\'][^>]*>',
        r'<input[^>]*\bid=["\']opportunityNiche["\'][^>]*>',
    ]
    anchor = None
    for expr in anchors:
        anchor = re.search(expr, html, flags=re.IGNORECASE)
        if anchor:
            break

    if anchor:
        html = html[:anchor.start()] + block + html[anchor.start():]
        location = "antes de opportunityNiche"
    else:
        section = re.search(
            r'<section[^>]*id=["\']opportunitySection["\'][^>]*>',
            html,
            flags=re.IGNORECASE,
        )
        if not section:
            raise RuntimeError("V11.11.5: seção de Oportunidades não encontrada")
        form = re.search(
            r'<div[^>]*class=["\']form["\'][^>]*>',
            html[section.end():],
            flags=re.IGNORECASE,
        )
        pos = section.end() + (form.start() if form else 0)
        html = html[:pos] + "\n" + block + html[pos:]
        location = "dentro da seção de Oportunidades"

    # O helper fica no fim do HTML para substituir a função global jsonFetch
    # depois que o script original a declarou.
    if "window.ofertaFormatError" not in html:
        body = html.lower().rfind("</body>")
        if body >= 0:
            html = html[:body] + _ERROR_HELPER + "\n" + html[body:]
        else:
            html += "\n" + _ERROR_HELPER

    app.HTML = html

    count = app.HTML.count('id="oferta-market-filter"')
    opportunity = app.HTML.find('id="opportunitySection"')
    selector = app.HTML.find('id="oferta-market-filter"')
    niche = app.HTML.find('id="opportunityNiche"')
    if count != 1:
        raise RuntimeError(f"V11.11.5: seletor duplicado/ausente: {count}")
    if opportunity < 0 or selector < opportunity:
        raise RuntimeError("V11.11.5: seletor não ficou na seção de Oportunidades")
    if niche >= 0 and selector > niche:
        raise RuntimeError("V11.11.5: seletor não ficou antes dos campos de Oportunidades")

    print(f"[V11.11.5] seletor Marketplace + diagnóstico de erro legível | {location}", flush=True)
