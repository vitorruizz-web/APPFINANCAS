# Finanças

PWA de planejamento financeiro pessoal. Projeta o patrimônio mês a mês e põe o
realizado ao lado do previsto.

- **App:** `index.html` (arquivo único) + `manifest.json` + `sw.js`
- **Banco:** Supabase, 11 tabelas `fin_*`, RLS `auth.uid() = user_id` em todas
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
| CDB (ou Ativo, Nome…) | sim | `CDB BANCO X - MAR/2028` — "JURO MENSAL" no nome liga os juros mensais |
| Rentabilidade (ou Taxa…) | sim | `+15,50%` (pré a.a.) · `120,00% CDI` · `CDI + 1,5%` |
| Data vencimento | sim | `15/03/2028` |
| Saldo líquido (ou Valor líquido) | sim | `R$ 2.480,15` |
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

**Posição direto da XP e do BTG (Open Finance).** A fonte principal é o Open Finance, via
[Meu Pluggy](https://www.pluggy.ai/meu-pluggy) (grátis para uso pessoal, até 5 conexões,
renova a cada 24 h). A chave da Pluggy não pode ir ao navegador, então quem fala com ela é a
Edge Function [`supabase/functions/pluggy-cdbs`](supabase/functions/pluggy-cdbs/index.ts): o app
chama com o JWT do usuário, recebe só os campos que usa, mapeia com `VENC.lerPluggy` e grava
em `fin_cdbs` com a mesma regra da planilha (lote novo, depois apaga os antigos). A aba
sincroniza sozinha se a posição tiver mais de 6 h; uma corretora que falhar mantém a posição
anterior (e a tela avisa). Entra a renda fixa bancária (CDB, RDB, LC, LCI, LCA — LCI/LCA sem
IR); Tesouro, debêntures e CRI/CRA ficam fora, com aviso. A planilha continua como plano B.

**A taxa que o Open Finance manda é a da EMISSÃO do título**, não a de quem comprou depois
no mercado secundário, que é a taxa em que o saldo realmente cresce. Por isso a função também
traz as movimentações de cada título, e o app calcula a taxa da **compra** pelo próprio saldo
(`VENC.dePluggy`): no prefixado, com uma compra só, `(bruto de hoje / valor aplicado)^(252 /
dias úteis desde a compra) − 1`; no CDI, o percentual que leva o aplicado ao bruto de hoje pelo
CDI que valeu em cada dia útil (histórico do BC — se ele ainda não cobre a compra, fica a taxa
da emissão até a próxima sincronização). Conferido com a planilha da XP em 19/09/2026: dos 105
prefixados com a compra registrada, 102 batem em 0,01 ponto (os 3 restantes vencem no dia útil
seguinte), e os 49 do CDI com compra batem em 0,05 ponto. Título que quase não cresceu desde a
compra paga **juros todo mês** (o cupom sai do saldo) e é marcado sozinho. Vários lotes no
mesmo dia contam como uma compra.

Sem a compra na janela do Open Finance (a XP manda ~12 meses de movimentações; o BTG, ~3), o
prefixado vai **pelo resgate da emissão**: quantidade × PU de emissão (R$ 1.000, ou R$ 1 no
fracionado) × (1 + taxa da emissão)^(du/252) é o que o título paga no vencimento, e a taxa de
quem o tem é a que leva o bruto de hoje até lá (a data da compra sai de trás para a frente). Isso
só vale onde a corretora manda a emissão certa: o app confere, em cada corretora, nos títulos que
têm compra — em 19/09/2026 a XP bateu 102 de 102; o BTG não confere, e fica a taxa da emissão.
A Conexões mostra de onde veio a taxa de cada título.

Configuração (uma vez):

1. `dashboard.pluggy.ai`: criar conta e time (teste de 15 dias); em *Customize*, pôr o conector
   **MeuPluggy** na lista; criar uma *Application* → **Client ID** e **Client Secret**.
2. `meu.pluggy.ai`: criar conta e conectar a **XP** e o **BTG** (consentimento no app de cada um).
3. Na Application (*Pluggy Demo App*): **Demo** → **Conectar Conta** → **MeuPluggy** → autorizar
   a conexão do banco (a janela do Meu Pluggy abre à parte), **uma vez por banco**. O Item ID
   aparece em *Itens Conectados* (menu ⋮ → **Copiar Item ID**). ⚠ Os passos 2 e 3 só funcionam
   durante o teste de 15 dias.
4. Supabase → Edge Functions: publicar `pluggy-cdbs` e, em *Secrets*, `PLUGGY_CLIENT_ID`,
   `PLUGGY_CLIENT_SECRET` (em *Credenciais* da Application) e `PLUGGY_ITEM_IDS` **com o nome da
   corretora na frente de cada id**: `XP:<id>,BTG:<id>`. Pelo Meu Pluggy todo item se chama
   "MeuPluggy"; sem o nome, a corretora que falhar não tem como manter a posição dela.
   Opcional: `DONO_UID` (uid do usuário do app).

