"""Texto de tela como o jogador lê: sem as tags HTML do Telegram."""

import re
from html import unescape

_TAG = re.compile(r"<[^>]+>")


def plain(text: str) -> str:
    return unescape(_TAG.sub("", text))


def art_choices_text(view, doctrine, slot: int) -> str:
    """Texto de todas as páginas da escolha de Arte de uma Doutrina."""
    from asterion.bot.doctrines_ui import ART_CHOICES_PER_PAGE, doctrine_art_ids, render_art_choices

    pages = max(1, -(-len(doctrine_art_ids(view, doctrine)) // ART_CHOICES_PER_PAGE))
    return "\n".join(
        plain(render_art_choices(view, doctrine, slot, page).text) for page in range(pages)
    )


def doctrine_talent_choices(view, doctrine) -> str:
    """Talentos que a Doutrina pode escolher (✨) ou já escolheu (✅), nas duas páginas."""
    from asterion.bot.doctrines_ui import TALENT_LOCKED, render_talent_page

    lines = []
    for page in (0, 1):
        for line in plain(render_talent_page(view, doctrine, page).text).splitlines():
            if line[:1] in {"✨", "✅"} and not line.startswith(TALENT_LOCKED):
                lines.append(line)
    return "\n".join(lines)
