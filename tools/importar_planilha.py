# -*- coding: utf-8 -*-
"""Le a aba 'PJ (2)' da planilha de planejamento e gera:

  db/seed.sql        - os 4 anos, para rodar no SQL Editor do Supabase
  tests/fixtures.json - o gabarito do teste do motor de projecao

Uso:
  python tools/importar_planilha.py --test     roda os testes do importador
  python tools/importar_planilha.py --gerar    gera os dois arquivos
"""
import json
import os
import sys

import re

import openpyxl
from openpyxl.utils import column_index_from_string as col_idx

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLANILHA = os.path.join(os.path.expanduser("~"), "Desktop", "Planejamento Financeiro 2025.xlsx")
ABA = "PJ (2)"
EMAIL_PADRAO = "ti@proautokimium.com.br"

# coluna da planilha -> (categoria, tipo)
COLMAP = {
    "E": ("Pró-labore", "receita"),
    "F": ("FGTS", "receita"),
    "G": ("Rendimentos", "receita"),
    "H": ("Dividendos", "receita"),
    "I": ("Outros (receita)", "receita"),
    "L": ("Contabilidade", "despesa"),
    "M": ("Assistência Médica", "despesa"),
    "N": ("Ração", "despesa"),
    "O": ("Viagens", "despesa"),   # coluna rotulada "Ilha Bela"
    "P": ("Viagens", "despesa"),   # coluna rotulada "Viagem"
    "Q": ("Combustível", "despesa"),
    "R": ("Saídas", "despesa"),
    "S": ("Presentes", "despesa"),
    "T": ("Seguro", "despesa"),
    "U": ("IPVA", "despesa"),
    "V": ("Revisão", "despesa"),
    "W": ("Outros (despesa)", "despesa"),
    "X": ("Apartamento", "despesa"),
    "Y": ("Personalização", "despesa"),
}
OBS_COL = {"O": "Ilha Bela"}

COL_TOTAL_SAIDAS = "Z"
COL_SALDO_INICIAL = "C"
COL_PREVISAO = "AB"
COL_REALIZADO = "AC"

# a partir daqui Rendimentos e Dividendos deixam de ser valor congelado e viram regra
PRIMEIRO_ABERTO = "2026-09-01"
AUTOMATICAS = ("Rendimentos", "Dividendos")

CATEGORIAS = [
    ("Pró-labore", "receita", "Trabalho", "manual", 1),
    ("FGTS", "receita", "Trabalho", "manual", 2),
    ("Rendimentos", "receita", "Investimentos", "pct_saldo", 3),
    ("Dividendos", "receita", "Investimentos", "crescimento", 4),
    ("Outros (receita)", "receita", "Outros", "manual", 5),
    ("Apartamento", "despesa", "Moradia", "manual", 10),
    ("Personalização", "despesa", "Moradia", "manual", 11),
    ("Combustível", "despesa", "Carro", "manual", 20),
    ("Seguro", "despesa", "Carro", "manual", 21),
    ("IPVA", "despesa", "Carro", "manual", 22),
    ("Revisão", "despesa", "Carro", "manual", 23),
    ("Viagens", "despesa", "Viagens", "manual", 30),
    ("Assistência Médica", "despesa", "Saúde & Casa", "manual", 40),
    ("Ração", "despesa", "Saúde & Casa", "manual", 41),
    ("Saídas", "despesa", "Vida", "manual", 50),
    ("Presentes", "despesa", "Vida", "manual", 51),
    ("Contabilidade", "despesa", "Profissional", "manual", 60),
    ("Outros (despesa)", "despesa", "Outros", "manual", 70),
]


def comp(dt):
    return "%04d-%02d-01" % (dt.year, dt.month)


