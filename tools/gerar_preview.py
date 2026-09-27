# -*- coding: utf-8 -*-
"""Gera tests/preview.html: o index.html com window.fetch trocado por um mock
que serve tests/mock.json (os dados reais da planilha).

Troca-se SO o window.fetch -- nao os sb*. E isso que garante que sbFetch,
tokenAtual, renovar e a trava de gravacao sejam de fato exercitados; um mock
que substitui as funcoes de dados nao testa nenhum desses caminhos.

O bloco entra ANTES do <script> do app: o app instala handlers e chama
iniciar() na carga, entao o mock precisa ja estar de pe.

Uso: python tools/gerar_preview.py
     (e depois abrir http://localhost:8765/tests/preview.html)
"""
import io
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MOCK = r"""
<script>
// ===== PREVIEW LOCAL - nao vai para o repositorio =====
(function(){
  const DADOS = {};
  let carregado = null;

  localStorage.setItem("fin_sess", JSON.stringify({
    access_token: "fake-token", refresh_token: "fake-refresh", expires_in: 3600
  }));

  async function garantir(){
    // guarda a PROMESSA, nao o resultado: as 9 tabelas carregam em paralelo e
    // cada uma disparava o proprio fetch do mock.json
    // cache-buster: sem ele o navegador serve o mock.json velho e o preview
    // mostra dados de antes -- ja me custou uma rodada inteira de conferencia
    if (!carregado) carregado = realFetch("./mock.json?v=" + Date.now()).then(r => r.json());
    return carregado;
  }
  const realFetch = window.fetch.bind(window);

  function json(body, status){
    return new Response(JSON.stringify(body), {
      status: status || 200, headers: { "Content-Type": "application/json" }
    });
  }

  window.fetch = async function(url, opts){
    url = String(url); opts = opts || {};
    if (url.indexOf("supabase.co") === -1) return realFetch(url, opts);

    // ---- Edge Function da aba Vencimentos (Open Finance): responde com
    //      tests/_real/<arquivo> (gerado da planilha real, FORA do git). Sem o
    //      arquivo, responde como funcao ainda nao publicada (404).
    //      window.__pluggyMock troca o arquivo (ex.: "pluggy_mock_falha.json").
    if (url.indexOf("/functions/v1/pluggy-cdbs") !== -1){
      const arq = window.__pluggyMock || "pluggy_mock.json";
      const r = await realFetch("./_real/" + arq + "?v=" + Date.now()).catch(() => null);
      if (!r || !r.ok) return json({ message: "Requested function was not found" }, 404);
      return json(await r.json());
    }

    // ---- auth ----
    if (url.indexOf("/auth/v1/user") !== -1)
      return json({ id: "u1", email: "preview@local" });
    if (url.indexOf("/auth/v1/token") !== -1 || url.indexOf("/auth/v1/signup") !== -1)
      return json({ access_token: "fake-token", refresh_token: "fake-refresh", expires_in: 3600 });

    // ---- rest ----
    const m = url.match(/\/rest\/v1\/(fin_[a-z]+)/);
    if (!m) return json([], 404);
    const tabela = m[1];
    const d = await garantir();
    DADOS[tabela] = DADOS[tabela] || (d[tabela] || []).slice();
    const metodo = (opts.method || "GET").toUpperCase();

    if (metodo === "GET") return json(DADOS[tabela]);

    const prefer = String((opts.headers || {})["Prefer"] || "");
    if (metodo === "POST"){
      const linhas = JSON.parse(opts.body);
      const merge = prefer.indexOf("merge-duplicates") >= 0;
      const porId = /on_conflict=id(&|$)/.test(url);
      // como o PostgREST: id repetido sem upsert por id e 409, e nada e gravado
      // (e o que acontece quando o salvar repete um insert cuja resposta se perdeu)
      if (!(merge && porId) && linhas.some(l => l.id !== undefined &&
          DADOS[tabela].some(x => String(x.id) === String(l.id))))
        return json({ code: "23505", message: "duplicate key value violates unique constraint" }, 409);
      const out = linhas.map((l, i) => {
        const novo = Object.assign({ id: tabela + "-" + Date.now() + "-" + i }, l);
        if (merge && porId){
          const j = DADOS[tabela].findIndex(x => String(x.id) === String(l.id));
          if (j >= 0){ DADOS[tabela][j] = novo; return novo; }
        }
        // merge-duplicates: substitui quem tem a mesma chave natural
        const chaves = { fin_plan:["competencia","category_id"], fin_months:["competencia"],
                         fin_balances:["competencia","account_id"], fin_categories:["nome"],
                         fin_accounts:["nome"], fin_settings:["user_id"] }[tabela];
        if (chaves){
          const j = DADOS[tabela].findIndex(x => chaves.every(k => x[k] === l[k]));
          if (j >= 0){ novo.id = DADOS[tabela][j].id; DADOS[tabela][j] = novo; return novo; }
        }
        DADOS[tabela].push(novo);
        return novo;
      });
      return json(out, 201);
    }
    if (metodo === "PATCH"){
      // filtros da URL que o app usa: col=eq.valor e col=is.null
      const filtros = (url.split("?")[1] || "").split("&").filter(Boolean).map(s => s.split("="));
      const passa = x => filtros.every(([k, v]) => {
        v = decodeURIComponent(v || "");
        if (v === "is.null") return x[k] === null || x[k] === undefined;
        if (v.indexOf("eq.") === 0) return String(x[k]) === v.slice(3);
        return true;
      });
      const linha = JSON.parse(opts.body);
      const alvos = DADOS[tabela].filter(passa);
      alvos.forEach(x => Object.assign(x, linha));
      // como o PostgREST: sem "return=representation" a resposta e 204, sem corpo --
      // inclusive quando o filtro nao achou linha nenhuma
      if (prefer.indexOf("return=representation") < 0) return new Response(null, { status: 204 });
      return json(alvos);
    }
    if (metodo === "DELETE"){
      // importacao de CDBs: apaga todos os lotes menos o novo
      const neq = (url.match(/lote=neq\.([^&]+)/) || [])[1];
      if (neq !== undefined){
        const fica = decodeURIComponent(neq);
        DADOS[tabela] = DADOS[tabela].filter(x => String(x.lote) === fica);
        return new Response(null, { status: 204 });
      }
      // desfazer uma simulacao apaga varios de uma vez: id=in.(a,b,c)
      const varios = (url.match(/id=in\.\(([^)]*)\)/) || [])[1];
      if (varios !== undefined){
        const fora = decodeURIComponent(varios).split(",");
        DADOS[tabela] = DADOS[tabela].filter(x => fora.indexOf(String(x.id)) < 0);
        return new Response(null, { status: 204 });
      }
      const id = (url.match(/id=eq\.([^&]+)/) || [])[1];
      DADOS[tabela] = DADOS[tabela].filter(x => String(x.id) !== id);
      return new Response(null, { status: 204 });
    }
    return json([], 400);
  };
})();
</script>
"""


