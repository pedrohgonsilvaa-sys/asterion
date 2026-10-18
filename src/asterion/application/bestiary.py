"""Shared persistence rules for creature discovery and Bestiary evidence."""

from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select

from asterion.application.progression import level_xp
from asterion.application.tdo_feats import reconcile_tdo_feats_for_character
from asterion.domain.road import creature_for
from asterion.infrastructure.db.models import (
    BestiaryEntry,
    BestiaryEvidence,
    Character,
    RewardComponent,
    RewardEvent,
)

BESTIARY_STAGE_LABELS = {
    "observed": "Observado",
    "known": "Conhecido",
    "studied": "Estudado",
    "dominated": "Dominado",
}

VDE_IMPORTANT_FIRST_VICTORY_XP = {
    "no_feroz": (14, 687),
    "viuva_cipos": (17, 876),
    "carrasco_casca": (20, 1086),
    "o_que_pende": (17, 876),
    "guardiao_no_antigo": (20, 1086),
}

VARZEAS_IMPORTANT_FIRST_VICTORY_XP = {
    "viuva_rubra": (37, 2718),
    "coletor_hematico": (40, 3084),
    "matriz_rubra": (40, 3084),
}
VARZEAS_BASE_CREATURES = frozenset(
    {
        "cao_salmoura", "garca_ferruginosa", "portador_rubro",
        "aranha_junco", "cervo_ferrugem", "lampreia_varzea",
        "enxerto_horto", "mariposa_soro", "vigia_hemaris",
    }
)

VDE_DISTINCTIVE_ELITE_MASTERY = {
    "custodio_enredado": {
        "first_victory",
        "action:egide_tomada",
        "action:marca_constritiva",
        "action:peso_no",
    },
    "prelado_enraizado": {
        "first_victory",
        "action:seiva_restritiva",
        "action:restabelecer_raiz",
    },
}

VARZEAS_DISTINCTIVE_ELITE_MASTERY = {
    "viuva_rubra": {
        "first_victory",
        "mechanic:poison",
        "action:teia_junco",
        "action:salto_agua",
    },
    "coletor_hematico": {
        "first_victory",
        "action:reservatorio_blindado",
        "action:marca_extracao",
        "action:extracao_forcada",
    },
    "curador_vazio": {
        "first_victory",
        "action:cauterizacao_inadequada",
        "action:placa_procedimento",
        "action:intervencao_brusca",
    },
    "condutor_rubro": {
        "first_victory",
        "action:linha_pressurizada",
        "action:descarga_fluxo",
        "action:fecho_seguranca",
    },
    "executor_hemaris": {
        "first_victory",
        "action:fixar_incidente",
        "action:resposta_emergencia",
        "action:imobilizacao_pesada",
    },
}

VARZEAS_DISTINCTIVE_BOSS_MASTERY = {
    "o_persistente": {
        "first_victory",
        "phase:persistencia",
        "phase:sem_alta",
        "action:protocolo_continuidade",
        "action:manutencao_repetida",
        "action:intervencao_final",
    },
    "coracao_transferencia": {
        "first_victory",
        "action:linha_aberta",
        "action:linha_fechada",
        "action:transferencia_final",
    },
    "matriz_rubra": {
        "first_victory",
        "p24_completed",
        "phase:persistencia",
        "phase:emergencia",
        "action:transferencia_externa",
        "action:regulacao_emergencia",
        "action:sobrecarga_matriz",
    },
    "custodio_quarentena": {
        "first_victory",
        "s24_completed",
        "action:rota_selada",
        "action:fecho_quarentena",
    },
}

