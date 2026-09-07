-- App Financas - migracao 005: precisao igual a da planilha
--
-- numeric(14,2) arredondava cada celula, e o encadeamento de 48 meses
-- acumulava ate ~3 centavos de diferenca contra o Excel. A planilha encadeia
-- valores NAO arredondados (ex.: Bruto = 15450,07229), entao as colunas que
-- alimentam a cadeia passam a guardar 6 casas. A exibicao continua com 2.

alter table fin_plan     alter column valor type numeric(18,6);
alter table fin_months   alter column saldo_inicial_override type numeric(18,6);
alter table fin_months   alter column realizado_override     type numeric(18,6);
alter table fin_rules    alter column valor type numeric(18,6);
alter table fin_balances alter column saldo type numeric(18,6);

select 'fin_plan.valor' as coluna, numeric_scale as casas
from information_schema.columns
where table_name = 'fin_plan' and column_name = 'valor';
