from uuid import uuid4

from asterion.application.p1 import P1View
from asterion.bot.p1_ui import render_p1


def view(step, *, progress=None, status="active", locations=()):
    return P1View(uuid4(), step, 4, progress or {}, status=status, known_locations=locations)


def test_p1_official_step_screens_and_callbacks():
    first = render_p1(view(1))
    assert "A chama deixada para trás desaparece" in first.text
    assert "🎯 Objetivo · Seguir pela Estrada das Cinzas" in first.text
    assert "Seguir pela Estrada" in first.text
    tracks = render_p1(view(2))
    assert "Marcas de botas cortam a fuligem" in tracks.text
    assert "0/2" in tracks.text
    furrows = render_p1(view(2, progress={"pegadas": True}))
    assert "🛞 Sulcos Recentes" in furrows.text
    assert "〰️ Sulcos Recentes" not in furrows.text
    assert "Duas marcas estreitas atravessam a cinza" in furrows.text
    assert "1/2" in furrows.text


def test_p1_defeat_is_italic_and_recovery_action():
    screen = render_p1(view(3, progress={"defeat": True}))
    assert "<i>Recuperado no Braseiro" in screen.text
    labels = [button.text for row in screen.keyboard.inline_keyboard for button in row]
    assert "Retornar à Estrada" in labels
    assert "← Menu" in labels


def test_p1_completed_screen_has_rest_and_never_activate():
    screen = render_p1(view(7, status="completed"))
    assert "🔥 Braseiro · Descoberto" in screen.text
    assert "❤️ Descansar · Restaura HP" in screen.text
    assert "✅ Vozes na Estrada · Concluída" in screen.text
    assert "Descansar" in [b.text for row in screen.keyboard.inline_keyboard for b in row]
    assert "← Menu" in [b.text for row in screen.keyboard.inline_keyboard for b in row]
    assert "Ativar Braseiro" not in screen.text


def test_p1_refuge_and_dialogue_screens_are_official():
    assert "Mais adiante, a estrada deixa de ser apenas ruína" in render_p1(view(4)).text
    assert "— Se chegou até aqui sozinho" in render_p1(view(5)).text
    assert "— Se ouvir nomes no vento" in render_p1(view(6)).text
    assert "🎯 Objetivo · Ativar o Braseiro do Refúgio" in render_p1(view(7)).text
