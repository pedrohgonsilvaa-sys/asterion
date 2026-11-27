"""Stable presentation metadata for regional cosmetic collections."""

from dataclasses import dataclass

from asterion.domain.chronicle import CHRONICLE_COSMETICS
from asterion.domain.guild_battle import GUILD_BATTLE_COSMETICS
from asterion.domain.payments import PATRON_COSMETICS


@dataclass(frozen=True, slots=True)
class CosmeticDefinition:
    cosmetic_id: str
    cosmetic_type: str
    name: str
    achievement_id: str | None
    origin_label: str | None = None
    # Especificação consolidada 2026-11-26, Parte IV §3–§5: Raridade e descrição só
    # aparecem quando a Fonte as define; nenhum valor é inventado.
    rarity: str | None = None
    description: str | None = None

    @property
    def origin(self) -> str:
        if self.origin_label:
            return self.origin_label
        if self.achievement_id:
            return f"Feito · {self.achievement_id}"
        return "Concessão não definida pela Fonte"


COSMETICS = (
    CosmeticDefinition(
        "cosmetic.title.nareth.andarilho_de_nareth",
        "title",
        "Andarilho de Nareth",
        "feat.nareth.andarilho_de_nareth",
    ),
    CosmeticDefinition(
        "cosmetic.title.nareth.sobrevivente_do_eixo",
        "title",
        "Sobrevivente do Eixo",
        "feat.nareth.a_camara_se_cala",
    ),
    CosmeticDefinition(
        "cosmetic.frame.nareth.eixo_fraturado",
        "frame",
        "Eixo Fraturado",
        "feat.nareth.eixos_fraturados",
    ),
    CosmeticDefinition(
        "cosmetic.title.nareth.cacador_de_nareth",
        "title",
        "Caçador de Nareth",
        "feat.nareth.cacador_de_nareth",
    ),
    CosmeticDefinition(
        "cosmetic.appearance.nareth.sobrevivente_de_nareth",
        "appearance",
        "Sobrevivente de Nareth",
        "feat.nareth.horizonte_sem_norte",
    ),
    CosmeticDefinition(
        "cosmetic.title.nareth.sem_norte",
        "title",
        "Sem Norte",
        "feat.nareth.os_caminhos_que_nao_coincidem",
    ),
    CosmeticDefinition(
        "cosmetic.frame.nareth.meridiano_antigo",
        "frame",
        "Meridiano Antigo",
        "feat.nareth.a_rede_mede_ainda",
    ),
    CosmeticDefinition(
        "cosmetic.frame.nareth.planicies_de_nareth",
        "frame",
        "Planícies de Nareth",
        "feat.nareth.planicies_de_nareth",
    ),
    CosmeticDefinition(
        "cosmetic.title.tdo.andarilho_das_cinzas",
        "title",
        "Andarilho das Cinzas",
        "feat.tdo.andarilho_das_cinzas",
    ),
    CosmeticDefinition(
        "cosmetic.title.tdo.vigia_das_cinzas",
        "title",
        "Vigia das Cinzas",
        "feat.tdo.a_ultima_guarda",
    ),
    CosmeticDefinition(
        "cosmetic.frame.tdo.pedra_fraturada",
        "frame",
        "Pedra Fraturada",
        "feat.tdo.cinzas_fraturadas",
    ),
    CosmeticDefinition(
        "cosmetic.title.tdo.cacador_do_ocaso",
        "title",
        "Caçador do Ocaso",
        "feat.tdo.cacador_do_ocaso",
    ),
    CosmeticDefinition(
        "cosmetic.appearance.tdo.errante_das_cinzas",
        "appearance",
        "Errante das Cinzas",
        "feat.tdo.entre_aquilo_que_caca",
    ),
    CosmeticDefinition(
        "cosmetic.title.tdo.nome_apagado",
        "title",
        "Nome Apagado",
        "feat.tdo.nomes_sob_a_cinza",
    ),
    CosmeticDefinition(
        "cosmetic.frame.tdo.vigilia_antiga",
        "frame",
        "Vigília Antiga",
        "feat.tdo.a_ordem_ainda_permanece",
    ),
    CosmeticDefinition(
        "cosmetic.frame.tdo.ocaso",
        "frame",
        "Ocaso",
        "feat.tdo.terras_do_ocaso",
    ),
    CosmeticDefinition(
        "cosmetic.title.vde.andarilho_dos_vales",
        "title",
        "Andarilho dos Vales",
        "feat.vde.andarilho_dos_vales",
    ),
    CosmeticDefinition(
        "cosmetic.title.vde.sobrevivente_do_berco",
        "title",
        "Sobrevivente do Berço",
        "feat.vde.o_berco_silencia",
    ),
    CosmeticDefinition(
        "cosmetic.title.vde.cacador_dos_vales",
        "title",
        "Caçador dos Vales",
        "feat.vde.cacador_dos_vales",
    ),
    CosmeticDefinition(
        "cosmetic.title.vde.nome_entalhado",
        "title",
        "Nome Entalhado",
        "feat.vde.nomes_presos_madeira",
    ),
    CosmeticDefinition(
        "cosmetic.frame.vde.vales_dos_enforcados",
        "frame",
        "Vales dos Enforcados",
        "feat.vde.vales_dos_enforcados",
    ),
    CosmeticDefinition(
        "cosmetic.frame.vde.pedra_enlacada",
        "frame",
        "Pedra Enlaçada",
        "feat.vde.a_rede_nao_dorme",
    ),
    CosmeticDefinition(
        "cosmetic.frame.vde.raiz_fraturada",
        "frame",
        "Raiz Fraturada",
        "feat.vde.raizes_fraturadas",
    ),
    CosmeticDefinition(
        "cosmetic.appearance.vde.sobrevivente_dos_vales",
        "appearance",
        "Sobrevivente dos Vales",
        "feat.vde.entre_galhos_e_presas",
    ),
    CosmeticDefinition(
        "cosmetic.title.varzeas.andarilho_da_salmoura",
        "title",
        "Andarilho da Salmoura",
        None,
    ),
    CosmeticDefinition(
        "cosmetic.title.varzeas.guardiao_dos_diques",
        "title",
        "Guardião dos Diques",
        None,
    ),
    CosmeticDefinition(
        "cosmetic.title.varzeas.testemunha_de_hemaris",
        "title",
        "Testemunha de Hemaris",
        None,
    ),
    CosmeticDefinition(
        "cosmetic.title.varzeas.persistente_sem_protocolo",
        "title",
        "Persistente sem Protocolo",
        None,
    ),
    CosmeticDefinition(
        "cosmetic.frame.varzeas.ferruginosa", "frame", "Moldura Ferruginosa", None
    ),
    CosmeticDefinition(
        "cosmetic.frame.varzeas.vidro_escurecido",
        "frame",
        "Moldura de Vidro Escurecido",
        None,
    ),
    CosmeticDefinition(
        "cosmetic.appearance.varzeas.sobrevivente",
        "appearance",
        "Sobrevivente das Várzeas",
        None,
    ),
    CosmeticDefinition(
        "cosmetic.appearance.varzeas.capa_porto_salmoura",
        "appearance",
        "Capa do Porto da Salmoura",
        None,
    ),
    CosmeticDefinition(
        "cosmetic.title.confins.testemunha_rota",
        "title",
        "Testemunha de Rota",
        "achievement.confins.primeira_marcha",
    ),
    CosmeticDefinition(
        "cosmetic.title.confins.leitor_incoerencias",
        "title",
        "Leitor de Incoerências",
        "achievement.confins.avesso_nomeado",
    ),
    CosmeticDefinition(
        "cosmetic.frame.confins.arquivo_duplo",
        "frame",
        "Arquivo Duplo",
        "achievement.confins.cadeia_ruptura",
    ),
    CosmeticDefinition(
        "cosmetic.frame.confins.ultima_referencia",
        "frame",
        "Última Referência",
        "achievement.confins.regente_primeira",
    ),
    CosmeticDefinition(
        "cosmetic.title.confins.guardiao_testemunhas",
        "title",
        "Guardião de Testemunhas",
        "achievement.confins.s36",
    ),
    CosmeticDefinition(
        "cosmetic.appearance.confins.viajante_veu",
        "appearance",
        "Viajante do Véu",
        "achievement.confins.regiao",
    ),
    *(
        CosmeticDefinition(cosmetic_id, kind, name, None, "Chamado de Asterion")
        for cosmetic_id, kind, name in (
            ("cosmetic.title.chamado.guia_da_estrada", "title", "Guia da Estrada"),
            ("cosmetic.title.chamado.voz_que_reune", "title", "Voz que Reúne"),
            ("cosmetic.frame.chamado.laco_das_cinzas", "frame", "Laço das Cinzas"),
            (
                "cosmetic.frame.chamado.circulo_dos_caminhantes",
                "frame",
                "Círculo dos Caminhantes",
            ),
            (
                "cosmetic.appearance.chamado.arauto_de_asterion",
                "appearance",
                "Arauto de Asterion",
            ),
        )
    ),
    *(
        CosmeticDefinition(
            item.cosmetic_id, item.cosmetic_type, item.name, None, "Trilha da Crônica"
        )
        for item in CHRONICLE_COSMETICS
    ),
    *(
        CosmeticDefinition(cosmetic_id, cosmetic_type, name, None, "Batalha de Guildas")
        for cosmetic_id, cosmetic_type, name in GUILD_BATTLE_COSMETICS
    ),
    *(
        CosmeticDefinition(cosmetic_id, cosmetic_type, name, None, "Patrono de Asterion")
        for cosmetic_id, cosmetic_type, name in PATRON_COSMETICS
    ),
)

