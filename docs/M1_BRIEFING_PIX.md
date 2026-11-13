# Briefing M1: pagamento Pix (InfinitePay) para Patrono e Passe da Crônica

Modelo: Opus. Conversa nova. Worktree `.worktrees/pagamento-pix`, branch `feat/pagamento-pix`.

## Cole isto na conversa nova

Item M1 de `docs/PLANO_DE_ACAO.md`. Implementar a venda do Patrono de Asterion e do Passe da Crônica com Pix pela InfinitePay. Leia antes: GDD §35 e §35.1 e §35.2, §49.19 (Patrono), HANDOFF §10 (Outbox e agendador), `application/outbox.py`, `application/chronicle.py` (`pass-grant`) e `application/cosmetics.py`. Fale com o autor em português, passos curtos.

### Regras já decididas
- Sem P2W: o Patrono e o Passe só dão cosméticos e prestígio (GDD §35). Nada de XP, Coroas, combate ou progressão.
- Patrono: um único nível, entitlement de 30 dias, cumulativo a partir do maior entre agora e `patron_active_until` (GDD §49.19). O prestígio permanente por apoio acumulado (30/90/180/270/360 dias) também vem do §49.19.
- Passe da Crônica: libera a camada Premium da Trilha, inclusive retroativamente (GDD §35). Hoje só o operador ativa, pelo comando `chronicle_cli pass-grant`; reaproveitar essa lógica, não duplicar.
- Preço real é configuração comercial, fora do GDD. Proposta do autor, a confirmar: Patrono R$ 14,90 e Passe R$ 24,90. Guardar em configuração (variável de ambiente), não no código.
- GDD §35.2: cada transação usa `payment_id` único e idempotente; webhook verificado antes de processar; estados `paid`, `refunded`, `reversed` preservados; revogação auditada, nunca apagar a compra; após restore de backup, reconciliar sem duplicar entitlement.

### Provedor: InfinitePay (API de checkout)
- Criar link: `POST api.checkout.infinitepay.io/links` com `webhook_url`. Consulta de status: `/payment_check`. Documentação: https://www.infinitepay.io/checkout-documentacao
- Não achei na documentação pública se o webhook tem assinatura (HMAC). Leia a documentação oficial inteira antes de codar. Se não houver assinatura, **nunca confie só no aviso**: ao receber, consulte o status na InfinitePay pelo servidor e só então marque como pago. Confira também valor e pedido.
- Fluxo: o jogador pede o produto no bot, recebe o link de checkout, paga o Pix no banco, o webhook chega, o servidor confirma e libera sozinho.

### Entregar
1. Tabela `payment_orders` (migration): conta, produto, valor, estado, id do provedor, datas. Pedidos nunca são apagados.
2. Serviço de pedidos: criar, confirmar (idempotente por `payment_id`), expirar, reembolsar/reverter (revoga só o que o pedido concedeu, com auditoria, GDD §35.1).
3. Webhook na API FastAPI, com checagem no servidor, respondendo rápido (200 ou 400).
4. Entrega do Patrono e do Passe por transação única; aviso ao jogador pela Outbox.
5. Tela no bot: comprar, "Meus pedidos", e termos de compra aceitos antes de pagar.
6. CLI de operador para listar pedidos, reconciliar e registrar reembolso.
7. Testes, `alembic check` e Ruff limpos. Não commitar segredos (token, chave da InfinitePay vão só em variáveis de ambiente; atualizar `.env.example` com os nomes).

### Antes de codar, confirmar com o autor
- A conta InfinitePay do autor é de CPF. Perguntar se a InfinitePay libera o checkout por API para CPF.
- Regras do Telegram para venda de bens digitais em bots: verificar na hora (GDD §35.2) e avisar o autor do resultado.
- A API precisa rodar publicamente com HTTPS para receber o webhook. O `docker-compose.prod.yml` hoje só tem o bot (polling); será preciso um serviço `api` e domínio com TLS. Propor a solução (por exemplo, proxy reverso Caddy) e pedir aprovação.
- Reembolso (proposta, a aprovar): 7 dias após o pagamento, sem perguntas; benefício revogado só no que foi pago; devolução feita pelo autor na InfinitePay; após 7 dias, só por erro nosso; reembolsos repetidos geram flag para análise.

### Pronto quando
Um pagamento de teste chega ao webhook, é confirmado por consulta ao provedor, libera o benefício uma única vez (mesmo com webhook repetido) e aparece em "Meus pedidos".
