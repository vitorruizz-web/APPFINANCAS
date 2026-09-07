-- App Financas - migracao 002: compromissos parcelados
-- Rodar no SQL Editor DEPOIS do schema.sql.
--
-- Por que tabela propria e nao uma regra: regra so vale nos meses em que nao
-- ha valor em fin_plan, e a importacao criou linha para TODO mes ate 12/2028.
-- Uma parcela feita como regra seria invisivel. O motor SOMA as parcelas por
-- cima do valor do mes.

create table if not exists fin_installments (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  category_id uuid not null references fin_categories(id) on delete cascade,
  descricao text not null,
  valor numeric(14,2) not null check (valor > 0),
  inicio date not null check (inicio = date_trunc('month', inicio)::date),
  parcelas int not null check (parcelas between 1 and 600),
  obs text,
  ativo boolean not null default true,
  created_at timestamptz not null default now()
);
create index if not exists fin_installments_cat on fin_installments (user_id, category_id);

alter table fin_installments enable row level security;
drop policy if exists fin_installments_own on fin_installments;
create policy fin_installments_own on fin_installments for all
  using (auth.uid() = user_id) with check (auth.uid() = user_id);
