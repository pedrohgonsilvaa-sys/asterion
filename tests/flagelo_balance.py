"""O Despertar dos Flagelos — suíte de balanceamento determinística (espec. final §23).

Não existe simulador de combate paralelo. A medição reaproveita o que o jogo usa:

- dano, vida, Defesa e Esquiva do jogador: ``FlageloRoundSimulator.prepare`` (o motor de
  combate real, sobre um personagem persistido no PostgreSQL), medido uma vez por Flagelo;
- rodada: ``veu_combat.resolve_batch`` com o kit, o nível e a esquiva global dos Flagelos;
- IA, alvos, escalonamento e arredondamento: ``domain/flagelos`` (``choose_action``,
  ``choose_targets``, ``scaling_for_steps``, ``effective_max_hp``, ``effective_attack``).

Só dados: nenhum valor de jogo é alterado e nenhum buff/nerf é aplicado. Tudo é semeado por
texto (sem ``random``/relógio), então duas execuções dão exatamente o mesmo relatório.

Perfil do participante (piso, não previsão): Sentinela no nível de referência do Flagelo, sem
equipamento, Talentos nem Artes, só Atacar. Morto, volta depois da reentrada de 2 minutos com
vida cheia (12 rodadas de 10 s). O Flagelo começa cheio no escalonamento medido (0, 5 ou 10
passos): o escalonamento real não cura, então é um teto para o TTK.
"""

from __future__ import annotations

import dataclasses
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid5

from sqlalchemy.ext.asyncio import async_sessionmaker

from asterion.application.flagelo_combat import BossEffects, FlageloRoundSimulator
from asterion.domain import flagelos as fl
from asterion.domain import veu_combat as vc
from asterion.domain.combat_math import resolve_combat_stats
from asterion.domain.veu_bestiary import ActionKind, VeuAction
from asterion.infrastructure.db.models import Account, Character

D = Decimal
_NS = UUID(int=0xF1A6E105)