def main():
    src = os.path.join(RAIZ, "index.html")
    dst = os.path.join(RAIZ, "tests", "preview.html")
    html = io.open(src, encoding="utf-8").read()

    # o script do app e o unico <script> sem atributos apos o </div> do toast
    marca = '<div id="toast"></div>\n\n<script>'
    if marca not in html:
        raise SystemExit("nao achei o ponto de injecao no index.html")
    html = html.replace(marca, '<div id="toast"></div>\n' + MOCK + "\n<script>", 1)

    # sem service worker no preview
    html = html.replace('if ("serviceWorker" in navigator){', 'if (false){')
    # caminho do manifest/sw sobe um nivel
    html = html.replace('href="manifest.json"', 'href="../manifest.json"')

    io.open(dst, "w", encoding="utf-8").write(html)
    print("gerado: %s (%d bytes)" % (dst, os.path.getsize(dst)))

    # sem o mock o preview cai no cache do localStorage e mostra "Sem conexao"
    # -- parece bug do app e nao e. Ja confundiu duas vezes.
    mock = os.path.join(RAIZ, "tests", "mock.json")
    if not os.path.exists(mock):
        print("")
        print("  !! FALTA tests/mock.json -- o preview vai abrir em modo offline.")
        print("     rode: python tools/importar_planilha.py --gerar --email <voce@exemplo.com>")
        print("")

if __name__ == "__main__":
    main()