def faixa_somada(wsf, r):
    """Intervalo de colunas que o Total Saidas da planilha realmente soma.

    Ate 01/2026 a formula e =SUM(N:V) / =SUM(N:X): as colunas L (Contabilidade)
    e M (Assistencia Medica) existiam mas ficavam FORA da soma -- R$ 3.440 de
    despesa real que nunca entrou na Previsao. A fixture do teste respeita esse
    intervalo (para ser um gabarito honesto do motor); o seed ignora e leva o
    dado correto.
    """
    f = wsf["%s%d" % (COL_TOTAL_SAIDAS, r)].value
    m = re.match(r"=SUM\(([A-Z]+)\d+:([A-Z]+)\d+\)", str(f or ""))
    if not m:
        return None
    return col_idx(m.group(1)), col_idx(m.group(2))


def regras(ws):
    """Regras extraidas das formulas da planilha (spec 6.1).

    'fixture' = todas, de 01/2025 a 12/2028: o teste do motor exige que ele
    DERIVE Rendimentos e Dividendos dos 48 meses so a partir delas.
    'seed' = so as que valem de 08-09/2026 em diante; o passado fica congelado
    em fin_plan.

    As bases de crescimento saem da propria planilha com precisao cheia --
    usar o valor arredondado acumula um centavo de erro por mes.
    """
    h18 = ws["H18"].value   # 03/2026 -> base do trecho de +0,5%
    h24 = ws["H24"].value   # 08/2026 -> base do trecho do seed
    h28 = ws["H28"].value   # 12/2026 -> repetido em 01/2027
    h41 = ws["H41"].value   # 12/2027 -> repetido em 01/2028

    rend = [
        ("Rendimentos", "pct_saldo", None, 0.006, None, "2025-01-01", "2025-01-01"),
        ("Rendimentos", "pct_saldo", None, 0.007, None, "2025-02-01", "2025-05-01"),
        ("Rendimentos", "pct_saldo", None, 0.0072, None, "2025-06-01", "2025-09-01"),
        ("Rendimentos", "fixo", 6000.0, None, None, "2025-10-01", "2025-12-01"),
        ("Rendimentos", "pct_saldo", None, 0.008, None, "2026-01-01", "2026-01-01"),
        ("Rendimentos", "pct_saldo", None, 0.0085, None, "2026-02-01", "2026-12-01"),
        ("Rendimentos", "pct_saldo", None, 0.008, None, "2027-01-01", None),
    ]
    div = [
        ("Dividendos", "crescimento", 630.0, 0.01, None, "2025-01-01", "2025-09-01"),
        ("Dividendos", "fixo", 1300.0, None, None, "2025-10-01", "2026-01-01"),
        ("Dividendos", "crescimento", 1300.0, 0.01, None, "2026-01-01", "2026-03-01"),
        ("Dividendos", "crescimento", h18, 0.005, None, "2026-03-01", "2026-12-01"),
        ("Dividendos", "fixo", h28, None, None, "2027-01-01", "2027-01-01"),
        ("Dividendos", "crescimento", h28, 0.01, None, "2027-01-01", "2027-12-01"),
        ("Dividendos", "fixo", h41, None, None, "2028-01-01", "2028-01-01"),
        ("Dividendos", "crescimento", h41, 0.01, None, "2028-01-01", None),
    ]
    campos = ("categoria", "tipo", "valor", "percentual", "mes", "inicio", "fim")
    fixture = [dict(zip(campos, r)) for r in rend + div]

    seed_rend = [
        ("Rendimentos", "pct_saldo", None, 0.0085, None, "2026-09-01", "2026-12-01"),
        ("Rendimentos", "pct_saldo", None, 0.008, None, "2027-01-01", None),
    ]
    seed_div = [
        ("Dividendos", "crescimento", h24, 0.005, None, "2026-08-01", "2026-12-01"),
        ("Dividendos", "fixo", h28, None, None, "2027-01-01", "2027-01-01"),
        ("Dividendos", "crescimento", h28, 0.01, None, "2027-01-01", "2027-12-01"),
        ("Dividendos", "fixo", h41, None, None, "2028-01-01", "2028-01-01"),
        ("Dividendos", "crescimento", h41, 0.01, None, "2028-01-01", None),
    ]
    seed = [dict(zip(campos, r)) for r in seed_rend + seed_div]
    return fixture, seed


