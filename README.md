# Finanças

PWA de planejamento financeiro pessoal. Projeta o patrimônio mês a mês e põe o
realizado ao lado do previsto.

- **App:** `index.html` (arquivo único) + `manifest.json` + `sw.js`
- **Banco:** Supabase, 9 tabelas `fin_*`, RLS `auth.uid() = user_id` em todas
- **Motor de projeção:** o bloco `/*<motor>*/` do `index.html` — função pura,
  testada contra os 48 meses da planilha original em `tests/test_motor.html`

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