NARETH_DISTINCTIVE_BOSS_MASTERY = {
    "custodio_sem_norte": {
        "first_victory",
        "action:rota_negada",
        "mechanic:queda_sem_norte_telegraph",
        "mechanic:queda_sem_norte_resolved",
    },
    "arconte_invertido": {
        "first_victory",
        "p18_completed",
        "phase:corrigir_o_que_permanece",
        "phase:a_medida_impossivel",
        "mechanic:eixo_carga_observado",
        "mechanic:eixo_guarda_observado",
        "mechanic:eixo_ritmo_observado",
        "action:protocolo_continuidade",
        "action:retificacao_final",
    },
    "o_que_retorna": {
        "first_victory",
        "phase:o_mesmo_trajeto",
        "phase:o_trajeto_fecha",
        "mechanic:marcos_retorno_observados",
        "action:colisao_recorrente",
        "mechanic:retorno_ao_marco_resolvido",
    },
    "guardiao_referencia": {
        "first_victory",
        "phase:corrigir_o_mundo",
        "phase:referencia_absoluta",
        "mechanic:eixos_calibracao_observados",
        "action:ancora_local",
        "action:referencia_absoluta",
    },
}

S30_DISTINCTIVE_BOSS_MASTERY = {
    "boss.altos.s30.custodio_ultimo_turno": {
        "first_victory",
        "action:ordem_vencida",
        "mechanic:ultimo_turno_telegraph",
    }
}

NARETH_DISTINCTIVE_ELITE_MASTERY = {
    "escavador_eixo": {
        "first_victory",
        "action:travar_trilho",
        "action:corte_canal",
        "action:broca_servico",
    },
    "custodio_meridiano": {
        "first_victory",
        "action:travar_referencia",
        "action:ajuste_forcado",
        "action:queda_prumo",
    },
    "preceptor_eixo": {
        "first_victory",
        "action:desvio_medido",
        "action:recalibrar_baliza",
    },
}