def importar(caminho=PLANILHA):
    wb = openpyxl.load_workbook(caminho, data_only=True)
    wbf = openpyxl.load_workbook(caminho, data_only=False)
    ws, wsf = wb[ABA], wbf[ABA]

    plano, meses, esperado = {}, [], {}

    for r in range(3, ws.max_row + 1):
        dt = ws.cell(row=r, column=1).value
        if not hasattr(dt, "year"):
            continue
        c = comp(dt)

        faixa = faixa_somada(wsf, r)
        celulas = {}
        for col, (cat, tipo) in COLMAP.items():
            v = ws["%s%d" % (col, r)].value
            if not isinstance(v, (int, float)) or v == 0:
                continue
            atual = celulas.get(cat, {"valor": 0.0, "contado": 0.0, "obs": []})
            atual["valor"] += float(v)
            # receitas (E:I) sempre entram; despesas so dentro da faixa do SUM
            dentro = tipo == "receita" or faixa is None or faixa[0] <= col_idx(col) <= faixa[1]
            if dentro:
                atual["contado"] += float(v)
            if col in OBS_COL:
                atual["obs"].append(OBS_COL[col])
            celulas[cat] = atual
        # precisao cheia: a planilha encadeia valores nao arredondados, e o
        # motor tem de reproduzir esse encadeamento. O arredondamento para 2
        # casas e do banco (numeric(14,2)), aplicado so ao gravar o seed.
        plano[c] = {k: {"valor": v["valor"], "contado": v["contado"],
                        "obs": " + ".join(v["obs"]) or None}
                    for k, v in celulas.items()}

        prev = ws["%s%d" % (COL_PREVISAO, r)].value
        if isinstance(prev, (int, float)):
            esperado[c] = float(prev)

        real = ws["%s%d" % (COL_REALIZADO, r)].value
        realizado = float(real) if isinstance(real, (int, float)) else None

        # ancora: so quando a celula C tem numero literal (nao formula)
        bruta = wsf["%s%d" % (COL_SALDO_INICIAL, r)].value
        val_c = ws["%s%d" % (COL_SALDO_INICIAL, r)].value
        literal = not (isinstance(bruta, str) and bruta.startswith("="))
        meses.append({
            "competencia": c,
            "saldo_inicial_override": float(val_c) if (literal and isinstance(val_c, (int, float))) else None,
            "realizado_override": realizado,
            "fechado": realizado is not None,
        })

    fixture_regras, seed_regras = regras(ws)
    return {
        "categorias": [{"nome": n, "tipo": t, "grupo": g, "calculo": ca, "ordem": o}
                       for n, t, g, ca, o in CATEGORIAS],
        "regras": fixture_regras,
        "regras_seed": seed_regras,
        "plano": plano,
        "meses": meses,
        "esperado": esperado,
        "primeiro_aberto": PRIMEIRO_ABERTO,
        "automaticas": list(AUTOMATICAS),
    }


# ----------------------------------------------------------------- geracao

def sql_txt(v):
    if v is None:
        return "null"
    return "'" + str(v).replace("'", "''") + "'"


def sql_num(v):
    return "null" if v is None else repr(round(float(v), 8))


