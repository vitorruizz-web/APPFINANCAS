-- App Financas - migracao 009: observacoes nas celulas (resumo por periodo da aba Vencimentos)
-- Rodar no SQL Editor DEPOIS das anteriores. Idempotente: pode ser reexecutada sem erro.
--
-- Uma linha por celula anotada. `chave` diz que celula e -- tabela|linha|coluna, montada
-- pelo app (VENC.chaveNota) --; o texto e livre. Sem esta tabela o app abre igual e so a
-- observacao fica indisponivel.
--
-- Tabela propria, e nao fin_settings: gravarPrefs grava o JSON inteiro de uma vez, e um
-- aparelho com as preferencias antigas em memoria apagaria a observacao gravada no outro.
-- Aqui cada celula e uma linha: gravar e upsert por (user_id, chave); apagar e por id.

create table if not exists fin_notas (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  chave text not null,
  texto text not null,
  updated_at timestamptz not null default now(),
  unique (user_id, chave)
);

alter table fin_notas enable row level security;
drop policy if exists fin_notas_own on fin_notas;
create policy fin_notas_own on fin_notas for all
  using (auth.uid() = user_id) with check (auth.uid() = user_id);
grant select, insert, update, delete on table fin_notas to authenticated;