COSMETICS_BY_ID = {item.cosmetic_id: item for item in COSMETICS}
COSMETIC_BY_ACHIEVEMENT = {
    item.achievement_id: item for item in COSMETICS if item.achievement_id is not None
}
# Only three player-facing categories exist (GDD 33.4). ``emblem`` and ``banner``
# survive solely as legacy values in the database and are never listed.
COSMETIC_TYPES = ("appearance", "title", "frame")
COSMETIC_TYPE_LABELS = {
    "appearance": "🧍 Aparência · Visual",
    "title": "🎖️ Título · Identidade",
    "frame": "🖼️ Moldura · Perfil",
}
COSMETIC_TYPE_NOUNS = {
    "appearance": "Aparência",
    "title": "Título",
    "frame": "Moldura",
}
# Parte IV §8: ``✅ Usar`` é o padrão para equipar cosméticos.
COSMETIC_USE_BUTTONS = {
    "appearance": "✅ Usar",
    "title": "✅ Usar",
    "frame": "✅ Usar",
}
# Player-facing name of the starting appearance (UI 7). It is not a catalog entry:
# it is what the character shows when no Appearance is selected.
DEFAULT_APPEARANCE_NAME = "Viajante de Asterion"


@dataclass(frozen=True, slots=True)
class InitialCosmetic:
    """Aparência e Título iniciais: não são itens do catálogo, valem sem seleção."""

    name: str
    description: str
    rarity: str
    origin: str
    closing: str | None = None


