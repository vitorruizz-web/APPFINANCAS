-- App Financas - migracao 010: despesas realizadas do mes (aba Plano -> Realizado)
-- Rodar no SQL Editor DEPOIS das anteriores. Idempotente: pode ser reexecutada sem erro.
--
-- O total geral de despesas que o mes teve de fato, digitado na sub-aba Realizado do
-- Plano e comparado com as Saidas previstas. Fica na linha do mes (um registro por
-- mes, upsert por user_id + competencia em definirMes), como o saldo inicial fixado e
-- a anotacao do mes; a RLS de fin_months ja cobre. So comparacao: nao entra na projecao.
-- Sem esta coluna o app abre igual e a sub-aba avisa para rodar esta migracao.

alter table fin_months add column if not exists saidas_realizadas numeric(18,6);
