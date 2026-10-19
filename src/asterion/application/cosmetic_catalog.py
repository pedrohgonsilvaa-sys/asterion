"""Stable presentation metadata for regional cosmetic collections."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CosmeticDefinition:
    cosmetic_id: str
    cosmetic_type: str
    name: str
    achievement_id: str | None

    @property
    def origin(self) -> str:
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
        "cosmetic.banner.tdo.profundezas_do_ocaso",
        "banner",
        "Profundezas do Ocaso",
        "feat.tdo.sob_a_superficie",
    ),
    CosmeticDefinition(
        "cosmetic.title.tdo.vigia_das_cinzas",
        "title",
        "Vigia das Cinzas",
        "feat.tdo.a_ultima_guarda",
    ),
    CosmeticDefinition(
        "cosmetic.emblem.tdo.lapide_raspada",
        "emblem",
        "Lápide Raspada",
        "feat.tdo.silencio_entre_os_nomes",
    ),
    CosmeticDefinition(
        "cosmetic.emblem.tdo.selo_fraturado",
        "emblem",
        "Selo Fraturado",
        "feat.tdo.a_ordem_interrompida",
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
        "cosmetic.banner.tdo.ultima_vigilia",
        "banner",
        "Última Vigília",
        "feat.tdo.testemunha_dos_guardioes",
    ),
    CosmeticDefinition(
        "cosmetic.emblem.tdo.nome_apagado",
        "emblem",
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
        "cosmetic.banner.tdo.ocaso",
        "banner",
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
)

COSMETICS_BY_ID = {item.cosmetic_id: item for item in COSMETICS}
COSMETIC_BY_ACHIEVEMENT = {
    item.achievement_id: item for item in COSMETICS if item.achievement_id is not None
}
COSMETIC_TYPES = ("appearance", "title", "emblem", "frame", "banner")
COSMETIC_TYPE_LABELS = {
    "appearance": "🧍 Aparência · Visual",
    "title": "🎖️ Título · Identidade",
    "emblem": "🔰 Emblema · Distinção",
    "frame": "🖼️ Moldura · Perfil",
    "banner": "🏳️ Banner · Exibição",
}
COSMETIC_TYPE_NOUNS = {
    "appearance": "Aparência",
    "title": "Título",
    "emblem": "Emblema",
    "frame": "Moldura",
    "banner": "Banner",
}
COSMETIC_USE_BUTTONS = {
    "appearance": "Usar Aparência",
    "title": "Usar Título",
    "emblem": "Usar Emblema",
    "frame": "Usar Moldura",
    "banner": "Usar Banner",
}