# Textos, Raridade e Origem fechados na especificação consolidada (Parte IV §3.1, §4.1).
INITIAL_APPEARANCE = InitialCosmetic(
    DEFAULT_APPEARANCE_NAME,
    "O visual simples de quem atravessa Asterion sem pertencer a lugar algum.",
    "Comum",
    "Aparência Inicial",
    "Uma aparência marcada pela estrada, pelas cinzas e pelos primeiros passos de uma "
    "longa jornada.",
)
INITIAL_TITLE = InitialCosmetic(
    "Caminhante das Cinzas",
    "O primeiro título de quem atravessou as cinzas e encontrou um caminho onde antes "
    "havia apenas ruínas.",
    "Comum",
    "Prólogo",
)
# Legacy TDO cosmetics converted to their canonical equivalent (GDD 33.4, TDO 17).
LEGACY_COSMETIC_CONVERSIONS = {
    "cosmetic.emblem.tdo.nome_apagado": "cosmetic.title.tdo.nome_apagado",
    "cosmetic.banner.tdo.ocaso": "cosmetic.frame.tdo.ocaso",
}
# Legacy TDO cosmetics with no canonical equivalent: rows are kept, never listed or granted.
RETIRED_LEGACY_COSMETICS = (
    "cosmetic.emblem.tdo.lapide_raspada",
    "cosmetic.emblem.tdo.selo_fraturado",
    "cosmetic.banner.tdo.profundezas_do_ocaso",
    "cosmetic.banner.tdo.ultima_vigilia",
)
