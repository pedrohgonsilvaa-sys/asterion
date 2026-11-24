"""Bloco 4: tela de Vitória da Caçada (UI v1.6.2, 47.3) com resultado real do serviço."""

import pytest

from asterion.bot.road_ui import render_road
from asterion.domain.road import creature_for
from tests.helpers.pvpve import start_manual_hunt_after_no_match
from tests.test_bosque_integration import _seed_bosque, _terminal


@pytest.mark.asyncio
async def test_real_hunt_victory_screen_and_back_to_hunt_screen(database, monkeypatch):
    import asterion.application.road as road_module

    actor = 998477
    _, service, _ = await _seed_bosque(database, actor, level=5)
    monkeypatch.setattr(
        road_module, "select_creature", lambda *_a, **_k: creature_for("carnical_fuligem")
    )
    combat = await start_manual_hunt_after_no_match(service, actor, monkeypatch)
    monkeypatch.setattr(road_module, "act", _terminal("victory"))
    victory = await service.action(actor, combat.activity_id, combat.combat.version, "attack")
    assert victory.kind == "hunt_victory"

    screen = render_road(victory)
    first, second, *rest = screen.text.split("\n")
    assert first == f"🏆 Vitória · {victory.creature}"
    assert second == "Bosque Calcinado · Terras do Ocaso"
    assert "Caçada concluída" not in screen.text
    assert ("🎁 Recompensas" in rest) == bool(victory.reward_lines)
    back = screen.keyboard.inline_keyboard[-1][0]
    assert (back.text, back.callback_data) == (
        "← Caçada",
        f"road:hunt_screen:{victory.activity_id.hex}",
    )

    # O que o handler de [← Caçada] faz: confirma o resultado e abre a tela de Caçada.
    await service.acknowledge_result(actor)
    prepare = await service.prepare_hunt(actor)
    assert prepare is not None and prepare.kind == "hunt_prepare"
    assert prepare.location == "Bosque Calcinado"
    assert render_road(prepare).text.startswith("🦌 Caçada")
    assert (await service.resume(actor)).kind != "hunt_victory"