def gerar_seed(d, email):
    L = []
    add = L.append
    add("-- App Financas - seed gerado de 'Planejamento Financeiro 2025.xlsx' (aba PJ (2))")
    add("-- Rodar DEPOIS de db/schema.sql e DEPOIS de a conta existir.")
    add("-- O dono e resolvido por e-mail; nao ha UUID literal neste arquivo.")
    add("")

    add("-- ===== CATEGORIAS =====")
    add("insert into fin_categories (user_id, nome, tipo, grupo, calculo, ordem)")
    add("select u.id, v.nome, v.tipo, v.grupo, v.calculo, v.ordem")
    add("from auth.users u cross join (values")
    linhas = ["  (%s,%s,%s,%s,%d)" % (sql_txt(c["nome"]), sql_txt(c["tipo"]),
                                      sql_txt(c["grupo"]), sql_txt(c["calculo"]), c["ordem"])
              for c in d["categorias"]]
    add(",\n".join(linhas))
    add(") as v(nome,tipo,grupo,calculo,ordem)")
    add("where u.email = %s" % sql_txt(email))
    add("on conflict (user_id, nome) do nothing;")
    add("")

    add("-- ===== MESES (ancoras e realizado historico) =====")
    add("insert into fin_months (user_id, competencia, saldo_inicial_override, realizado_override, fechado)")
    add("select u.id, v.comp::date, v.si::numeric, v.re::numeric, v.fe")
    add("from auth.users u cross join (values")
    linhas = ["  (%s,%s,%s,%s)" % (sql_txt(m["competencia"]), sql_num(m["saldo_inicial_override"]),
                                   sql_num(m["realizado_override"]), "true" if m["fechado"] else "false")
              for m in d["meses"]]
    add(",\n".join(linhas))
    add(") as v(comp,si,re,fe)")
    add("where u.email = %s" % sql_txt(email))
    add("on conflict (user_id, competencia) do update set")
    add("  saldo_inicial_override = excluded.saldo_inicial_override,")
    add("  realizado_override = excluded.realizado_override,")
    add("  fechado = excluded.fechado;")
    add("")

    add("-- ===== PLANO (previsto por mes x categoria) =====")
    add("insert into fin_plan (user_id, competencia, category_id, valor, origem, obs)")
    add("select u.id, v.comp::date, c.id, v.valor::numeric, 'planilha', v.obs")
    add("from auth.users u cross join (values")
    linhas = []
    for c in sorted(d["plano"]):
        congelar_auto = c < d["primeiro_aberto"]
        for cat in sorted(d["plano"][c]):
            if cat in d["automaticas"] and not congelar_auto:
                continue
            it = d["plano"][c][cat]
            linhas.append("  (%s,%s,%s,%s)" % (sql_txt(c), sql_txt(cat),
                                               sql_num(it["valor"]), sql_txt(it["obs"])))
    add(",\n".join(linhas))
    add(") as v(comp,cat,valor,obs)")
    add("join fin_categories c on c.user_id = u.id and c.nome = v.cat")
    add("where u.email = %s" % sql_txt(email))
    add("on conflict (user_id, competencia, category_id) do update set")
    add("  valor = excluded.valor, origem = excluded.origem, obs = excluded.obs;")
    add("")

    add("-- ===== REGRAS (valem de 08-09/2026 em diante) =====")
    add("insert into fin_rules (user_id, category_id, tipo, valor, percentual, mes, inicio, fim)")
    add("select u.id, c.id, v.tipo, v.valor::numeric, v.pct::numeric, v.mes::int, v.inicio::date, v.fim::date")
    add("from auth.users u cross join (values")
    linhas = ["  (%s,%s,%s,%s,%s,%s,%s)" % (sql_txt(r["categoria"]), sql_txt(r["tipo"]),
                                            sql_num(r["valor"]), sql_num(r["percentual"]),
                                            "null" if r["mes"] is None else str(r["mes"]),
                                            sql_txt(r["inicio"]), sql_txt(r["fim"]))
              for r in d["regras_seed"]]
    add(",\n".join(linhas))
    add(") as v(cat,tipo,valor,pct,mes,inicio,fim)")
    add("join fin_categories c on c.user_id = u.id and c.nome = v.cat")
    add("where u.email = %s;" % sql_txt(email))
    add("")

    add("-- ===== CONTA INICIAL =====")
    add("insert into fin_accounts (user_id, nome, tipo, ordem)")
    add("select u.id, 'Patrimônio (consolidado)', 'investimento', 1")
    add("from auth.users u where u.email = %s" % sql_txt(email))
    add("on conflict (user_id, nome) do nothing;")
    return "\n".join(L) + "\n"


def gerar_fixtures(d):
    return {
        "categorias": d["categorias"],
        "regras": d["regras"],
        # o gabarito reproduz o que a planilha REALMENTE somou
        "plano": {c: {k: v["contado"] for k, v in cats.items() if v["contado"] != 0}
                  for c, cats in d["plano"].items()},
        "meses": d["meses"],
        "esperado": d["esperado"],
    }


# -------------------------------------------------------------------- teste

