---
name: project-pagamentos-decisoes
description: M1 pagamentos — InfinitePay mantida apesar da regra Stars do Telegram; Caddy aprovado; reembolso 7 dias delegado
metadata:
  node_type: memory
  type: project
  originSessionId: 650397df-7558-4332-a878-62dbb1ecace2
  modified: 2026-11-12T00:17:48.002Z
---

Decisões do item M1 (Patrono + Passe por Pix), tomadas em 2026-11-11:

- Provedor: InfinitePay. O autor foi avisado que o Telegram exige Telegram Stars para bens digitais em bots (risco de esconder o bot) e escolheu manter a InfinitePay. Não reabrir sem o autor pedir.
- HTTPS: aprovado Caddy no docker-compose.prod.yml (perfil `payments`, só a rota do webhook pública).
- Reembolso: autor delegou ("confio na sua sugestão"): 7 dias sem perguntas; depois só erro nosso; repetidos (2+) geram flag.
- Código: PR 133 (feat/pagamentos-infinitepay).
- Feito pelo autor (2026-11-11): checkout integrado ligado e API Key criada (conta CPF pode, confirmado na ajuda oficial); VPS Hostinger Ubuntu, IP 187.53.107.165; domínio asterion.net.br registrado (pagamento pendente no Registro.br); entrada DNS A `pagamentos` -> 187.53.107.165 no modo avançado.
- Próximo: instalar na VPS (Docker, .env.prod pelo próprio autor, compose com --profile payments), teste com Pix real. O bot ainda roda no PC do autor.
- Domínio: pagamentos.asterion.net.br (registro A no Registro.br). Preços aprovados pelo autor em 2026-11-12: Patrono R$ 14,90 (1490), Passe R$ 24,90 (2490). InfiniteTag: denrique. Em aberto: se conta CPF mostra "Habilitar checkout integrado".
- InfinitePay: webhook sem assinatura, sem sandbox (teste = Pix real ≥ R$ 1,00), sem estorno por API.

**Why:** evitar reabrir decisões já tomadas e lembrar o que falta para o teste real.
**How to apply:** em trabalho de pagamentos, partir destas decisões; perguntar só o que está em aberto. Ver [[project-escopo-beta]].
