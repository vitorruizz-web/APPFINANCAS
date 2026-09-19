-- App Financas - migracao 006: posicao de CDBs (aba Vencimentos)
-- Rodar no SQL Editor DEPOIS das anteriores.
--
-- Uma linha por CDB da planilha da corretora. Importar e AUTORITATIVO: o app
-- grava o lote novo e SO DEPOIS apaga os anteriores (lote <> novo). Se o DELETE
-- falhar, o app usa so o lote mais recente -- nunca soma dois.

create table if not exists fin_cdbs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  lote timestamptz not null,
  data_posicao date not null,
  nome text not null,
  emissor text,
  indexador text not null check (indexador in ('pre','cdi','cdi+')),
  taxa numeric(12,8) not null,
  vencimento date not null,
  saldo_liquido numeric(18,6) not null check (saldo_liquido >= 0),
  data_aplicacao date,
  valor_aplicado numeric(18,6),
  juros_mensais boolean not null default false,
  created_at timestamptz not null default now()
);
create index if not exists fin_cdbs_venc on fin_cdbs (user_id, vencimento);

alter table fin_cdbs enable row level security;
drop policy if exists fin_cdbs_own on fin_cdbs;
create policy fin_cdbs_own on fin_cdbs for all
  using (auth.uid() = user_id) with check (auth.uid() = user_id);
grant select, insert, update, delete on table fin_cdbs to authenticated;
