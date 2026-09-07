-- App Financas - schema completo
-- Rodar UMA VEZ no SQL Editor do projeto financas-app.
-- Idempotente: pode ser reexecutado sem erro.

-- ============================================================
-- TABELAS
-- ============================================================

create table if not exists fin_categories (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  nome text not null,
  tipo text not null check (tipo in ('receita','despesa')),
  grupo text not null,
  calculo text not null default 'manual'
    check (calculo in ('manual','pct_saldo','crescimento')),
  cor text,
  ordem int not null default 0,
  ativo boolean not null default true,
  created_at timestamptz not null default now(),
  unique (user_id, nome)
);

create table if not exists fin_accounts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  nome text not null,
  tipo text not null default 'investimento'
    check (tipo in ('corrente','investimento','fgts','cartao','outro')),
  instituicao text,
  cor text,
  ordem int not null default 0,
  ativo boolean not null default true,
  considera_patrimonio boolean not null default true,
  created_at timestamptz not null default now(),
  unique (user_id, nome)
);

create table if not exists fin_rules (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  category_id uuid not null references fin_categories(id) on delete cascade,
  tipo text not null check (tipo in ('fixo','pct_saldo','crescimento','anual')),
  valor numeric(14,2),
  percentual numeric(12,8),
  mes int check (mes between 1 and 12),
  inicio date not null check (inicio = date_trunc('month', inicio)::date),
  fim date check (fim = date_trunc('month', fim)::date),
  reajuste_pct numeric(9,6),
  reajuste_mes int check (reajuste_mes between 1 and 12),
  obs text,
  ativo boolean not null default true,
  created_at timestamptz not null default now(),
  check (fim is null or fim >= inicio),
  check (tipo <> 'anual' or mes is not null),
  check (tipo not in ('pct_saldo','crescimento') or percentual is not null),
  check (tipo not in ('fixo','anual','crescimento') or valor is not null)
);
create index if not exists fin_rules_cat on fin_rules (user_id, category_id);

create table if not exists fin_plan (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  competencia date not null check (competencia = date_trunc('month', competencia)::date),
  category_id uuid not null references fin_categories(id) on delete cascade,
  valor numeric(14,2) not null default 0,
  origem text not null default 'manual' check (origem in ('manual','planilha')),
  obs text,
  unique (user_id, competencia, category_id)
);
create index if not exists fin_plan_comp on fin_plan (user_id, competencia);

create table if not exists fin_entries (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  data date not null,
  competencia date not null check (competencia = date_trunc('month', competencia)::date),
  category_id uuid not null references fin_categories(id) on delete restrict,
  account_id uuid references fin_accounts(id) on delete set null,
  valor numeric(14,2) not null check (valor >= 0),
  descricao text,
  created_at timestamptz not null default now()
);
create index if not exists fin_entries_comp on fin_entries (user_id, competencia);

create table if not exists fin_balances (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  competencia date not null check (competencia = date_trunc('month', competencia)::date),
  account_id uuid not null references fin_accounts(id) on delete cascade,
  saldo numeric(14,2) not null,
  unique (user_id, competencia, account_id)
);

create table if not exists fin_months (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  competencia date not null check (competencia = date_trunc('month', competencia)::date),
  saldo_inicial_override numeric(14,2),
  realizado_override numeric(14,2),
  fechado boolean not null default false,
  obs text,
  unique (user_id, competencia)
);

create table if not exists fin_settings (
  user_id uuid primary key references auth.users(id) on delete cascade,
  data jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

-- ============================================================
-- RLS  (escrito tabela a tabela de proposito: dollar-quoting
--       aninhado quebra no editor Monaco do Supabase)
-- ============================================================

alter table fin_categories enable row level security;
alter table fin_accounts   enable row level security;
alter table fin_rules      enable row level security;
alter table fin_plan       enable row level security;
alter table fin_entries    enable row level security;
alter table fin_balances   enable row level security;
alter table fin_months     enable row level security;
alter table fin_settings   enable row level security;

drop policy if exists fin_categories_own on fin_categories;
create policy fin_categories_own on fin_categories for all
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists fin_accounts_own on fin_accounts;
create policy fin_accounts_own on fin_accounts for all
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists fin_rules_own on fin_rules;
create policy fin_rules_own on fin_rules for all
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists fin_plan_own on fin_plan;
create policy fin_plan_own on fin_plan for all
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists fin_entries_own on fin_entries;
create policy fin_entries_own on fin_entries for all
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists fin_balances_own on fin_balances;
create policy fin_balances_own on fin_balances for all
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists fin_months_own on fin_months;
create policy fin_months_own on fin_months for all
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists fin_settings_own on fin_settings;
create policy fin_settings_own on fin_settings for all
  using (auth.uid() = user_id) with check (auth.uid() = user_id);