PARTICIPANT_COUNTS = (3, 5, 6, 9, 12, 20, 30, 50)
SCALING_STEPS = (0, 5, 10)
ABLATION_COUNT = 10
REENTRY_ROUNDS = int(fl.REENTRY_DELAY.total_seconds() // fl.TURN_SECONDS)  # 12
MAX_ROUNDS = 6_000  # 1000 min; acima disso o Flagelo é dado como "sem morte" na medição
PROFILE_SAMPLES = 24  # personagens idênticos com sementes de combate distintas
OUTLIER_LOW, OUTLIER_HIGH = D("0.67"), D("1.50")  # fração da mediana dos seis Flagelos


# --------------------------------------------------------------------------- perfil do motor


def _name(level: int, index: int) -> str:
    letters = "abcdefghijklmnopqrstuvwxyz"
    return "Med" + letters[level // 10 % 26] + letters[index // 26 % 26] + letters[index % 26]


@dataclass(frozen=True, slots=True)
class Profile:
    level: int
    max_hp: int
    defense: Decimal
    defense_def_debuffed: Decimal
    evasion: Decimal
    evasion_agi_debuffed: Decimal
    damage: int  # média inteira do ataque básico (inclui os críticos do motor)
    damage_atk_debuffed: int  # mesmo ataque com ATQ −10%


def _debuff(stat: str) -> dict:
    effect = vc.PlayerEffect("balance:" + stat, stat, D("0.10"), 2, "debuff", "balance")
    return {"effects": [effect.to_data()]}


async def measure_profile(sessions: async_sessionmaker, region: fl.FlageloRegion) -> Profile:
    level = region.reference_level
    boss = region.flagelo
    max_hp = int(resolve_combat_stats("sentinela", level, "remanescente").hp)
    ids: list[UUID] = []
    async with sessions.begin() as session:
        for index in range(PROFILE_SAMPLES):
            telegram_id = 870_000_000 + level * 1_000 + index
            session.add(Account(telegram_id=telegram_id))
            character = Character(
                id=uuid5(_NS, f"profile|{level}|{index}"),  # o motor semeia o crítico pelo id
                telegram_id=telegram_id,
                server_id="balance",
                name=_name(level, index),
                race="remanescente",
                character_class="sentinela",
                stage="menu",
                ruleset_version="tdo-1.0.15",
                level=level,
                hp=D(max_hp),
                max_hp=D(max_hp),
                vigor=100,
                max_vigor=100,
            )
            session.add(character)
            await session.flush()
            ids.append(character.id)

    async def prepare(state: dict, tag: str):
        enemy = vc.EnemyUnit(
            boss.flagelo_id, D(boss.hp), D(boss.hp), D(boss.attack), D(boss.defense),
            agility=D(boss.agility),
        )
        participants = [SimpleNamespace(character_id=i, hp=None, combat_state=state) for i in ids]
        actions = [
            SimpleNamespace(character_id=i, action_type="attack", art_slot=None, target_ref=None)
            for i in ids
        ]
        simulator = FlageloRoundSimulator(level, BossEffects())
        async with sessions() as session:
            inputs = await simulator.prepare(
                session, participants, actions, {boss.flagelo_id: enemy}, f"balance|{level}|{tag}"
            )
        return inputs

    base = await prepare({}, "base")
    atk = await prepare(_debuff("attack"), "atk")
    agi = await prepare(_debuff("agility"), "agi")
    dfn = await prepare(_debuff("defense"), "def")
    first = base.players[ids[0]]
    return Profile(
        level=level,
        max_hp=int(first.max_hp),
        defense=first.defense,
        defense_def_debuffed=dfn.players[ids[0]].defense,
        evasion=first.evasion,
        evasion_agi_debuffed=agi.players[ids[0]].evasion,
        damage=int(sum(i.damage for i in base.intents) // len(base.intents)),
        damage_atk_debuffed=int(sum(i.damage for i in atk.intents) // len(atk.intents)),
    )


# --------------------------------------------------------------------------- variações do kit


def kit_variant(
    flagelo_id: str,
    *,
    no_aoe: bool = False,
    no_prepared: bool = False,
    no_debuffs: bool = False,
    no_heal: bool = False,
):
    """Kit do Flagelo sem uma família de ações (ablação). Não altera ``domain/flagelos``."""

    def kit(code: str) -> tuple[VeuAction, ...]:
        out = []
        for item in fl.kit(code):
            if no_aoe and item.kind is ActionKind.AOE:
                continue
            if no_prepared and item.prepared:
                continue
            if no_heal and item.kind is ActionKind.HEAL:
                continue
            if no_debuffs:
                # Mantém o dano; remove só o debuff de atributo e o DoT.
                item = dataclasses.replace(
                    item,
                    kind=ActionKind.DAMAGE if item.kind is ActionKind.DAMAGE_DEBUFF else item.kind,
                    stat=None if item.kind is not ActionKind.SELF_BUFF else item.stat,
                    magnitude=None if item.kind is not ActionKind.SELF_BUFF else item.magnitude,
                    turns=None if item.kind is not ActionKind.SELF_BUFF else item.turns,
                    dot_kind=None,
                    dot_stacks=0,
                    second_stat=None if item.kind is not ActionKind.SELF_BUFF else item.second_stat,
                    second_magnitude=(
                        None if item.kind is not ActionKind.SELF_BUFF else item.second_magnitude
                    ),
                )
            out.append(item)
        return tuple(out)

    return kit


# --------------------------------------------------------------------------- simulação


@dataclass(slots=True)
class Result:
    flagelo_id: str
    participants: int
    steps: int
    killed: bool
    rounds: int  # rodadas de relógio (10 s) até a morte, inclusive as sem ninguém presente
    boss_hp: int
    deaths: int = 0
    damage_taken: int = 0
    dodged: int = 0
    player_rounds: int = 0
    healed: int = 0
    by_action: dict[str, dict[str, int]] = field(default_factory=dict)

    @property
    def ttk_minutes(self) -> Decimal | None:
        return D(self.rounds * fl.TURN_SECONDS) / 60 if self.killed else None

    @property
    def damage_per_participant_round(self) -> Decimal:
        return D(self.damage_taken) / self.player_rounds if self.player_rounds else D(0)


def simulate(
    region: fl.FlageloRegion,
    profile: Profile,
    participants: int,
    *,
    steps: int = 0,
    kit=None,
    max_rounds: int = MAX_ROUNDS,
) -> Result:
    boss = region.flagelo
    code = boss.flagelo_id
    kit = kit or fl.kit
    scaling = fl.scaling_for_steps(steps)
    max_hp = fl.effective_max_hp(boss.hp, scaling.hp_bonus)
    unit = vc.EnemyUnit(
        code, D(max_hp), D(max_hp), D(fl.effective_attack(boss.attack, scaling.atq_bonus)),
        D(boss.defense), agility=D(boss.agility),
    )
    ids = [uuid5(_NS, f"{code}|{index}") for index in range(participants)]

    def fresh() -> vc.PlayerUnit:
        return vc.PlayerUnit(
            ids[0], D(profile.max_hp), D(profile.max_hp), profile.defense, evasion=profile.evasion
        )

    players = {i: dataclasses.replace(fresh(), character_id=i) for i in ids}
    returns_at: dict[UUID, int] = {}
    result = Result(code, participants, steps, False, 0, max_hp)
    by_action: dict[str, dict[str, int]] = defaultdict(
        lambda: {"uses": 0, "damage": 0, "dodged": 0}
    )

    for number in range(1, max_rounds + 1):
        for character_id, back in list(returns_at.items()):
            if number >= back:
                players[character_id] = dataclasses.replace(fresh(), character_id=character_id)
                del returns_at[character_id]
        present = sorted(i for i in ids if i not in returns_at)
        result.rounds = number
        if not present:
            continue  # ninguém em combate: nenhuma oportunidade abre (o relógio corre)
        chosen = _choose(code, unit, kit)  # IA real; ``kit`` só muda as ações elegíveis
        targets = fl.choose_targets(chosen, present, fl.seed_for(f"{code}|{participants}", number))
        intents = []
        for character_id in present:
            player = players[character_id]
            player.defense = (
                profile.defense_def_debuffed
                if any(e.stat == "defense" for e in player.effects)
                else profile.defense
            )
            weak = any(e.stat == "attack" for e in player.effects)
            damage = profile.damage_atk_debuffed if weak else profile.damage
            player.evasion = (
                profile.evasion_agi_debuffed
                if any(e.stat == "agility" for e in player.effects)
                else profile.evasion
            )
            intents.append(vc.PlayerIntent(character_id, "attack", code, damage))
        outcome = vc.resolve_batch(
            {code: unit},
            {i: players[i] for i in present},
            intents,
            [vc.EnemyDecisionData(code, chosen.key, tuple(targets), chosen.prepared)],
            kit=kit,
            level=boss.level,
            evasion_seed=f"{code}|{participants}|{steps}|{number}",
        )
        taken = sum(outcome.damage_taken.values())
        dodged = sum(outcome.dodged_by_character.values())
        row = by_action[chosen.key]
        row["uses"] += 1
        row["damage"] += int(taken)
        row["dodged"] += int(dodged)
        result.damage_taken += int(taken)
        result.dodged += int(dodged)
        result.player_rounds += len(present)
        result.healed += int(
            sum(item["amount"] for item in outcome.history if item["kind"] == "enemy_healed")
        )
        for character_id in outcome.defeated_players:
            result.deaths += 1
            returns_at[character_id] = number + 1 + REENTRY_ROUNDS
        if unit.hp <= 0:
            result.killed = True
            break
    result.by_action = {key: dict(value) for key, value in by_action.items()}
    return result


def _choose(code: str, unit: vc.EnemyUnit, kit) -> VeuAction:
    """``fl.choose_action`` lê o kit publicado; para uma variação, ``skip`` tira as ações."""
    published = fl.kit(code)
    allowed = {item.key for item in kit(code)}
    skip = [item.key for item in published if item.key not in allowed]
    return fl.choose_action(
        code,
        cooldowns=unit.cooldowns,
        uses=unit.uses,
        hp=unit.hp,
        max_hp=unit.max_hp,
        skip=skip,
    )


# --------------------------------------------------------------------------- isolados


def isolated_action(
    region: fl.FlageloRegion,
    profile: Profile,
    key: str,
    participants: int,
    *,
    defend: bool = False,
    defense: Decimal | None = None,
):
    """Uma ação sozinha contra ``participants`` jogadores de vida cheia (sem esquiva sorteada
    quando ``evasion=0``): dano por alvo e total do grupo, e efeitos aplicados."""
    boss = region.flagelo
    code = boss.flagelo_id
    ids = [uuid5(_NS, f"iso|{code}|{i}") for i in range(participants)]
    players = {
        i: vc.PlayerUnit(
            i, D(profile.max_hp), D(profile.max_hp), profile.defense if defense is None else defense
        )
        for i in ids
    }
    unit = vc.EnemyUnit(
        code, D(boss.hp), D(boss.hp), D(boss.attack), D(boss.defense), agility=D(boss.agility)
    )
    item = fl.action(code, key)
    targets = fl.choose_targets(item, ids, 0)
    intents = [vc.PlayerIntent(i, "defend", None, 0) for i in ids] if defend else []
    outcome = vc.resolve_batch(
        {code: unit}, players, intents,
        [vc.EnemyDecisionData(code, key, tuple(targets), item.prepared)],
        kit=fl.kit, level=boss.level,
    )
    taken = list(outcome.damage_taken.values())
    return {
        "targets": len(targets),
        "per_target": max(taken) if taken else 0,
        "group_total": sum(taken),
        "effects": sorted({e.stat for p in players.values() for e in p.effects}),
        "dots": sorted({d.kind for p in players.values() for d in p.dots}),
    }


# --------------------------------------------------------------------------- relatório


@dataclass(slots=True)
class Report:
    profiles: dict[str, Profile]
    ttk: dict[tuple[str, int], Result]
    scaling: dict[tuple[str, int, int], Result]
    ablation: dict[tuple[str, str], Result]
    isolated: dict[tuple[str, str], dict]
    prepared_defended: dict[str, dict]
    def_debuffed: dict[str, dict]
    outliers: list[str] = field(default_factory=list)


def build(profiles: dict[str, Profile]) -> Report:
    regions = fl.REGIONS
    ttk = {
        (r.flagelo.flagelo_id, n): simulate(r, profiles[r.flagelo.flagelo_id], n)
        for r in regions
        for n in PARTICIPANT_COUNTS
    }
    scaling = {
        (r.flagelo.flagelo_id, ABLATION_COUNT, s): simulate(
            r, profiles[r.flagelo.flagelo_id], ABLATION_COUNT, steps=s
        )
        for r in regions
        for s in SCALING_STEPS
    }
    ablations = {
        "base": {},
        "sem AoE": {"no_aoe": True},
        "sem Preparada": {"no_prepared": True},
        "sem debuffs/DoT": {"no_debuffs": True},
        "sem cura própria": {"no_heal": True},
    }
    ablation = {}
    for r in regions:
        code = r.flagelo.flagelo_id
        for name, options in ablations.items():
            ablation[(code, name)] = simulate(
                r, profiles[code], ABLATION_COUNT, kit=kit_variant(code, **options)
            )
    defended = {
        r.flagelo.flagelo_id: isolated_action(
            r, profiles[r.flagelo.flagelo_id],
            next(a.key for a in r.flagelo.actions if a.prepared), ABLATION_COUNT, defend=True,
        )
        for r in regions
    }
    isolated = {
        (r.flagelo.flagelo_id, item.key): isolated_action(
            r, profiles[r.flagelo.flagelo_id], item.key, ABLATION_COUNT
        )
        for r in regions
        for item in r.flagelo.actions
    }
    def_debuffed = {
        r.flagelo.flagelo_id: isolated_action(
            r, profiles[r.flagelo.flagelo_id], r.flagelo.basic_action.key, ABLATION_COUNT,
            defense=profiles[r.flagelo.flagelo_id].defense_def_debuffed,
        )
        for r in regions
    }
    report = Report(profiles, ttk, scaling, ablation, isolated, defended, def_debuffed)
    report.outliers = find_outliers(report)
    return report


def find_outliers(report: Report) -> list[str]:
    """Só detecta e descreve: nenhum buff/nerf é aplicado."""
    found: list[str] = []
    codes = [r.flagelo.flagelo_id for r in fl.REGIONS]
    for n in PARTICIPANT_COUNTS:
        values = {c: report.ttk[(c, n)].ttk_minutes for c in codes}
        if any(v is None for v in values.values()):
            missing = ", ".join(c for c, v in values.items() if v is None)
            found.append(f"N={n}: sem morte em {MAX_ROUNDS * fl.TURN_SECONDS // 60} min: {missing}")
            continue
        ordered = sorted(values.values())
        median = (ordered[2] + ordered[3]) / 2
        for code, value in values.items():
            ratio = value / median
            if ratio < OUTLIER_LOW or ratio > OUTLIER_HIGH:
                found.append(f"N={n}: {code} TTK {value:.1f} min = {ratio:.2f}× a mediana")
    return found


def attention(report: Report) -> list[str]:
    """Fatos que merecem olhar do autor; nenhum vira falha nem ajuste automático."""
    notes: list[str] = []
    for region in fl.REGIONS:
        code = region.flagelo.flagelo_id
        base = report.ablation[(code, "base")]
        total = max(1, base.damage_taken)
        aoe_keys = [i.key for i in region.flagelo.actions if i.kind is ActionKind.AOE]
        aoe = sum(base.by_action.get(k, {}).get("damage", 0) for k in aoe_keys)
        if aoe * 100 // total >= 50:
            notes.append(
                f"{region.flagelo.short_name}: a AoE causa {aoe * 100 // total}% do dano recebido "
                f"(N = {ABLATION_COUNT}); sem ela as mortes caem de {base.deaths} para "
                f"{report.ablation[(code, 'sem AoE')].deaths}."
            )
    for n in (3, 5):
        for region in fl.REGIONS:
            code = region.flagelo.flagelo_id
            r = report.ttk[(code, n)]
            if r.deaths >= 20:
                notes.append(
                    f"{region.flagelo.short_name}: com {n} participantes ocorrem {r.deaths} "
                    f"derrotas até a morte ({_min(r.ttk_minutes)} min)."
                )
    return notes


# --------------------------------------------------------------------------- Markdown


def _min(value: Decimal | None) -> str:
    return "sem morte" if value is None else f"{value:.1f}"


def render(report: Report) -> str:
    codes = [r.flagelo.flagelo_id for r in fl.REGIONS]
    names = {r.flagelo.flagelo_id: r.flagelo.short_name for r in fl.REGIONS}
    out: list[str] = []
    add = out.append
    add("# O Despertar dos Flagelos — medição de balanceamento (V1)")
    add("")
    add("Gerado por `tests/flagelo_balance.py` (determinístico; nenhum valor foi alterado).")
    add("Piso, não previsão: Sentinela no nível do Flagelo, sem equipamento, Talentos nem Artes,")
    add("só Atacar; morto volta em 2 min com vida cheia. Sem Artes de cura/Barreira e sem Defender")
    add("(exceto onde dito). O Flagelo começa cheio em cada escalonamento medido.")
    add("")
    add("## Perfil do participante (motor real)")
    add("")
    add("| Flagelo | Nv. | HP jogador | DEF | Esquiva | Ataque (média) | Ataque c/ ATQ −10% |")
    add("|---|---:|---:|---:|---:|---:|---:|")
    for code in codes:
        p = report.profiles[code]
        add(
            f"| {names[code]} | {p.level} | {p.max_hp} | {p.defense:.0f} | {p.evasion:.1f} | "
            f"{p.damage} | {p.damage_atk_debuffed} |"
        )
    add("")
    add("## 1. TTK (minutos, sem escalonamento)")
    add("")
    add("| N | " + " | ".join(names[c] for c in codes) + " |")
    add("|---:|" + "---:|" * len(codes))
    for n in PARTICIPANT_COUNTS:
        add(f"| {n} | " + " | ".join(_min(report.ttk[(c, n)].ttk_minutes) for c in codes) + " |")
    add("")
    add("## 2. Diferença relativa de TTK (÷ mediana dos seis)")
    add("")
    add("| N | " + " | ".join(names[c] for c in codes) + " | máx ÷ mín |")
    add("|---:|" + "---:|" * (len(codes) + 1))
    for n in PARTICIPANT_COUNTS:
        values = [report.ttk[(c, n)].ttk_minutes for c in codes]
        if any(v is None for v in values):
            add(f"| {n} | " + " | ".join("—" for _ in codes) + " | — |")
            continue
        ordered = sorted(values)
        median = (ordered[2] + ordered[3]) / 2
        cells = " | ".join(f"{v / median:.2f}" for v in values)
        add(f"| {n} | {cells} | {max(values) / min(values):.2f} |")
    add("")
    add("## 3. Dano recebido por participante (% do HP máximo por rodada presente) e mortes")
    add("")
    add("| N | " + " | ".join(names[c] for c in codes) + " |")
    add("|---:|" + "---:|" * len(codes))
    for n in PARTICIPANT_COUNTS:
        cells = []
        for c in codes:
            r = report.ttk[(c, n)]
            pct = r.damage_per_participant_round / report.profiles[c].max_hp * 100
            cells.append(f"{pct:.1f}% / {r.deaths}☠")
        add(f"| {n} | " + " | ".join(cells) + " |")
    add("")
    add(f"## 4. Ações isoladas contra {ABLATION_COUNT} participantes de vida cheia")
    add("")
    add("| Flagelo | Ação | Tipo | Alvos | Dano por alvo (% HP) | Dano do grupo | Efeitos / DoT |")
    add("|---|---|---|---:|---:|---:|---|")
    for region in fl.REGIONS:
        code = region.flagelo.flagelo_id
        for item in region.flagelo.actions:
            row = report.isolated[(code, item.key)]
            tipo = (
                "Preparada" if item.prepared
                else {
                    ActionKind.AOE: "AoE",
                    ActionKind.DAMAGE: "Golpe",
                    ActionKind.DAMAGE_DEBUFF: "Golpe + debuff",
                    ActionKind.SELF_BUFF: "Buff próprio",
                    ActionKind.HEAL: "Cura própria",
                }.get(item.kind, item.kind.name)
            )
            pct = D(row["per_target"]) / report.profiles[code].max_hp * 100
            extra = ", ".join(row["effects"] + row["dots"]) or "—"
            add(
                f"| {names[code]} | {item.label} | {tipo} | {row['targets']} | {pct:.1f}% | "
                f"{row['group_total']} | {extra} |"
            )
    add("")
    add(f"## 5. Peso de cada família de ações (N = {ABLATION_COUNT}, 0 passos)")
    add("")
    add("| Flagelo | Variação | TTK (min) | Δ TTK | Dano recebido total | Mortes |")
    add("|---|---|---:|---:|---:|---:|")
    for code in codes:
        base = report.ablation[(code, "base")]
        for name in ("base", "sem AoE", "sem Preparada", "sem debuffs/DoT", "sem cura própria"):
            r = report.ablation[(code, name)]
            if name == "sem cura própria" and code != "hemrath":
                continue
            delta = (
                "—" if name == "base" or r.ttk_minutes is None or base.ttk_minutes is None
                else f"{(r.ttk_minutes / base.ttk_minutes - 1) * 100:+.1f}%"
            )
            add(
                f"| {names[code]} | {name} | {_min(r.ttk_minutes)} | {delta} | "
                f"{r.damage_taken} | {r.deaths} |"
            )
    add("")
    add(f"### Participação de cada ação no dano recebido (N = {ABLATION_COUNT})")
    add("")
    add("| Flagelo | Ação | Usos | Dano recebido | % do total | Esquivados |")
    add("|---|---|---:|---:|---:|---:|")
    for code in codes:
        r = report.ablation[(code, "base")]
        total = max(1, r.damage_taken)
        for key, row in sorted(r.by_action.items(), key=lambda kv: -kv[1]["damage"]):
            label = fl.action(code, key).label
            add(
                f"| {names[code]} | {label} | {row['uses']} | {row['damage']} | "
                f"{row['damage'] * 100 / total:.1f}% | {row['dodged']} |"
            )
    add("")
    add("### Debuffs de atributo (−10%, 2 turnos), efeito direto medido")
    add("")
    add("| Flagelo | Dano do jogador com ATQ −10% | Dano recebido no golpe básico com DEF −10% |")
    add("|---|---:|---:|")
    for code in codes:
        p = report.profiles[code]
        plain = report.isolated[(code, fl.FLAGELOS_BY_ID[code].flagelo.basic_action.key)]
        weak = report.def_debuffed[code]
        add(
            f"| {names[code]} | {(p.damage_atk_debuffed / p.damage - 1) * 100:+.1f}% | "
            f"{(weak['per_target'] / plain['per_target'] - 1) * 100:+.1f}% |"
        )
    add("")
    add("### Preparada: golpe isolado, sem e com Defender")
    add("")
    add("| Flagelo | Preparada | Dano (% HP) | Com Defender | Prevenido | Mortes por golpe |")
    add("|---|---|---:|---:|---:|---|")
    for region in fl.REGIONS:
        code = region.flagelo.flagelo_id
        item = next(a for a in region.flagelo.actions if a.prepared)
        plain = report.isolated[(code, item.key)]["per_target"]
        guarded = report.prepared_defended[code]["per_target"]
        hp = report.profiles[code].max_hp
        prevented = (plain - guarded) * 100 / plain if plain else 0
        hits = -(-hp // plain)
        lethal = "sim" if plain >= hp else f"não (precisa de ≥ {hits} golpes seguidos)"
        add(
            f"| {names[code]} | {item.label} | {D(plain) * 100 / hp:.1f}% | "
            f"{D(guarded) * 100 / hp:.1f}% | {prevented:.0f}% | {lethal} |"
        )
    add("")
    hemrath = report.ablation[("hemrath", "base")]
    add("### Restituição Rubra (Hemrath, N = 10)")
    add("")
    uses = hemrath.by_action.get("restituicao_rubra", {}).get("uses", 0)
    add(f"- usos: {uses} (máximo 3); curado no total: {hemrath.healed} de {hemrath.boss_hp} HP.")
    add("")
    add(f"## 6. Escalonamento por abandono (N = {ABLATION_COUNT})")
    add("")
    add("| Flagelo | " + " | ".join(f"{s} passos" for s in SCALING_STEPS) + " | Δ 10 passos |")
    add("|---|" + "---:|" * (len(SCALING_STEPS) + 1))
    for code in codes:
        rows = [report.scaling[(code, ABLATION_COUNT, s)] for s in SCALING_STEPS]
        first, last = rows[0].ttk_minutes, rows[-1].ttk_minutes
        delta = "—" if first is None or last is None else f"{(last / first - 1) * 100:+.1f}%"
        cells = " | ".join(f"{_min(r.ttk_minutes)} min · {r.deaths}☠" for r in rows)
        add(f"| {names[code]} | {cells} | {delta} |")
    add("")
    add("## Outliers detectados")
    add("")
    add(f"Limiar: TTK fora de {OUTLIER_LOW}–{OUTLIER_HIGH}× a mediana dos seis Flagelos.")
    add("")
    if report.outliers:
        out.extend(f"- {line}" for line in report.outliers)
    else:
        add("- nenhum")
    add("")
    add("## Pontos de atenção (dados, não decisões)")
    add("")
    notes = attention(report)
    if notes:
        out.extend(f"- {line}" for line in notes)
    else:
        add("- nenhum")
    add("")
    add("Esquiva global: o Sentinela sem equipamento tem Esquiva 0, então a esquiva do Flagelo")
    add("não é exercida nesta medição (a Esquiva real depende de equipamento e Talentos).")
    add("")
    return "\n".join(out)
