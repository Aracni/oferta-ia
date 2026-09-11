"""V11.10.14 — correção estrutural final da UI de Marketplace.

O patch V11.10.13 validava a presença do seletor no HTML, mas o log mostrou
que a âncora opportunityNiche não foi encontrada naquele momento e o seletor
acabou no fallback antes de </body>. Este módulo apenas move o seletor já
existente para dentro do formulário de Oportunidades. Não usa middleware,
MutationObserver, polling ou alteração de rota.
"""
import re


def install(app):
    global HTML

    html = globals().get("HTML")
    if not isinstance(html, str):
        raise RuntimeError("V11.10.14: HTML da aplicação não encontrado")

    # Captura exatamente o seletor já criado pelo patch anterior, incluindo o
    # script que o acompanha, para poder reposicioná-lo sem duplicação.
    pattern = r'<div id="oferta-market-filter"[\s\S]*?</script>\s*'
    match = re.search(pattern, html, count=1)
    if not match:
        raise RuntimeError("V11.10.14: seletor oferta-market-filter não encontrado")

    block = match.group(0).strip() + "\n"
    html = html[:match.start()] + html[match.end():]

    # Primeiro tentamos a âncora exata do campo. Mantemos variantes com aspas
    # simples/duplas e uma busca estrutural dentro da seção para sobreviver a
    # pequenas mudanças de formatação do HTML congelado.
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
        # Fallback estrutural: localiza a seção de Oportunidades e seu primeiro
        # formulário, em vez de jogar o seletor no final do documento.
        section = re.search(
            r'<section[^>]*id=["\']opportunitySection["\'][^>]*>[\s\S]*?<div[^>]*class=["\']form["\'][^>]*>',
            html,
            flags=re.IGNORECASE,
        )
        if not section:
            raise RuntimeError("V11.10.14: seção/formulário de Oportunidades não encontrado")
        pos = section.end()
        html = html[:pos] + "\n" + block + html[pos:]
        location = "dentro do formulário de Oportunidades"

    HTML = html

    count = HTML.count('id="oferta-market-filter"')
    niche = HTML.find('id="opportunityNiche"')
    selector = HTML.find('id="oferta-market-filter"')
    opportunity = HTML.find('id="opportunitySection"')
    if count != 1:
        raise RuntimeError(f"V11.10.14: seletor duplicado/ausente: {count}")
    if niche < 0 or opportunity < 0 or selector < opportunity:
        raise RuntimeError("V11.10.14: seletor não ficou dentro da seção de Oportunidades")

    print(f"[V11.10.14] seletor Marketplace reposicionado {location} | seção Oportunidades", flush=True)
