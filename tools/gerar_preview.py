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
    if (!carregado) carregado = (await (await realFetch("./mock.json")).json());
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

    if (metodo === "POST"){
      const linhas = JSON.parse(opts.body);
      const out = linhas.map((l, i) => {
        const novo = Object.assign({ id: tabela + "-" + Date.now() + "-" + i }, l);
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
      const id = (url.match(/id=eq\.([^&]+)/) || [])[1];
      const linha = JSON.parse(opts.body);
      const j = DADOS[tabela].findIndex(x => String(x.id) === id);
      if (j >= 0) Object.assign(DADOS[tabela][j], linha);
      return json(j >= 0 ? [DADOS[tabela][j]] : []);
    }
    if (metodo === "DELETE"){
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


if __name__ == "__main__":
    main()
