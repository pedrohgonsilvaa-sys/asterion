from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from asterion.domain.arts import active_art_definition
from asterion.domain.road import materialize_equipment
from asterion.domain.weapon_metadata import WEAPON_DEFINITIONS
from asterion.infrastructure.db.models import (
    CharacterEquipmentSlot,
    EquipmentItem,
)


async def add_compatible_weapon_for_arts(
    session: AsyncSession,
    character_id,
    art_ids: tuple[str, ...],
) -> str | None:
    requirements = tuple(
        definition.weapon_requirement
        for art_id in art_ids
        if (definition := active_art_definition(art_id)) is not None
        and definition.weapon_requirement
    )
    if not requirements:
        return None

    weapon = next(
        (
            definition
            for definition in WEAPON_DEFINITIONS.values()
            if all(
                requirement & definition.compatibility_tags
                for requirement in requirements
            )
        ),
        None,
    )
    if weapon is None:
        raise AssertionError(
            "No canonical test weapon satisfies the Arts' published requirements."
        )

    item_id = uuid4()
    payload = materialize_equipment(
        f"test-weapon:{character_id}:{item_id}",
        "Comum",
        1,
        weapon_type_id=weapon.weapon_type_id,
    )
    payload["core"] = {"ATQ": "0"}
    payload["secondaries"] = []
    payload["item_instance_id"] = str(item_id)
    session.add(
        EquipmentItem(
            id=item_id,
            character_id=character_id,
            source_key=f"test:weapon:{character_id}:{item_id}",
            item_name=weapon.item_name,
            rarity="Comum",
            slot=weapon.persisted_item_slot,
            item_level=1,
            bound=False,
            payload=payload,
        )
    )
    await session.flush()
    equipped_slot = (
        "Principal"
        if weapon.persisted_item_slot == "2H"
        else weapon.persisted_item_slot
    )
    session.add(
        CharacterEquipmentSlot(
            character_id=character_id,
            slot=equipped_slot,
            equipment_item_id=item_id,
        )
    )
    return weapon.weapon_type_id


# Proficiências v1.0.0: weapons equipped through the authoritative services need a
# canonical identity. Defaults below are all inside the Sentinela whitelist.
DEFAULT_TEST_WEAPON_TYPE_IDS = {
    "Principal": "weapon.type.base.espada",
    "Arma Principal": "weapon.type.base.espada",
    "Secundária": "weapon.type.tdo.guarda_caminhante",
    "2H": "weapon.type.base.espada_de_guerra",
}


def all_proficiency_rows(character_id):
    """Every family, so pre-Proficiência tests are gated only by the Classe whitelist."""
    from asterion.domain.weapon_proficiency import ProficiencyFamily
    from asterion.infrastructure.db.models import CharacterWeaponProficiency

    return [
        CharacterWeaponProficiency(
            character_id=character_id,
            family=family.value,
            ordinal=ordinal,
            source="initial" if ordinal == 1 else "trainer",
            cost_crowns=0,
        )
        for ordinal, family in enumerate(ProficiencyFamily, start=1)
    ]
