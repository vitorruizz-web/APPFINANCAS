-- App Financas - migracao 008: simulacoes
-- Rodar no SQL Editor. Idempotente: pode ser reexecutada sem erro.
--
-- Uma linha por simulacao: a lista de alteracoes (jsonb) que o app aplica por
-- cima do plano oficial. `desfazer` guarda o que tornar oficial gravou, para
-- voltar atras; `oficializada_em` marca quando virou o plano.
--
-- Tabela propria, e nao fin_settings: gravarPrefs grava o JSON inteiro de uma
-- vez, e um aparelho com as preferencias antigas em memoria apagaria a
-- simulacao salva no outro. Aqui cada simulacao e uma linha, PATCH por id.

create table if not exists fin_simulations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  nome text not null,
  alteracoes jsonb not null default '[]'::jsonb,
  oficializada_em timestamptz,
  desfazer jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists fin_simulations_user on fin_simulations (user_id);

alter table fin_simulations enable row level security;
drop policy if exists fin_simulations_own on fin_simulations;
create policy fin_simulations_own on fin_simulations for all
  using (auth.uid() = user_id) with check (auth.uid() = user_id);