Para somar outra corretora depois: passo 2 (conectar no Meu Pluggy), passo 3 (autorizar no Demo e
copiar o Item ID) e trocar o valor de `PLUGGY_ITEM_IDS` por `XP:<id>,BTG:<id-novo>`.

O consentimento do Open Finance vence (até 12 meses): a aba avisa 30 dias antes; renova-se no
Meu Pluggy.

**Rendimento mês a mês** (chave *Calendário | Rendimento* na aba): quanto a carteira rendeu em
cada mês, bruto e líquido. Com a data e o valor aplicados (Open Finance), o **passado** é
reconstruído desde a aplicação de cada título, pela taxa da compra e pelo CDI que valeu em cada
dia (o app busca pelo menos 2 anos de histórico no BC, em pedaços de um ano, com prazo de 25 s por
pedido); o futuro é a mesma projeção do calendário. Cálculo em `VENC.rendimentoMensal`.

- **Quem comprou antes da janela do Open Finance** ganha a data de compra de trás para a frente
  (o aplicado crescendo pela taxa — ou pelo CDI — até o bruto de hoje), conferida com a faixa de
  IR que a corretora provisiona.
- **Os que já venceram entram até o vencimento**: a função traz as movimentações de quem venceu
  no último ano; com a compra na janela, o título vira uma linha com `resgate` preenchido em
  `fin_cdbs` (migração 007), fora do calendário e da posição, e **fica guardado** — o app leva essas
  linhas de uma importação para a outra, porque o Open Finance para de mostrar o título.
- **Mês parcial**: antes do mês em que o histórico fica completo (depois do último vencimento sem
  a compra na janela, e nunca antes do primeiro vencimento que o Open Finance ainda mostra), o mês
  aparece como "parcial" — o valor é "pelo menos isso". Daqui para a frente, os meses fecham
  completos.

**Instituições** (terceira chave da aba): quanto há em cada emissor diante do limite do FGC —
R$ 250 mil por CPF por instituição **ou conglomerado**, principal + rendimento até o dia de uma
quebra, com teto de R$ 1 milhão a cada 4 anos. Conta o emissor, não a corretora: o mesmo banco na
XP e no BTG soma junto. Cálculo em `VENC.porInstituicao`.

- **Valor bruto na curva** (antes do IR) e **pico**: o maior valor que a instituição atinge se nada
  for reaplicado. Entre um crédito e o seguinte o valor só cresce, então o pico é calculado só em
  hoje e nos dias de crédito/cupom; a data em que passa do limite sai por bisseção.
- **Situação**: *Dentro*, *Atenção* (a projeção passa do limite ou já usa 90%) e *Acima*. O Resumo
  avisa quando alguma passa do limite, hoje ou na projeção.
- **Agrupamento**: o nome do emissor é normalizado (sem "BANCO", "S.A.", "FINANCEIRA"...), quem
  tem o mesmo primeiro nome soma junto (na dúvida, somar é o lado seguro) e a tabela
  `CONGLOMERADOS` junta os grupos de nomes diferentes (ex.: BTG + Pan) — conglomerado prudencial do
  BC, conferido no IF.data de jun/2026 e na lista de associadas do FGC de 08/2026; rever de tempos
  em tempos. *Juntar* e *Separar* na tela ficam em `settings.venc.fgcJuntar` (sem migração).
- Letra Financeira e LIG não têm FGC: ficam fora da soma, com aviso.

O cálculo mora no bloco `/*<vencimentos>*/` do `index.html` (função pura: dias úteis
ANBIMA, IR regressivo, curva do CDI, projeção, leitura da planilha) e o leitor de
arquivo no bloco `/*<xlsx>*/` (ZIP + `DecompressionStream` + `DOMParser`, sem
biblioteca).

## Simulações

Na aba **Plano**, *Nova simulação* abre um "e se…" que **não mexe no plano**: uma
lista de alterações aplicada por cima dele e calculada pelo mesmo motor. Se o plano
mudar depois, a simulação acompanha — só o que ela altera fica diferente.

| Tipo | Exemplo |
|---|---|
| Valor de um mês | Viagens em jun/2027 = R$ 30 mil |
| Daqui para a frente | Pró-labore +10% (ou "passa a R$ X") a partir de jan/2027, fim opcional |
| Gasto ou receita pontual | Carro novo: R$ 80 mil em jun/2027 |
| Parcelado | Financiamento: 48× R$ 2.500 a partir de jan/2027 |
| Taxa de rendimento | Rendimentos a 0,65% ao mês a partir de jan/2027 |

No mesmo mês e categoria, o valor de um mês vence a série; porcentagens se acumulam
(+10% e depois +5% = ×1,155). Rendimentos não aceita %: o valor dele depende do
saldo, que depende da própria simulação — para isso existe a taxa, que vira a única
regra da categoria a partir do mês escolhido.

A tela mostra onde cada ano termina no plano × na simulação, o gráfico dos 12 meses
(plano em linha contínua, simulação tracejada em violeta `#8D7AF0`) e a tabela do
ano, em que tocar numa célula cria uma alteração.

