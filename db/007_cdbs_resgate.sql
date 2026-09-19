-- App Financas - migracao 007: titulos que ja venceram (rendimento do passado)
-- Rodar no SQL Editor DEPOIS da 006.
--
-- O Open Finance mostra o titulo resgatado/vencido so por uns meses; o app guarda a
-- linha dele (compra, taxa, vencimento) para o "quanto rendeu por mes" do passado nao
-- perder o que ele rendeu. `resgate` preenchido = ja venceu: fica fora do calendario e
-- da posicao, e o app a leva de um lote para o outro a cada importacao.

alter table fin_cdbs add column if not exists resgate date;
