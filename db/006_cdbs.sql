-- App Financas - migracao 006: posicao de CDBs (aba Vencimentos)
-- Rodar no SQL Editor DEPOIS das anteriores.
--
-- Uma linha por titulo de renda fixa bancaria (CDB, LCI, LCA...). A posicao vem da
-- XP e do BTG pelo Open Finance (Edge Function pluggy-cdbs) ou, como plano B, da
-- planilha da corretora. Importar e AUTORITATIVO: o app grava o lote novo e SO
-- DEPOIS apaga os anteriores (lote <> novo). Se o DELETE falhar, o app usa so o
-- lote mais recente -- nunca soma dois.

create table if not exists fin_cdbs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  lote timestamptz not null,
  origem text not null default 'planilha' check (origem in ('planilha','pluggy')),
  data_posicao date not null,               -- dia do saldo (cada corretora pode estar num dia)
  instituicao text,                         -- corretora (XP, BTG) quando vem do Open Finance
  externo_id text,                          -- id do investimento na Pluggy
  tipo text,                                -- CDB, LCI, LCA, LC, RDB
  nome text not null,
  emissor text,
  indexador text not null check (indexador in ('pre','cdi','cdi+')),
  taxa numeric(12,8) not null,              -- pre: 0.155 | cdi: 1.20 (120%) | cdi+: spread 0.015
  spread numeric(12,8),                     -- hibrido: 110% do CDI + 1% a.a. -> taxa 1.10, spread 0.01
  vencimento date not null,
  saldo_liquido numeric(18,6) not null check (saldo_liquido >= 0),
  valor_bruto numeric(18,6),                -- bruto de hoje, quando a corretora informa
  data_aplicacao date,
  valor_aplicado numeric(18,6),
  juros_mensais boolean not null default false,
  isento_ir boolean not null default false, -- LCI e LCA
  created_at timestamptz not null default now()
);
-- quem rodou a primeira versao desta migracao (sem as colunas do Open Finance):
-- completa a tabela sem perder nada; em tabela nova, nao faz nada
alter table fin_cdbs add column if not exists origem text not null default 'planilha'
  check (origem in ('planilha','pluggy'));
alter table fin_cdbs add column if not exists instituicao text;
alter table fin_cdbs add column if not exists externo_id text;
alter table fin_cdbs add column if not exists tipo text;
alter table fin_cdbs add column if not exists spread numeric(12,8);
alter table fin_cdbs add column if not exists valor_bruto numeric(18,6);
alter table fin_cdbs add column if not exists isento_ir boolean not null default false;

create index if not exists fin_cdbs_venc on fin_cdbs (user_id, vencimento);

alter table fin_cdbs enable row level security;
drop policy if exists fin_cdbs_own on fin_cdbs;
create policy fin_cdbs_own on fin_cdbs for all
  using (auth.uid() = user_id) with check (auth.uid() = user_id);
grant select, insert, update, delete on table fin_cdbs to authenticated;