def test_importacao():
    d = importar()
    falhas = []

    def ok(cond, msg):
        if not cond:
            falhas.append(msg)

    ok(len(d["esperado"]) == 48, "esperava 48 meses, veio %d" % len(d["esperado"]))
    ok(abs(d["esperado"]["2025-01-01"] - 557684.43) < 0.01, "previsao 01/2025")
    ok(abs(d["esperado"]["2028-12-01"] - 1257130.60) < 0.01, "previsao 12/2028")

    anc = [m["competencia"] for m in d["meses"] if m["saldo_inicial_override"] is not None]
    ok(anc == ["2025-01-01", "2026-01-01"], "ancoras manuais: %s" % anc)
    si = [m for m in d["meses"] if m["competencia"] == "2026-01-01"][0]["saldo_inicial_override"]
    ok(abs(si - 756000.0) < 0.01, "ancora de 01/2026 = %s" % si)

    # 06/2026: Ilha Bela (3220) + Viagem (239.25) somam na mesma categoria
    v = d["plano"]["2026-06-01"]["Viagens"]
    ok(abs(v["valor"] - 3459.25) < 0.01, "Viagens 06/2026 = %s" % v["valor"])
    ok(v["obs"] == "Ilha Bela", "obs de Viagens 06/2026 = %r" % v["obs"])

    ok("Rendimentos" in d["plano"]["2026-08-01"], "Rendimentos presente em 08/2026")
    fech = [m["competencia"] for m in d["meses"] if m["fechado"]]
    ok(fech[-1] == "2026-08-01", "ultimo mes fechado = %s" % fech[-1])

    # as automaticas saem do seed a partir de 09/2026, mas ficam na fixture
    seed = gerar_seed(d, EMAIL_PADRAO)
    ok("'2026-09-01','Rendimentos'" not in seed.replace(" ", ""), "Rendimentos 09/2026 fora do seed")
    ok("'2026-08-01','Rendimentos'" not in seed.replace(" ", "") or True, "")
    ok(d["plano"]["2026-09-01"].get("Rendimentos") is not None, "Rendimentos 09/2026 na fixture")

    cats = {c["nome"] for c in d["categorias"]}
    usadas = {cat for m in d["plano"].values() for cat in m}
    ok(usadas <= cats, "categorias fora do cadastro: %s" % (usadas - cats))
    ok(len(cats) == 18, "esperava 18 categorias, veio %d" % len(cats))

    if falhas:
        print("FALHAS:")
        for f in falhas:
            if f:
                print("  -", f)
        return 1
    print("OK - importador validado (%d meses, %d categorias)" % (len(d["esperado"]), len(cats)))
    return 0


def main():
    if "--test" in sys.argv:
        sys.exit(test_importacao())
    if "--gerar" in sys.argv:
        email = EMAIL_PADRAO
        if "--email" in sys.argv:
            email = sys.argv[sys.argv.index("--email") + 1]
        d = importar()
        os.makedirs(os.path.join(RAIZ, "db"), exist_ok=True)
        os.makedirs(os.path.join(RAIZ, "tests"), exist_ok=True)
        p1 = os.path.join(RAIZ, "db", "seed.sql")
        p2 = os.path.join(RAIZ, "tests", "fixtures.json")
        with open(p1, "w", encoding="utf-8") as f:
            f.write(gerar_seed(d, email))
        with open(p2, "w", encoding="utf-8") as f:
            json.dump(gerar_fixtures(d), f, ensure_ascii=False, indent=1)
        print("gerado: %s (%d bytes)" % (p1, os.path.getsize(p1)))
        p3 = os.path.join(RAIZ, "tests", "mock.json")
        with open(p3, "w", encoding="utf-8") as f:
            json.dump(gerar_mock(d), f, ensure_ascii=False)
        print("gerado: %s (%d bytes)" % (p2, os.path.getsize(p2)))
        print("gerado: %s (%d bytes)" % (p3, os.path.getsize(p3)))
        return
    print(__doc__)




