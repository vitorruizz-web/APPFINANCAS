# -*- coding: utf-8 -*-
"""Gera tests/mock.json com numeros INVENTADOS, para trabalhar a interface.

Por que existe: a planilha nao tem saldo por conta -- o apontamento mensal so
comeca em 09/2026. Rodando o preview com os dados reais, as quatro analises da
sub-aba "Analise" aparecem todas vazias, e nao da para ver se estao certas.

Este mock traz 6 contas e quatro meses: TRES completos (set, out, nov/2026) e
um pela METADE (dez/2026), que e o estado em que o aviso de "faltam N contas"
tem de aparecer e o mes tem de continuar em aberto.

Nenhum numero aqui e real -- pode ir para o repositorio publico. O que nao pode
e o mock.json gerado, que continua no .gitignore junto com o de dados reais.

Uso: python tools/gerar_mock_sintetico.py
     python tools/gerar_preview.py
     (abrir http://localhost:8765/tests/preview.html)

Para voltar aos dados reais: python tools/importar_planilha.py --gerar --email <voce>
"""
import io
import json
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CATS = [("cat1", "Pró-labore", "receita", "Trabalho", 1),
        ("cat2", "Rendimentos", "receita", "Investimentos", 2),
        ("cat3", "Apartamento", "despesa", "Moradia", 3),
        ("cat4", "Viagens", "despesa", "Viagens", 4)]
PREVISTO = {"cat1": 21000.0, "cat2": 4200.0, "cat3": 6800.0, "cat4": 900.0}

CONTAS = [("a1", "Conta corrente", "corrente", 1),
          ("a2", "CDB Itaú", "investimento", 2),
          ("a3", "Tesouro Direto", "investimento", 3),
          ("a4", "Ações", "investimento", 4),
          ("a5", "FGTS", "fgts", 5),
          ("a6", "Reserva de emergência", "investimento", 6)]

# None = conta em branco naquele mes
SALDOS = {
    "2026-09-01": [12500, 285000, 190000, 96000, 48400, 87000],
    "2026-10-01": [9800, 292400, 193100, 101500, 49100, 87600],
    "2026-11-01": [14200, 299900, 196300, 98700, 49800, 88200],
    "2026-12-01": [11900, 306100, None, None, 50500, None],
}

INICIO_CONTAS = "2026-09-01"   # antes disso o realizado vem do "historico"
ULTIMO_APURADO = "2026-08-01"  # o que na vida real veio da planilha


def competencias(ini, fim):
    ano, mes = int(ini[:4]), int(ini[5:7])
    out = []
    while "%04d-%02d" % (ano, mes) <= fim:
        out.append("%04d-%02d-01" % (ano, mes))
        mes += 1
        if mes > 12:
            mes, ano = 1, ano + 1
    return out


def main():
    todos = competencias("2026-01", "2028-12")
    plano, meses, patrimonio = [], [], 700000.0
    for c in todos:
        for cid, _, _, _, _ in CATS:
            plano.append({"id": "p-%s-%s" % (c, cid), "competencia": c,
                          "category_id": cid, "valor": PREVISTO[cid],
                          "origem": "planilha", "obs": None})
        apurado = c <= ULTIMO_APURADO
        meses.append({"id": "m-" + c, "competencia": c,
                      "saldo_inicial_override": 690000.0 if c == todos[0] else None,
                      "realizado_override": round(patrimonio, 2) if apurado else None,
                      "fechado": apurado, "obs": None})
        if apurado:
            patrimonio *= 1.006

    balances = []
    for comp, valores in SALDOS.items():
        for (aid, _, _, _), v in zip(CONTAS, valores):
            if v is None:
                continue
            balances.append({"id": "b-%s-%s" % (comp, aid), "competencia": comp,
                             "account_id": aid, "saldo": float(v)})

    mock = {
        "fin_categories": [{"id": i, "nome": n, "tipo": t, "grupo": g,
                            "calculo": "manual", "ordem": o, "ativo": True, "cor": None}
                           for i, n, t, g, o in CATS],
        "fin_accounts": [{"id": i, "nome": n, "tipo": t, "instituicao": None,
                          "cor": None, "ordem": o, "ativo": True,
                          "considera_patrimonio": True, "inicio": INICIO_CONTAS}
                         for i, n, t, o in CONTAS],
        "fin_rules": [], "fin_entries": [], "fin_installments": [],
        "fin_plan": plano, "fin_months": meses, "fin_balances": balances,
        "fin_settings": [{"user_id": "u1", "data": {}}],
    }

    dst = os.path.join(RAIZ, "tests", "mock.json")
    io.open(dst, "w", encoding="utf-8").write(json.dumps(mock, ensure_ascii=False))
    completos = [c for c, v in SALDOS.items() if None not in v]
    print("gerado: %s (%d bytes) -- NUMEROS INVENTADOS" % (dst, os.path.getsize(dst)))
    print("meses completos: %s" % ", ".join(completos))
    print("mes pela metade: %s" % ", ".join(c for c in SALDOS if c not in completos))


if __name__ == "__main__":
    main()
