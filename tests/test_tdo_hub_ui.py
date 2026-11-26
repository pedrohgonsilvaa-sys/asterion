"""Bloco A (Navegacao) da TdO v1.0.18: telas do hub (UI v1.6.1, secao 66) e regras puras."""

from uuid import uuid4

from asterion.application.road import (
    BOSQUE,
    CAMARA,
    CHARNECA,
    REFUGE,
    ROAD,
    RUINS,
    RoadView,
)
from asterion.application.tdo_explore import ExploreResult
from asterion.bot.road_ui import render_current_local
from asterion.bot.tdo_hub_ui import render_explore_result, render_hunt_choice
from asterion.bot.world_ui import render_refuge_dashboard
from asterion.domain.tdo_explore import (
    BOSQUE_LOCATION_ID,
    CAMARA_LOCATION_ID,
    CHARNECA_LOCATION_ID,
    RUINS_LOCATION_ID,
)
from asterion.domain.tdo_hub import (
    TEXTO_CAMARA_DESCOBERTA,
    TEXTO_CAMARA_POS_P6,
    TEXTO_CAMARA_PRE_P6,
    camara_entry_text,
    hub_destinations,
    hunt_choices,
    is_hub_step,
)


def _callbacks(screen):
    return [b.callback_data for row in screen.keyboard.inline_keyboard for b in row]


def _texts(screen):
    return [b.text for row in screen.keyboard.inline_keyboard for b in row]


def _view(kind, location, **kwargs):
    return RoadView(kind, uuid4(), location, **kwargs)


ALL_IDS = (CHARNECA_LOCATION_ID, BOSQUE_LOCATION_ID, RUINS_LOCATION_ID, CAMARA_LOCATION_ID)


# --- regras puras -----------------------------------------------------------


def test_hub_destinations_are_star_shaped():
    assert hub_destinations(REFUGE, ()) == (ROAD,)
    assert hub_destinations(REFUGE, ALL_IDS) == (ROAD, CHARNECA, BOSQUE, RUINS, CAMARA)
    for local in (ROAD, CHARNECA, BOSQUE, RUINS, CAMARA):
        assert hub_destinations(local, ALL_IDS) == (REFUGE,)
    assert hub_destinations("Mata Suspensa", ALL_IDS) == ()


def test_is_hub_step_rejects_local_to_local():
    assert is_hub_step(REFUGE, CHARNECA) and is_hub_step(CAMARA, REFUGE)
    assert not is_hub_step(CHARNECA, BOSQUE)
    assert not is_hub_step(BOSQUE, RUINS)
    assert not is_hub_step(REFUGE, REFUGE)


def test_hunt_choices_exclude_camara_and_undiscovered():
    assert hunt_choices(()) == (ROAD,)
    assert hunt_choices((CAMARA_LOCATION_ID,)) == (ROAD,)
    assert hunt_choices((RUINS_LOCATION_ID, CHARNECA_LOCATION_ID)) == (ROAD, CHARNECA, RUINS)
    assert hunt_choices(ALL_IDS) == (ROAD, CHARNECA, BOSQUE, RUINS)


def test_camara_texts_match_source_and_markers_never_leak():
    assert "Âncora" not in TEXTO_CAMARA_PRE_P6
    assert "Âncora" not in TEXTO_CAMARA_DESCOBERTA
    assert "Âncora do Poente" in TEXTO_CAMARA_POS_P6
    assert camara_entry_text(False) == TEXTO_CAMARA_PRE_P6
    assert camara_entry_text(True) == TEXTO_CAMARA_POS_P6
    assert TEXTO_CAMARA_DESCOBERTA == "Entre as pedras do Poente há um recinto fechado."
    for text in (TEXTO_CAMARA_PRE_P6, TEXTO_CAMARA_POS_P6, TEXTO_CAMARA_DESCOBERTA):
        assert "[[" not in text


# --- tela do Refugio --------------------------------------------------------


def test_refuge_screen_shows_hub_actions_and_discovered_locals_only():
    view = _view("refuge", REFUGE, route_available=True, route_destinations=(ROAD, CHARNECA))
    screen = render_current_local(view, explore_remaining=3, mission_available=True)
    callbacks = _callbacks(screen)
    assert "tdo:explore" in callbacks and "tdo:hunt" in callbacks
    assert "dungeon:known" in callbacks
    assert "world:missions" in callbacks
    assert "road:route:road" in callbacks and "road:route:charneca" in callbacks
    assert "road:route:bosque" not in callbacks
    assert "road:route:ruinas" not in callbacks
    assert "road:route:camara" not in callbacks
    # Sem Travessia dos Braseiros / mapa de viagem nas Terras do Ocaso.
    assert not any("world:travel" in value for value in callbacks)
    assert "world:map:fromlocal" not in callbacks
    assert "Travessia" not in screen.text


