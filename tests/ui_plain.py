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
