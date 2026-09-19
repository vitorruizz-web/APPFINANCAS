# Finanças

PWA de planejamento financeiro pessoal. Projeta o patrimônio mês a mês e põe o
realizado ao lado do previsto.

- **App:** `index.html` (arquivo único) + `manifest.json` + `sw.js`
- **Banco:** Supabase, 10 tabelas `fin_*`, RLS `auth.uid() = user_id` em todas
- **Motor de projeção:** o bloco `/*<motor>*/` do `index.html` — função pura,
  testada contra os 48 meses da planilha original em `tests/test_motor.html`
- **Agregações por conta:** o bloco `/*<contas>*/` — composição, variação e série
  empilhada, testadas no mesmo arquivo

## Apuração por conta

Até **08/2026** o realizado vem da planilha (`fin_months.realizado_override`), e o
motor dá prioridade a ele. De **09/2026** em diante não há override: o patrimônio
apurado **é** a soma dos saldos apontados conta a conta em Patrimônio → *Apontar*.

Um mês só vira apurado com **todas** as contas do mês preenchidas — com 4 de 6 ele
continua em aberto, porque somar parte das contas registraria um patrimônio menor
que o real. Saldo zero conta como preenchido; em branco, não.

A sub-aba *Análise* mostra composição, variação contra o mês apurado anterior,
evolução empilhada e a trajetória de cada conta. A cor segue a **conta** (ordem de
cadastro), nunca o tamanho dela. A rampa está no bloco `<contas>` e foi validada
contra o fundo `#0A0D11`: pior par adjacente ΔE 12,8 sob daltonismo (alvo 8), 23,2
em visão normal (piso 15), contraste ≥ 3:1 nas seis. **Reordenar exige revalidar.**

## Vencimentos (CDBs)

A aba mostra, dia a dia, **quanto cai na conta** com os CDBs que vencem: o valor
líquido projetado de cada um no vencimento, os juros dos CDBs de juros mensais, e o
valor estimado da carteira HOJE (o saldo da planilha corrigido pela taxa desde a data
da posição). A posição vem da planilha da corretora, subida pela própria aba
(*Atualizar posição*) — ela substitui a posição inteira.

**Colunas da planilha** (.xlsx ou .csv; o app acha a linha de títulos sozinho e
ignora colunas a mais):

| Coluna | Obrigatória | Exemplo |
|---|---|---|
| CDB (ou Ativo, Nome…) | sim | `CDB BANCO X - NOV/2027` — "JURO MENSAL" no nome liga os juros mensais |
| Rentabilidade (ou Taxa…) | sim | `+15,50%` (pré a.a.) · `120,00% CDI` · `CDI + 1,5%` |
| Data vencimento | sim | `24/11/2027` |
| Saldo líquido (ou Valor líquido) | sim | `R$ 3.702,38` |
| Data aplicação | não | deixa o IR exato |
| Valor aplicado | não | deixa o IR exato |

Sem a data de aplicação, o rendimento daqui até o vencimento paga o **IR presumido**
(15% por padrão, ajustável em Premissas).

**Taxas** (Banco Central, sem chave, CORS liberado): CDI publicado (SGS 4389), Selic
meta (SGS 432, que vem preenchida até o dia da próxima reunião do Copom) e as
medianas do Focus (Olinda). A curva do CDI tem três camadas: o CDI que **já valeu**,
dia útil a dia útil; a Selic meta **já decidida** até a próxima reunião; e o
**futuro** pelo Focus (padrão), pela Selic de hoje ou por uma Selic digitada. Uma
mudança de Selic entra no dia em que vigorou — o passado não muda. As taxas ficam em
cache no aparelho (`localStorage`), não no banco.

O cálculo mora no bloco `/*<vencimentos>*/` do `index.html` (função pura: dias úteis
ANBIMA, IR regressivo, curva do CDI, projeção, leitura da planilha) e o leitor de
arquivo no bloco `/*<xlsx>*/` (ZIP + `DecompressionStream` + `DOMParser`, sem
biblioteca).

## Rodar os testes

```bash
python -m http.server 8765
# abrir http://localhost:8765/tests/test_motor.html        -> "TUDO PASSOU"
# abrir http://localhost:8765/tests/test_vencimentos.html  -> "TUDO PASSOU"
```

`tests/test_vencimentos.html` usa só CDBs inventados. A conferência com a planilha
real (`tests/_real/`: `conferir.py` projeta por um caminho independente em Python e
`test_planilha_real.html` compara com o app) fica **fora do git**.

## Preview local com os dados reais (sem tocar no banco)

```bash
python tools/importar_planilha.py --gerar   # gera db/seed.sql, tests/fixtures.json, tests/mock.json
python tools/gerar_preview.py               # gera tests/preview.html
# abrir http://localhost:8765/tests/preview.html
```

Para mexer na **análise por conta** os dados reais não servem: o apontamento só
começa em 09/2026, então os quatro gráficos abrem vazios. Use o mock sintético,
que traz 3 meses completos e 1 pela metade:

```bash
python tools/gerar_mock_sintetico.py        # numeros inventados, sobrescreve tests/mock.json
python tools/gerar_preview.py
```

`tests/preview.html`, `tests/mock.json`, `db/seed.sql` e a planilha ficam **fora
do repositório** (`.gitignore`): o repo é público e não guarda dado financeiro.

## Banco

| Arquivo | O que faz |
|---|---|
| `db/schema.sql` | as 8 tabelas base, constraints, índices e RLS |
| `db/002_compromissos.sql` | `fin_installments` (parcelas) + RLS |
| `db/006_cdbs.sql` | `fin_cdbs` (posição de CDBs da aba Vencimentos) + RLS |
| `db/seed.sql` | os 4 anos da planilha (gerado, fora do git) |

A proteção do dado é **RLS + cadastro de novos usuários desligado** no painel do
Supabase. A chave publicável no `index.html` é pública por design.

## Documentos

- Design: `docs/superpowers/specs/2026-09-07-app-financas-design.md`
- Plano de implementação: `docs/superpowers/plans/2026-09-07-app-financas.md`