def test_refuge_dashboard_has_regional_and_global_actions_without_campaign_adventure():
    from asterion.application.world import WorldView

    view = WorldView(
        kind="menu",
        character_id=uuid4(),
        name="Heroa",
        race="remanescente",
        character_class="sentinela",
        hp=100,
        max_hp=100,
        vigor=100,
        max_vigor=100,
        xp=0,
        region="Terras do Ocaso",
        location=REFUGE,
        quest_title=None,
    )
    screen = render_refuge_dashboard(
        view,
        route_destinations=(ROAD, CHARNECA),
        explore_remaining=2,
        can_hunt=True,
        known_dungeons=True,
    )
    callbacks = _callbacks(screen)
    labels = _texts(screen)
    # Decisão do autor: Caçadas e Masmorras saem do Menu Principal (Masmorras entram
    # pelo Desbravar).
    assert {"tdo:explore", "world:map", "wev:hub"} <= set(callbacks)
    assert "tdo:hunt" not in callbacks and "dungeon:known" not in callbacks
    # Contrato Mestre de Telas UI v1.0.0 §5: Missões entram pelo Mural do Refúgio.
    assert "world:missions" not in callbacks
    assert {
        "character:root",
        "guild:root",
        "mkt:root",
        "pvp:hub",
        "bn:root",
        "community:open",
    } <= set(callbacks)
    assert "⛰️ Desbravar" in labels and "(Covil)" not in labels
    assert "Campanha" not in labels and "Aventura" not in labels


def test_refuge_local_offers_desbravar_without_reveal_status():
    """Todos os Locais nascem descobertos: o Refúgio leva ao menu Desbravar."""
    view = _view("refuge", REFUGE, route_destinations=(ROAD,))
    screen = render_current_local(view, explore_remaining=0)
    assert "tdo:explore" in _callbacks(screen)
    assert "Não há mais o que explorar" not in screen.text
    assert "Revela um Local" not in screen.text


def test_refuge_hunt_button_hidden_without_hunt_local():
    view = _view("refuge", REFUGE, route_destinations=(CAMARA,))
    assert "tdo:hunt" not in _callbacks(render_current_local(view, explore_remaining=1))


# --- Cacar no Refugio -------------------------------------------------------


def test_hunt_choice_lists_only_discovered_hunt_locals():
    screen = render_hunt_choice((ROAD, CHARNECA, RUINS, CAMARA))
    callbacks = _callbacks(screen)
    assert callbacks[:3] == ["road:route:road", "road:route:charneca", "road:route:ruinas"]
    assert "road:route:camara" not in callbacks
    assert "road:route:bosque" not in callbacks
    assert not any("Câmara" in text for text in _texts(screen))


# --- tela do Local ----------------------------------------------------------


def test_local_screen_has_hunt_explore_round_and_back_to_refuge():
    view = _view(
        "bosque",
        BOSQUE,
        hunt_enabled=True,
        explore_enabled=True,
        familiar=True,
        route_available=True,
        route_destinations=(REFUGE,),
    )
    screen = render_current_local(view, explore_state="available")
    callbacks = _callbacks(screen)
    assert {"road:hunt", "road:explore:start", "world:round", "road:route:refuge"} <= set(callbacks)
    assert "Voltar ao Refúgio" in _texts(screen)
    # Nenhuma ida direta Local-Local.
    for other in ("road:route:charneca", "road:route:ruinas", "road:route:camara"):
        assert other not in callbacks


def test_local_screen_hides_round_until_released():
    view = _view(
        "ruinas",
        RUINS,
        hunt_enabled=True,
        explore_enabled=True,
        familiar=False,
        route_destinations=(REFUGE,),
    )
    screen = render_current_local(view)
    assert "world:round" not in _callbacks(screen)
    assert "road:route:refuge" in _callbacks(screen)


# --- Camara -----------------------------------------------------------------


def test_camara_screen_pre_p6_exact_text_without_ancora_and_only_back():
    view = _view(
        "camara", CAMARA, hunt_enabled=False, explore_enabled=False, route_destinations=(REFUGE,)
    )
    screen = render_current_local(view)
    assert screen.text == f"🏛️ Câmara do Poente\n\n{TEXTO_CAMARA_PRE_P6}"
    assert "Âncora" not in screen.text
    assert _callbacks(screen) == ["road:route:refuge"]
    assert _texts(screen) == ["Voltar ao Refúgio"]


def test_camara_screen_post_p6_exact_text_with_ancora():
    view = _view(
        "camara",
        CAMARA,
        hunt_enabled=False,
        explore_enabled=False,
        route_destinations=(REFUGE,),
        camara_p6_completed=True,
    )
    screen = render_current_local(view)
    assert screen.text == f"🏛️ Câmara do Poente\n\n{TEXTO_CAMARA_POS_P6}"
    assert "Âncora do Poente" in screen.text
    assert _callbacks(screen) == ["road:route:refuge"]
    for forbidden in ("road:hunt", "road:explore:start", "world:round"):
        assert forbidden not in _callbacks(screen)


def test_camara_discovery_result_is_neutral():
    discovered = ExploreResult(
        "discovered", location_id=CAMARA_LOCATION_ID, label=CAMARA, xp=120, camara_codex=True
    )
    screen = render_explore_result(discovered)
    assert TEXTO_CAMARA_DESCOBERTA in screen.text
    assert "Âncora" not in screen.text
    assert "<code>120 XP</code>" in screen.text and "agora é conhecida" in screen.text
    assert "Vigor" not in screen.text


def test_explore_result_other_states_use_source_texts():
    assert "Aguarde um instante." in render_explore_result(ExploreResult("cooldown")).text
    assert (
        "Não há mais o que explorar por aqui."
        in render_explore_result(ExploreResult("unavailable")).text
    )
    shown = render_explore_result(
        ExploreResult("discovered", location_id=CHARNECA_LOCATION_ID, label=CHARNECA, xp=120)
    )
    assert "Charneca da Fuligem" in shown.text and "agora é conhecida" in shown.text
    assert TEXTO_CAMARA_DESCOBERTA not in shown.text
