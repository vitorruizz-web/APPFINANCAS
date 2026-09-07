# Finanças

PWA de planejamento financeiro pessoal. Projeta o patrimônio mês a mês e põe o
realizado ao lado do previsto.

- **App:** `index.html` (arquivo único) + `manifest.json` + `sw.js`
- **Banco:** Supabase, 9 tabelas `fin_*`, RLS `auth.uid() = user_id` em todas
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

## Rodar os testes

```bash
python -m http.server 8765
# abrir http://localhost:8765/tests/test_motor.html  -> "TUDO PASSOU"
```

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
| `db/seed.sql` | os 4 anos da planilha (gerado, fora do git) |

A proteção do dado é **RLS + cadastro de novos usuários desligado** no painel do
Supabase. A chave publicável no `index.html` é pública por design.

## Documentos

- Design: `docs/superpowers/specs/2026-09-07-app-financas-design.md`
- Plano de implementação: `docs/superpowers/plans/2026-09-07-app-financas.md`
