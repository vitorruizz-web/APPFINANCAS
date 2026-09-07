-- App Financas - migracao 003: a conta so conta a partir de um mes
--
-- Cadastrar uma conta hoje NAO pode reescrever o patrimonio dos meses ja
-- apurados. Antes de `inicio` a conta e ignorada na soma, e o mes fechado
-- continua valendo o fin_months.realizado_override que ja estava la.

alter table fin_accounts
  add column if not exists inicio date;

alter table fin_accounts
  drop constraint if exists fin_accounts_inicio_mes;
alter table fin_accounts
  add constraint fin_accounts_inicio_mes
  check (inicio is null or inicio = date_trunc('month', inicio)::date);

-- a conta que veio do seed representa o historico inteiro: vale desde sempre
update fin_accounts set inicio = null where inicio is null;
