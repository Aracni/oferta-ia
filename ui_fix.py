"""V11.11.2 — correção estrutural final da UI de Marketplace.

Garante um único seletor Marketplace dentro do formulário de Oportunidades.
Não usa middleware, MutationObserver, polling ou alteração da rota.
"""
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


def install(app):
    html = getattr(app, "HTML", None)
    if not isinstance(html, str):
        raise RuntimeError("V11.11.2: HTML da aplicação não encontrado")

    # Remova qualquer versão antiga do seletor para garantir exatamente uma.
    html = re.sub(r'<div id="(?:oferta-market-filter|v119-market-filter)"[\s\S]*?</script>\s*', '', html, flags=re.IGNORECASE)

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
        section = re.search(r'<section[^>]*id=["\']opportunitySection["\'][^>]*>', html, flags=re.IGNORECASE)
        if not section:
            raise RuntimeError("V11.11.2: seção de Oportunidades não encontrada")
        form = re.search(r'<div[^>]*class=["\']form["\'][^>]*>', html[section.end():], flags=re.IGNORECASE)
        pos = section.end() + (form.start() if form else 0)
        html = html[:pos] + "\n" + block + html[pos:]
        location = "dentro da seção de Oportunidades"

    app.HTML = html

    count = app.HTML.count('id="oferta-market-filter"')
    opportunity = app.HTML.find('id="opportunitySection"')
    selector = app.HTML.find('id="oferta-market-filter"')
    niche = app.HTML.find('id="opportunityNiche"')
    if count != 1:
        raise RuntimeError(f"V11.11.2: seletor duplicado/ausente: {count}")
    if opportunity < 0 or selector < opportunity:
        raise RuntimeError("V11.11.2: seletor não ficou na seção de Oportunidades")
    if niche >= 0 and selector > niche:
        raise RuntimeError("V11.11.2: seletor não ficou antes dos campos de Oportunidades")

    print(f"[V11.11.2] seletor Marketplace garantido {location} | único e dentro de Oportunidades", flush=True)
