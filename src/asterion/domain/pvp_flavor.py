"""Micro-combat Flavor Text for PvP results (GDD §49.17; Crônica I proposal §10).

40–120 characters, no spoiler layer. The line is chosen from a stable seed, so the
same result screen always shows the same line.
"""

from __future__ import annotations

import hashlib

PVP_FLAVOR: dict[str, dict[str, tuple[str, ...]]] = {
    "arena": {
        "win": (
            "A Vigília registra seu nome. Amanhã, alguém virá buscá-lo.",
            "Você continua de pé. Ninguém aplaude; a Vigília apenas anota.",
            "O Renome sobe como brasa soprada: quente agora, frágil depois.",
        ),
        "loss": (
            "Caído, você ouve a Vigília anotar. Derrota também é registro.",
            "A Arena guarda mais nomes vencidos que vitoriosos.",
            "Levante-se. A janela ainda está aberta, e o erro já tem nome.",
        ),
        "draw": (
            "Caíram juntos. A Vigília registra dois nomes na mesma linha.",
            "Nenhum dos dois ficou de pé. Nenhum dos dois perdeu sozinho.",
            "A pedra não decide o que os golpes não decidiram.",
        ),
    },
    "duel": {
        "win": (
            "O desafio foi aceito e respondido. A última palavra é sua.",
            "O outro sabe agora o que você sabe.",
            "Lâmina baixa, fôlego curto: a vitória pesa menos que o golpe.",
        ),
        "loss": (
            "Você aceitou o duelo e perdeu. Aceitar já foi coragem.",
            "Perder um duelo é aprender o preço exato de um erro.",
            "A mão estendida, ou não. A derrota é sua de qualquer jeito.",
        ),
        "draw": (
            "Dois corpos no chão, nenhum vencedor. O desafio continua aberto.",
            "Caíram ao mesmo tempo. Fica a pergunta para outro dia.",
            "Ninguém venceu. Os dois vão lembrar.",
        ),
    },
    "guild_battle": {
        "win": (
            "As frentes cederam do outro lado. Hoje, a Guilda se manteve.",
            "A vitória pertence a todos os nomes que estavam na linha.",
            "Vitória registrada. Na próxima noite, será preciso merecê-la de novo.",
        ),
        "loss": (
            "A Guilda recua junta. Ninguém perde sozinho numa batalha assim.",
            "As frentes caíram. Contem os feridos, não os culpados.",
            "Derrota registrada. A próxima batalha começa com esta lição.",
        ),
        "draw": (
            "Nenhuma Guilda cedeu. A noite termina sem vencedor.",
            "Frente por frente, golpe por golpe: tudo igual até o fim.",
            "As duas Guildas partem sabendo quanto a outra vale.",
        ),
    },
}


def pvp_flavor(mode: str, outcome: str, seed: str) -> str:
    lines = PVP_FLAVOR[mode][outcome]
    index = int.from_bytes(hashlib.sha256(seed.encode()).digest()[:4], "big") % len(lines)
    return lines[index]