**Salvar** guarda só como simulação (`fin_simulations`, migração 008) ou guarda e
**torna o plano oficial**: as alterações viram valores em `fin_plan`, compromissos
em `fin_installments` e regras em `fin_rules`, com os mesmos números, arredondados
na precisão de cada coluna — o que a simulação mostrava é o que o plano passa a
mostrar. Antes de tocar no plano, o app grava o registro para **desfazer**, que
nunca desfaz o que foi mudado depois. Oficializada, a simulação vira histórico:
aplicá-la de novo contaria o parcelado duas vezes.

Tornar oficial e desfazer **decidem pelo banco, não pela memória**: antes de gravar,
o app recarrega tudo (um celular com o app aberto há dias, ou uma resposta perdida no
meio de uma gravação, deixaria a memória diferente do banco). O primeiro passo é um
PATCH condicional — se outro aparelho oficializou antes, nada é gravado —, e parcelas
e regras novas vão com upsert por id, então repetir um pedido não duplica. Desfazer só
na ordem inversa (a oficializada mais nova primeiro): uma taxa oficializada depois pode
ter encerrado a regra que a mais antiga devolveria.

Limitação conhecida: uma série "daqui para a frente" sem fim, ao virar oficial, grava um
valor em cada mês **até o fim do horizonte daquele dia**. Se depois o horizonte for
estendido, os meses novos seguem o plano de antes — o mesmo que já acontece com "Repetir
este valor até o fim".

O cálculo mora no bloco `/*<simulacao>*/` (função pura, `tests/test_simulacao.html`).

## Dividendos

Aba própria com o que entrou de dividendos em cada mês. **Não há tabela nova:** o
recebido do mês é a soma dos lançamentos (`fin_entries`) da categoria de receita
**Dividendos** — por isso ele aparece sozinho como apurado de Dividendos na aba Mês, e o
previsto vem do plano (regras incluídas). Mês sem lançamento é vazio; lançamento 0 é zero.

- **Destaque do mês escolhido:** contra o mês anterior, contra o mesmo mês do ano
  anterior e contra o previsto no plano; últimos 12 meses (soma, média, variação contra
  os 12 anteriores).
- **Gráfico:** barras ouro = recebido, traço tiffany = previsto. Um eixo só — a variação %
  fica no destaque e na tabela. Toque, arrasto ou setas escolhem o mês.
- **Ano contra ano:** total de cada ano (ano parcial marcado) e o acumulado do ano contra
  os mesmos meses do ano anterior.
- **Tabela** (cabeçalho preso, mais recente no topo): a célula *Recebido* lança o mês.
  Sem lançamento → cria um "Total do mês"; com um → altera ou apaga (campo vazio); com
  dois ou mais → abre a lista do mês, porque não dá para adivinhar qual mudar.
- **Importar planilha:** lê a aba *Lançamento* pelas colunas *Liquidação* e *Valor*, soma
  por mês e mostra o resumo antes de gravar. Mês que já tem lançamento fica como está —
  importar de novo não duplica.

Com 7 abas, o nome da aba ativa não cabe em todo celular: `ajustarNav()` **mede** a barra
e só onde não couber deixa a aba ativa com o ícone.

O cálculo mora no bloco `/*<dividendos>*/` (função pura, `tests/test_dividendos.html`).

## Rodar os testes

```bash
python -m http.server 8765
# abrir http://localhost:8765/tests/test_motor.html        -> "TUDO PASSOU"
# abrir http://localhost:8765/tests/test_vencimentos.html  -> "TUDO PASSOU"
# abrir http://localhost:8765/tests/test_simulacao.html    -> "TUDO PASSOU"
# abrir http://localhost:8765/tests/test_dividendos.html   -> "TUDO PASSOU"
# abrir http://localhost:8765/tests/test_pluggy_funcao.html -> "TUDO PASSOU" (a Edge Function com Deno e Pluggy falsos)
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
que traz 3 meses completos e 1 pela metade (e Rendimentos por regra de % do saldo,
para testar a taxa nas simulações):

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
| `db/007_cdbs_resgate.sql` | `fin_cdbs.resgate`: títulos que já venceram, guardados para o rendimento do passado |
| `db/008_simulacoes.sql` | `fin_simulations` (simulações: alterações por cima do plano e o registro para desfazer) + RLS |
| `db/seed.sql` | os 4 anos da planilha (gerado, fora do git) |

A proteção do dado é **RLS + cadastro de novos usuários desligado** no painel do
Supabase. A chave publicável no `index.html` é pública por design.

## Documentos

- Design: `docs/superpowers/specs/2026-09-07-app-financas-design.md`
- Plano de implementação: `docs/superpowers/plans/2026-09-07-app-financas.md`
- Simulações: `docs/superpowers/specs/2026-09-26-simulacoes-design.md` e
  `docs/superpowers/plans/2026-09-26-simulacoes.md`