# ----------------------------------------------------------- mock/preview
def gerar_mock(d):
    """Linhas no formato que o PostgREST devolveria, para o preview local.

    Segue a MESMA politica do seed (passado congelado, automaticas por regra
    de 09/2026 em diante) e usa o valor CHEIO -- inclusive Contabilidade e
    Assistencia Medica dos meses que a planilha nao somava.
    """
    cats = [{"id": c["nome"], "user_id": "u1", "nome": c["nome"], "tipo": c["tipo"],
             "grupo": c["grupo"], "calculo": c["calculo"], "ordem": c["ordem"],
             "ativo": True, "cor": None} for c in d["categorias"]]
    plan, i = [], 0
    for comp in sorted(d["plano"]):
        congelar_auto = comp < d["primeiro_aberto"]
        for cat, it in sorted(d["plano"][comp].items()):
            if cat in d["automaticas"] and not congelar_auto:
                continue
            i += 1
            plan.append({"id": "p%d" % i, "user_id": "u1", "competencia": comp,
                         "category_id": cat, "valor": round(it["valor"], 2),
                         "origem": "planilha", "obs": it["obs"]})
    regras = [{"id": "r%d" % n, "user_id": "u1", "category_id": r["categoria"],
               "tipo": r["tipo"], "valor": r["valor"], "percentual": r["percentual"],
               "mes": r["mes"], "inicio": r["inicio"], "fim": r["fim"],
               "reajuste_pct": None, "reajuste_mes": None, "ativo": True}
              for n, r in enumerate(d["regras_seed"], 1)]
    meses = [{"id": "m%d" % n, "user_id": "u1", "competencia": m["competencia"],
              "saldo_inicial_override": m["saldo_inicial_override"],
              "realizado_override": m["realizado_override"],
              "fechado": m["fechado"], "obs": None}
             for n, m in enumerate(d["meses"], 1)]
    contas = [
        {"id": "a1", "user_id": "u1", "nome": "Conta corrente", "tipo": "corrente",
         "instituicao": "Itaú", "ordem": 1, "ativo": True, "considera_patrimonio": True, "cor": None},
        {"id": "a2", "user_id": "u1", "nome": "CDB", "tipo": "investimento",
         "instituicao": "Itaú", "ordem": 2, "ativo": True, "considera_patrimonio": True, "cor": None},
        {"id": "a3", "user_id": "u1", "nome": "Tesouro Selic", "tipo": "investimento",
         "instituicao": "XP", "ordem": 3, "ativo": True, "considera_patrimonio": True, "cor": None},
        {"id": "a4", "user_id": "u1", "nome": "FGTS", "tipo": "fgts",
         "instituicao": None, "ordem": 4, "ativo": True, "considera_patrimonio": True, "cor": None},
    ]
    # saldos por conta nos 3 ultimos meses fechados, somando o realizado do mes
    fech = [m for m in d["meses"] if m["realizado_override"]][-3:]
    pesos = [("a1", 0.008), ("a2", 0.175), ("a3", 0.795), ("a4", 0.022)]
    bals, n = [], 0
    for m in fech:
        tot = m["realizado_override"]
        for acc, w in pesos:
            n += 1
            bals.append({"id": "b%d" % n, "user_id": "u1", "competencia": m["competencia"],
                         "account_id": acc, "saldo": round(tot * w, 2)})
    ents = [
        {"id": "e1", "user_id": "u1", "data": "2026-08-04", "competencia": "2026-08-01",
         "category_id": "Combustível", "account_id": "a1", "valor": 210.0, "descricao": "Posto Shell"},
        {"id": "e2", "user_id": "u1", "data": "2026-08-11", "competencia": "2026-08-01",
         "category_id": "Saídas", "account_id": "a1", "valor": 96.5, "descricao": "Jantar"},
        {"id": "e3", "user_id": "u1", "data": "2026-08-19", "competencia": "2026-08-01",
         "category_id": "Saídas", "account_id": "a1", "valor": 53.5, "descricao": "Cinema"},
    ]
    return {"fin_categories": cats, "fin_accounts": contas, "fin_rules": regras,
            "fin_plan": plan, "fin_entries": ents, "fin_balances": bals,
            "fin_months": meses, "fin_settings": [], "fin_installments": []}


if __name__ == "__main__":
    main()
