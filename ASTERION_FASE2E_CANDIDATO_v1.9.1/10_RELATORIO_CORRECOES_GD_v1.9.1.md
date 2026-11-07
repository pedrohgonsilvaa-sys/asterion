# Relatório das correções finais de Game Design — pacote candidato v1.9.1

**Data:** 2026-10-24  
**Estado:** revisão documental candidata, não canônica.

## Conferência estrutural do Weapon Metadata

O contrato v1.0.0 FINAL foi lido diretamente. A sua seção 9 contém §§9.1–9.7; a §9.7 é a auditoria das 22 armas, e não existe §9.8. Portanto, a correção proposta é: manter as tabelas atuais §§9.2–9.6, inserir Confins como §9.7 e renumerar integralmente a auditoria para §9.8. O texto candidato corrige ainda a cobertura e a contagem em §§9.1, 13.9 e 15. A distribuição proposta é 4 + 4 + 5 + 4 + 5 + 5 = 27 armas publicadas.

## Conferência das decisões de Origem

A nova tabela de §24.7 contém exatamente as seis composições aprovadas e declara vazios Acessório e Artefato em todas as Classes. As quantidades por Classe somam 34 templates (6 + 6 + 5 + 5 + 6 + 6). Ela remete aos 34 registros e atributos existentes sem recriar IDs nem valores.

A concessão foi registrada como única na criação, sem nova concessão por Legado ou recuperação. As dez operações proibidas foram nomeadas. O procedimento de recuperação continua sem especificação; nenhuma política de substituição, migração ou recuperação de último loadout foi acrescentada.

## Integridade e escopo

- IDs candidatos preservados: 226; IDs verificados em release: 0.
- Atributos individuais homologados preservados: 66 regionais e 34 de Origem.
- Os quatro totais corporais e o núcleo de Escudo foram mantidos sem alteração.
- O total global antigo HP305/ATQ56/DEF33/AGI16 foi removido apenas da regra proposta da minuta GDD; seu valor é registrado aqui como revogado, sem substituição por outro total global.
- Pendências mantidas: identidades/receitas e vínculos, publicação do contrato global e elegibilidade individual template × raridade.
- GDD v1.6.0 vigente, Weapon Metadata v1.0.0 FINAL, fontes regionais, SOURCE_AUTHORITY, código e bancos permanecem inalterados.
- **GO:** revisão documental candidata para homologação final de Game Design.
- **NO-GO:** publicação canônica, validação em release, importação, migração, ativação de flag, merge e deploy.
