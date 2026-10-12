"""Stable presentation metadata for the TDO cosmetic collection."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CosmeticDefinition:
    cosmetic_id: str
    cosmetic_type: str
    name: str
    achievement_id: str

    @property
    def origin(self) -> str:
        return f"Feito · {self.achievement_id}"


COSMETICS = (
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
        "cosmetic.title.vde.sobrevivente_do_berco",
        "title",
        "Sobrevivente do Berço",
        "feat.vde.o_berco_silencia",
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
)

COSMETICS_BY_ID = {item.cosmetic_id: item for item in COSMETICS}
COSMETIC_BY_ACHIEVEMENT = {item.achievement_id: item for item in COSMETICS}
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