class BestiaryRecorder:
    """Record shared first-contact, evidence, victory, and stage semantics."""

    async def record(
        self,
        session,
        character_id,
        creature_id,
        *,
        victory=False,
        evidence_id=None,
        evidence_category=None,
        evidence_points=0,
        variant=None,
        elite=False,
        grant_observation_xp=False,
        observation_level=None,
        observation_category="common",
    ):
        before_evidence_ids = set(
            (
                await session.scalars(
                    select(BestiaryEvidence.evidence_id).where(
                        BestiaryEvidence.character_id == character_id,
                        BestiaryEvidence.creature_id == creature_id,
                    )
                )
            ).all()
        )
        first_observation_new = "first_observation" not in before_evidence_ids
        entry = await session.scalar(
            select(BestiaryEntry)
            .where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == creature_id,
            )
            .with_for_update()
        )
        if entry is None:
            entry = BestiaryEntry(
                character_id=character_id,
                creature_id=creature_id,
                bkp=0,
                wins=1 if victory else 0,
            )
            session.add(entry)
            previous_stage = None
        elif victory:
            previous_stage = entry.stage
            entry.wins += 1
        else:
            previous_stage = entry.stage

        for evidence, category, points in (
            ("first_observation", "observation", 4),
            ("first_combat", "combat", 3),
        ):
            if await self.add_evidence(
                session, entry, character_id, creature_id, evidence, category, points
            ):
                pass

        if first_observation_new and grant_observation_xp and observation_level is not None:
            await self._grant_observation_xp(
                session, character_id, creature_id, observation_level
            )
        if evidence_id:
            await self.add_evidence(
                session,
                entry,
                character_id,
                creature_id,
                evidence_id,
                evidence_category or evidence_id,
                evidence_points,
            )
        if variant:
            await self.add_evidence(
                session, entry, character_id, creature_id,
                f"variant:{variant}", "variant", 8,
            )
            if victory:
                await self.add_evidence(
                    session, entry, character_id, creature_id,
                    f"variant_victory:{variant}", "variant_victory", 6,
                )
        evidence_ids = set(
            (
                await session.scalars(
                    select(BestiaryEvidence.evidence_id).where(
                        BestiaryEvidence.character_id == character_id,
                        BestiaryEvidence.creature_id == creature_id,
                    )
                )
            ).all()
        )
        if creature_id in S30_DISTINCTIVE_BOSS_MASTERY:
            required = S30_DISTINCTIVE_BOSS_MASTERY[creature_id]
            entry.stage = (
                "dominated"
                if entry.bkp >= 50 and required.issubset(evidence_ids)
                else "studied"
                if entry.bkp >= 30
                else "known"
                if entry.bkp >= 10
                else "observed"
            )
        elif creature_id == "tecela_fosso":
            required = {
                "first_victory",
                "action:fio_arrasto",
                "action:casulo_breve",
                "action:queda_tecela",
            }
            entry.stage = (
                "dominated"
                if required.issubset(evidence_ids)
                else "studied"
                if entry.bkp >= 25
                else "known"
                if entry.bkp >= 10
                else "observed"
            )
        elif creature_id == "o_que_pende":
            required = {
                "first_victory",
                "phase:cordas_tensas",
                "phase:nada_sustenta",
                "mechanic:raizes_sustentacao",
                "action:despencar",
            }
            entry.stage = (
                "dominated"
                if required.issubset(evidence_ids)
                else "studied"
                if entry.bkp >= 22
                else "known"
                if entry.bkp >= 8
                else "observed"
            )
        elif creature_id == "matriarca_raizes":
            required = {
                "first_victory",
                "p12_completed",
                "phase:a_rede",
                "phase:aquilo_que_permanece",
                "mechanic:conexoes_radicular_observadas",
                "action:abraco_do_berco",
                "action:estrangulamento_do_vale",
            }
            entry.stage = (
                "dominated"
                if required.issubset(evidence_ids)
                else "studied"
                if entry.bkp >= 22
                else "known"
                if entry.bkp >= 8
                else "observed"
            )
        elif creature_id == "guardiao_no_antigo":
            required = {
                "first_victory",
                "phase:o_no_se_fecha",
                "phase:raiz_e_pedra",
                "mechanic:selos_radicular",
                "action:egide_raizes",
                "action:fechamento_no",
            }
            entry.stage = (
                "dominated"
                if required.issubset(evidence_ids)
                else "studied"
                if entry.bkp >= 22
                else "known"
                if entry.bkp >= 8
                else "observed"
            )
        elif (
            creature_id in VDE_DISTINCTIVE_ELITE_MASTERY
            or creature_id in VARZEAS_DISTINCTIVE_ELITE_MASTERY
        ):
            await self.add_evidence(
                session, entry, character_id, creature_id, "elite", "elite", 8
            )
            if victory:
                await self.add_evidence(
                    session,
                    entry,
                    character_id,
                    creature_id,
                    "elite_victory",
                    "elite_victory",
                    6,
                )
        elif creature_id in NARETH_DISTINCTIVE_BOSS_MASTERY:
            required = NARETH_DISTINCTIVE_BOSS_MASTERY[creature_id]
            entry.stage = (
                "dominated"
                if required.issubset(evidence_ids)
                else "studied"
                if entry.bkp >= 22
                else "known"
                if entry.bkp >= 8
                else "observed"
            )
        elif creature_id in VARZEAS_DISTINCTIVE_BOSS_MASTERY:
            required = VARZEAS_DISTINCTIVE_BOSS_MASTERY[creature_id]
            entry.stage = (
                "dominated"
                if required.issubset(evidence_ids)
                else "studied"
                if entry.bkp >= 22
                else "known"
                if entry.bkp >= 8
                else "observed"
            )
        elif creature_id in NARETH_DISTINCTIVE_ELITE_MASTERY:
            await self.add_evidence(
                session, entry, character_id, creature_id, "elite", "elite", 8
            )
            if victory:
                await self.add_evidence(
                    session,
                    entry,
                    character_id,
                    creature_id,
                    "elite_victory",
                    "elite_victory",
                    6,
                )
            required = NARETH_DISTINCTIVE_ELITE_MASTERY[creature_id]
            entry.stage = (
                "dominated"
                if required.issubset(evidence_ids)
                else "studied"
                if entry.bkp >= 25
                else "known"
                if entry.bkp >= 10
                else "observed"
            )
        elif creature_id == "vigia_partido" or observation_category == "boss":
            required = {
                "first_victory",
                "p6_completed",
                "phase:a_fratura",
                "phase:o_ultimo_posto",
                "action:egide_partida",
                "action:queda_ocaso",
            }
            entry.stage = (
                "dominated"
                if required.issubset(evidence_ids)
                else "studied"
                if entry.bkp >= 22
                else "known"
                if entry.bkp >= 8
                else "observed"
            )
        elif elite:
            await self.add_evidence(
                session, entry, character_id, creature_id, "elite", "elite", 8
            )
            if victory:
                await self.add_evidence(
                    session, entry, character_id, creature_id,
                    "elite_victory", "elite_victory", 6,
                )
        if victory:
            first_victory = await session.scalar(
                select(BestiaryEvidence).where(
                    BestiaryEvidence.character_id == character_id,
                    BestiaryEvidence.creature_id == creature_id,
                    BestiaryEvidence.evidence_id == "first_victory",
                )
            )
            if first_victory is None:
                await self.add_evidence(
                    session, entry, character_id, creature_id,
                    "first_victory", "victory", 5,
                )
                if creature_id == "alfa_cinereo":
                    await self._grant_alpha_victory_xp(
                        session, character_id, creature_id
                    )
                elif creature_id == "viuva_fuligem":
                    await self._grant_regional_victory_xp(
                        session, character_id, creature_id, reference_level=6
                    )
                elif creature_id == "vigia_partido":
                    await self._grant_regional_victory_xp(
                        session,
                        character_id,
                        creature_id,
                        reference_level=10,
                        configured_xp=474,
                    )
                elif creature_id in VDE_IMPORTANT_FIRST_VICTORY_XP:
                    reference_level, configured_xp = VDE_IMPORTANT_FIRST_VICTORY_XP[
                        creature_id
                    ]
                    await self._grant_regional_victory_xp(
                        session,
                        character_id,
                        creature_id,
                        reference_level=reference_level,
                        configured_xp=configured_xp,
                    )
                elif creature_id in VARZEAS_IMPORTANT_FIRST_VICTORY_XP:
                    reference_level, configured_xp = VARZEAS_IMPORTANT_FIRST_VICTORY_XP[
                        creature_id
                    ]
                    await self._grant_regional_victory_xp(
                        session,
                        character_id,
                        creature_id,
                        reference_level=reference_level,
                        configured_xp=configured_xp,
                    )
                elif creature_id == "matriarca_raizes":
                    await self._grant_regional_victory_xp(
                        session,
                        character_id,
                        creature_id,
                        reference_level=20,
                        configured_xp=1086,
                    )
                elif creature_id == "arconte_invertido":
                    await self._grant_regional_victory_xp(
                        session,
                        character_id,
                        creature_id,
                        reference_level=30,
                        configured_xp=1956,
                    )
            else:
                entry.bkp += _repeat_bkp(
                    entry.wins, elite, observation_category
                )

        categories = set(
            (
                await session.scalars(
                    select(BestiaryEvidence.category).where(
                        BestiaryEvidence.character_id == character_id,
                        BestiaryEvidence.creature_id == creature_id,
                    )
                )
            ).all()
        )
        evidence_ids = set(
            (
                await session.scalars(
                    select(BestiaryEvidence.evidence_id).where(
                        BestiaryEvidence.character_id == character_id,
                        BestiaryEvidence.creature_id == creature_id,
                    )
                )
            ).all()
        )
        if creature_id == "tecela_fosso":
            required = {
                "first_victory",
                "action:fio_arrasto",
                "action:casulo_breve",
                "action:queda_tecela",
            }
            entry.stage = (
                "dominated"
                if required.issubset(evidence_ids)
                else "studied"
                if entry.bkp >= 25
                else "known"
                if entry.bkp >= 10
                else "observed"
            )
        elif creature_id == "o_que_pende":
            required = {
                "first_victory",
                "phase:cordas_tensas",
                "phase:nada_sustenta",
                "mechanic:raizes_sustentacao",
                "action:despencar",
            }
            entry.stage = (
                "dominated"
                if required.issubset(evidence_ids)
                else "studied"
                if entry.bkp >= 22
                else "known"
                if entry.bkp >= 8
                else "observed"
            )
        elif creature_id == "matriarca_raizes":
            required = {
                "first_victory",
                "p12_completed",
                "phase:a_rede",
                "phase:aquilo_que_permanece",
                "mechanic:conexoes_radicular_observadas",
                "action:abraco_do_berco",
                "action:estrangulamento_do_vale",
            }
            entry.stage = (
                "dominated"
                if required.issubset(evidence_ids)
                else "studied"
                if entry.bkp >= 22
                else "known"
                if entry.bkp >= 8
                else "observed"
            )
        elif creature_id == "guardiao_no_antigo":
            required = {
                "first_victory",
                "phase:o_no_se_fecha",
                "phase:raiz_e_pedra",
                "mechanic:selos_radicular",
                "action:egide_raizes",
                "action:fechamento_no",
            }
            entry.stage = (
                "dominated"
                if required.issubset(evidence_ids)
                else "studied"
                if entry.bkp >= 22
                else "known"
                if entry.bkp >= 8
                else "observed"
            )
        elif creature_id in NARETH_DISTINCTIVE_BOSS_MASTERY:
            required = NARETH_DISTINCTIVE_BOSS_MASTERY[creature_id]
            entry.stage = (
                "dominated"
                if required.issubset(evidence_ids)
                else "studied"
                if entry.bkp >= 22
                else "known"
                if entry.bkp >= 8
                else "observed"
            )
        elif creature_id in VARZEAS_DISTINCTIVE_BOSS_MASTERY:
            required = VARZEAS_DISTINCTIVE_BOSS_MASTERY[creature_id]
            entry.stage = (
                "dominated"
                if required.issubset(evidence_ids)
                else "studied"
                if entry.bkp >= 22
                else "known"
                if entry.bkp >= 8
                else "observed"
            )
        elif creature_id in NARETH_DISTINCTIVE_ELITE_MASTERY:
            required = NARETH_DISTINCTIVE_ELITE_MASTERY[creature_id]
            entry.stage = (
                "dominated"
                if required.issubset(evidence_ids)
                else "studied"
                if entry.bkp >= 25
                else "known"
                if entry.bkp >= 10
                else "observed"
            )
        elif creature_id == "vigia_partido" or observation_category == "boss":
            required = {
                "first_victory",
                "p6_completed",
                "phase:a_fratura",
                "phase:o_ultimo_posto",
                "action:egide_partida",
                "action:queda_ocaso",
            }
            entry.stage = (
                "dominated"
                if required.issubset(evidence_ids)
                else "studied"
                if entry.bkp >= 22
                else "known"
                if entry.bkp >= 8
                else "observed"
            )
        elif creature_id in VDE_DISTINCTIVE_ELITE_MASTERY:
            required = VDE_DISTINCTIVE_ELITE_MASTERY[creature_id]
            entry.stage = (
                "dominated"
                if required.issubset(evidence_ids)
                else "studied"
                if entry.bkp >= 25
                else "known"
                if entry.bkp >= 10
                else "observed"
            )
        elif creature_id in VARZEAS_DISTINCTIVE_ELITE_MASTERY:
            required = VARZEAS_DISTINCTIVE_ELITE_MASTERY[creature_id]
            entry.stage = (
                "dominated"
                if required.issubset(evidence_ids)
                else "studied"
                if entry.bkp >= 25
                else "known"
                if entry.bkp >= 10
                else "observed"
            )
        elif elite:
            if creature_id == "alfa_cinereo":
                special = {
                    "first_victory",
                    "mechanic:bleed",
                    "mechanic:prepared_leap",
                }.issubset(evidence_ids)
            else:
                special = bool({"elite_victory", "mechanic"} & categories)
            entry.stage = (
                "dominated"
                if entry.bkp >= 45 and entry.wins >= 1 and special
                else "studied"
                if entry.bkp >= 25
                else "known"
                if entry.bkp >= 10
                else "observed"
            )
        elif observation_category in {"uncommon", "rare"}:
            entry.stage = (
                "dominated"
                if entry.bkp >= 40 and len(categories) >= 2
                else "studied"
                if entry.bkp >= 22
                else "known"
                if entry.bkp >= 8
                else "observed"
            )
        else:
            entry.stage = (
                "dominated"
                if entry.bkp >= 60 and len(categories) >= 3
                else "studied"
                if entry.bkp >= 30 and len(categories) >= 2
                else "known"
                if entry.bkp >= 10
                else "observed"
            )

        new_evidence_ids = evidence_ids - before_evidence_ids
        if (
            (previous_stage is not None and previous_stage != entry.stage)
            or any(evidence.startswith("variant:") for evidence in new_evidence_ids)
            or (
                creature_id == "vigia_partido"
                and "first_victory" in new_evidence_ids
            )
        ):
            await reconcile_tdo_feats_for_character(session, character_id)
        if (
            (previous_stage is not None and previous_stage != entry.stage)
            or (
                creature_id
                in {
                    "vigia_enraizado",
                    "custodio_enredado",
                    "prelado_enraizado",
                    "guardiao_no_antigo",
                }
                and new_evidence_ids
            )
        ):
            from asterion.application.vde_feats import reconcile_vde_feats_for_character

            await reconcile_vde_feats_for_character(session, character_id)
        if (
            (previous_stage is not None and previous_stage != entry.stage)
            or victory
            or any(evidence.startswith("variant:") for evidence in new_evidence_ids)
        ):
            from asterion.application.nareth_feats import reconcile_nareth_feats_for_character

            await reconcile_nareth_feats_for_character(session, character_id)
        if (
            (
                creature_id in VARZEAS_BASE_CREATURES
                or creature_id in VARZEAS_DISTINCTIVE_ELITE_MASTERY
            )
            and (
                (previous_stage is not None and previous_stage != entry.stage)
                or victory
                or bool(new_evidence_ids)
            )
        ):
            from asterion.application.varzeas_feats import reconcile_varzeas_feats

            character = await session.get(Character, character_id)
            if character is not None:
                await reconcile_varzeas_feats(session, character)
        if (previous_stage is not None and previous_stage != entry.stage) or (
            victory and new_evidence_ids
        ):
            return {
                "creature_id": creature_id,
                "creature_name": creature_for(creature_id).name,
                "stage": entry.stage,
                "stage_label": BESTIARY_STAGE_LABELS[entry.stage],
            }
        return None

    async def record_combat_events(
        self, session, character_id, creature_id, variant, combat
    ):
        entry = await session.scalar(
            select(BestiaryEntry)
            .where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == creature_id,
            )
            .with_for_update()
        )
        if entry is None:
            return set()
        new_evidence_ids = set()
        for event in combat.events:
            if event.actor != "enemy":
                continue
            action_id = event.action.removeprefix("prepare:")
            if await self.add_evidence(
                session,
                entry,
                character_id,
                creature_id,
                f"action:{action_id}",
                "behavior",
                4,
            ):
                new_evidence_ids.add(f"action:{action_id}")
            if event.action == "prepare:leap":
                if await self.add_evidence(
                    session, entry, character_id, creature_id,
                    "mechanic:prepared_leap", "mechanic", 5,
                ):
                    new_evidence_ids.add("mechanic:prepared_leap")
            if creature_id == "boss.altos.s30.custodio_ultimo_turno":
                if action_id == "ordem_vencida":
                    if await self.add_evidence(
                        session,
                        entry,
                        character_id,
                        creature_id,
                        "mechanic:ordem_vencida_agility",
                        "mechanic",
                        5,
                    ):
                        new_evidence_ids.add("mechanic:ordem_vencida_agility")
                if event.action == "prepare:ultimo_turno":
                    if await self.add_evidence(
                        session,
                        entry,
                        character_id,
                        creature_id,
                        "mechanic:ultimo_turno_telegraph",
                        "mechanic",
                        5,
                    ):
                        new_evidence_ids.add("mechanic:ultimo_turno_telegraph")
            if event.action == "rend":
                if await self.add_evidence(
                    session, entry, character_id, creature_id,
                    "mechanic:bleed", "mechanic", 5,
                ):
                    new_evidence_ids.add("mechanic:bleed")
            if variant == "hemorrhagic" and event.damage > 0:
                if await self.add_evidence(
                    session, entry, character_id, creature_id,
                    "mechanic:hemorrhage", "mechanic", 5,
                ):
                    new_evidence_ids.add("mechanic:hemorrhage")
            if variant == "venomous" and event.damage > 0:
                if await self.add_evidence(
                    session, entry, character_id, creature_id,
                    "mechanic:poison", "mechanic", 5,
                ):
                    new_evidence_ids.add("mechanic:poison")
            if creature_id == "viuva_fuligem":
                if action_id == "widow_sting" and event.damage > 0:
                    if await self.add_evidence(
                        session, entry, character_id, creature_id,
                        "mechanic:poison", "mechanic", 5,
                    ):
                        new_evidence_ids.add("mechanic:poison")
                if action_id == "soot_web" and event.effect_id == "soot_web":
                    if await self.add_evidence(
                        session, entry, character_id, creature_id,
                        "mechanic:agility_reduction", "mechanic", 5,
                    ):
                        new_evidence_ids.add("mechanic:agility_reduction")
            if creature_id == "viuva_rubra" and action_id in {
                "picada_rubra",
                "toxina_concentrada",
            } and event.damage > 0:
                if await self.add_evidence(
                    session,
                    entry,
                    character_id,
                    creature_id,
                    "mechanic:poison",
                    "mechanic",
                    5,
                ):
                    new_evidence_ids.add("mechanic:poison")
        return new_evidence_ids

    async def add_evidence(
        self,
        session,
        entry,
        character_id,
        creature_id,
        evidence_id,
        category,
        points=0,
    ):
        exists = await session.scalar(
            select(BestiaryEvidence).where(
                BestiaryEvidence.character_id == character_id,
                BestiaryEvidence.creature_id == creature_id,
                BestiaryEvidence.evidence_id == evidence_id,
            )
        )
        if exists is not None:
            return False
        session.add(
            BestiaryEvidence(
                character_id=character_id,
                creature_id=creature_id,
                evidence_id=evidence_id,
                category=category,
            )
        )
        entry.bkp += points
        return True

    async def refresh_boss_mastery(self, session, character_id, creature_id):
        """Recompute the campaign boss stage after an external campaign fact is added."""
        entry = await session.scalar(
            select(BestiaryEntry)
            .where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == creature_id,
            )
            .with_for_update()
        )
        if entry is None:
            return
        evidence_ids = set(
            (
                await session.scalars(
                    select(BestiaryEvidence.evidence_id).where(
                        BestiaryEvidence.character_id == character_id,
                        BestiaryEvidence.creature_id == creature_id,
                    )
                )
            ).all()
        )
        required = (
            S30_DISTINCTIVE_BOSS_MASTERY[creature_id]
            if creature_id in S30_DISTINCTIVE_BOSS_MASTERY
            else
            VARZEAS_DISTINCTIVE_BOSS_MASTERY[creature_id]
            if creature_id in VARZEAS_DISTINCTIVE_BOSS_MASTERY
            else NARETH_DISTINCTIVE_BOSS_MASTERY[creature_id]
            if creature_id in NARETH_DISTINCTIVE_BOSS_MASTERY
            else
            {
                "first_victory",
                "p12_completed",
                "phase:a_rede",
                "phase:aquilo_que_permanece",
                "mechanic:conexoes_radicular_observadas",
                "action:abraco_do_berco",
                "action:estrangulamento_do_vale",
            }
            if creature_id == "matriarca_raizes"
            else {
                "first_victory",
                "p6_completed",
                "phase:a_fratura",
                "phase:o_ultimo_posto",
                "action:egide_partida",
                "action:queda_ocaso",
            }
        )
        previous_stage = entry.stage
        if creature_id in S30_DISTINCTIVE_BOSS_MASTERY:
            entry.stage = (
                "dominated"
                if entry.bkp >= 50 and required.issubset(evidence_ids)
                else "studied"
                if entry.bkp >= 30
                else "known"
                if entry.bkp >= 10
                else "observed"
            )
        else:
            entry.stage = (
                "dominated"
                if required.issubset(evidence_ids)
                else "studied"
                if entry.bkp >= 22
                else "known"
                if entry.bkp >= 8
                else "observed"
            )
        if entry.stage != previous_stage:
            await reconcile_tdo_feats_for_character(session, character_id)

    async def _grant_observation_xp(
        self, session, character_id, creature_id, reference_level
    ):
        source_id = f"bestiary:observation:{character_id}:{creature_id}"
        event = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == source_id,
            )
            .with_for_update()
        )
        if event is not None:
            return 0
        xp = int(
            (Decimal(level_xp(reference_level)) * Decimal("0.01")).quantize(
                Decimal(1), rounding=ROUND_HALF_UP
            )
        )
        event = RewardEvent(character_id=character_id, source_id=source_id)
        session.add(event)
        await session.flush()
        session.add(
            RewardComponent(
                reward_event_id=event.id,
                kind="bestiary_observation_xp",
                item_id=creature_id,
                quantity=xp,
                payload={"reference_level": reference_level, "fixed_percent": "0.01"},
            )
        )
        character = await session.scalar(
            select(Character).where(Character.id == character_id).with_for_update()
        )
        if character is not None:
            character.xp += xp
        return xp

    async def _grant_alpha_victory_xp(self, session, character_id, creature_id):
        source_id = f"bestiary:first_victory:{character_id}:{creature_id}"
        event = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == source_id,
            )
            .with_for_update()
        )
        if event is not None:
            return False
        event = RewardEvent(character_id=character_id, source_id=source_id)
        session.add(event)
        await session.flush()
        session.add(
            RewardComponent(
                reward_event_id=event.id,
                kind="bestiary_first_victory_xp",
                item_id=creature_id,
                quantity=198,
                payload={"reference_level": 3, "milestone": "first_major_victory"},
            )
        )
        character = await session.scalar(
            select(Character).where(Character.id == character_id).with_for_update()
        )
        if character is not None:
            character.xp += 198
        return True

    async def _grant_regional_victory_xp(
        self,
        session,
        character_id,
        creature_id,
        *,
        reference_level,
        configured_xp=None,
    ):
        source_id = f"bestiary:first_victory:{character_id}:{creature_id}"
        event = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == source_id,
            )
            .with_for_update()
        )
        if event is not None:
            return False
        xp = (
            configured_xp
            if configured_xp is not None
            else int(
                (Decimal(level_xp(reference_level)) * Decimal("0.06")).quantize(
                    Decimal(1), rounding=ROUND_HALF_UP
                )
            )
        )
        event = RewardEvent(character_id=character_id, source_id=source_id)
        session.add(event)
        await session.flush()
        session.add(
            RewardComponent(
                reward_event_id=event.id,
                kind="bestiary_first_victory_xp",
                item_id=creature_id,
                quantity=xp,
                payload=(
                    {"reference_level": reference_level, "configured_xp": configured_xp}
                    if configured_xp is not None
                    else {"reference_level": reference_level, "fixed_percent": "0.06"}
                ),
            )
        )
        character = await session.scalar(
            select(Character).where(Character.id == character_id).with_for_update()
        )
        if character is not None:
            character.xp += xp
        return True


def _repeat_bkp(wins: int, elite: bool, observation_category: str) -> int:
    if elite:
        return 3 if wins == 2 else 2 if wins == 3 else 1 if 4 <= wins <= 5 else 0
    if observation_category in {"uncommon", "rare"}:
        return 2 if 2 <= wins <= 5 else 0
    if 2 <= wins <= 5:
        return 2
    if 6 <= wins <= 10:
        return 1
    if wins in {15, 25, 40}:
        return 3
    return 0
