// Supabase Edge Function "pluggy-cdbs" -- posicao de renda fixa da XP e do BTG
// pelo Open Finance (Meu Pluggy), para a aba Vencimentos do app Financas.
//
// A chave da Pluggy NUNCA vai ao navegador: fica nos Secrets do Supabase e so esta
// funcao a usa. O app chama com o JWT do usuario (conferido no Auth do Supabase) e
// recebe so os campos que usa; quem grava em fin_cdbs e o proprio app, com RLS.
// No painel, "Verify JWT with legacy secret" fica DESLIGADO: a conferencia e aqui.
//
// Secrets (painel do Supabase > Edge Functions > Secrets):
//   PLUGGY_CLIENT_ID      Client ID da Application no dashboard.pluggy.ai
//   PLUGGY_CLIENT_SECRET  Client Secret da mesma Application
//   PLUGGY_ITEM_IDS       Item IDs das conexoes, separados por virgula, cada um com o
//                         nome da corretora na frente: "XP:<id>,BTG:<id>". Pelo Meu
//                         Pluggy todo item se chama "MeuPluggy" -- sem o nome, a
//                         corretora que falhar nao tem como manter a posicao dela.
//   DONO_UID (opcional)   uid do usuario do app: qualquer outro token e barrado
//
// JavaScript puro (que tambem e TypeScript valido) e sem import: o mesmo arquivo roda
// no Supabase e em tests/test_pluggy_funcao.html, com Deno e fetch falsos.

const API = "https://api.pluggy.ai";
const ORIGENS = ["https://vitorruizz-web.github.io", "http://localhost:8765", "http://127.0.0.1:8765"];
// o que o app usa de cada investimento -- nome do titular e conta ficam aqui; das
// transacoes vai so o enxuto de cada movimentacao (movimentosDe)
const CAMPOS = ["id", "name", "code", "type", "subtype", "issuer", "status", "balance", "amount",
                "amountOriginal", "taxes", "taxes2", "date", "dueDate", "issueDate", "rate", "rateType",
                "fixedAnnualRate"];

function cors(req) {
  const o = req.headers.get("origin") || "";
  return {
    "Access-Control-Allow-Origin": ORIGENS.includes(o) ? o : ORIGENS[0],
    "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Vary": "Origin",
  };
}

// Quem chama. O gateway do Supabase so confere JWT assinado pelo segredo LEGADO -- e a
// chave anon, que e publica, passaria por ele. A verificacao de verdade e aqui: o
// proprio Auth do Supabase diz se o token e de um usuario valido (serve para as chaves
// legadas e para as novas). A chave `apikey` e a publica que o app ja manda.
async function usuarioDoToken(req) {
  const token = (req.headers.get("authorization") || "").replace(/^Bearer\s+/i, "").trim();
  const base = String(Deno.env.get("SUPABASE_URL") || "").replace(/\/+$/, "");
  const chave = req.headers.get("apikey") || Deno.env.get("SUPABASE_ANON_KEY") || "";
  if (!token || !base) return null;
  try {
    const r = await fetch(base + "/auth/v1/user", { headers: { "Authorization": "Bearer " + token, "apikey": chave } });
    if (!r.ok) return null;
    const u = await r.json();
    return u && u.id ? u : null;
  } catch (e) {
    return null;
  }
}

function enxuto(x, conector) {
  const o = { conector: conector || null };
  for (const k of CAMPOS) o[k] = x[k] === undefined ? null : x[k];
  o.instituicao = (x.institution && x.institution.name) || null;
  o.movimentos = null;
  return o;
}

// "XP:<id>" -> { rotulo: "XP", id }; "<id>" -> { rotulo: null, id }
function lerItens(s) {
  return String(s || "").split(/[\s,;]+/).filter(Boolean).map((t) => {
    const m = /^([^:=]+)[:=](.+)$/.exec(t);
    return m ? { rotulo: m[1].trim(), id: m[2].trim() } : { rotulo: null, id: t };
  });
}

// Renda fixa BANCARIA: e o que o calendario usa, e o que precisa das compras.
const BANCARIA = { CDB: 1, RDB: 1, LC: 1, LCI: 1, LCA: 1 };
// A taxa que a Pluggy manda e a da EMISSAO do titulo. Quem comprou no mercado
// secundario rende a taxa da COMPRA -- e so a data e o valor da compra permitem
// chegar nela. Vem das movimentacoes de cada investimento (1 pedido por titulo;
// o limite da Pluggy e 360/min por rota).
async function movimentosDe(x, h) {
  try {
    const r = await fetch(API + "/investments/" + encodeURIComponent(x.id) + "/transactions?pageSize=500", { headers: h });
    if (!r.ok) return null;
    const p = await r.json();
    return (p.results || []).map((t) => ({
      tipo: t.type || null, data: t.date || null, liquidacao: t.tradeDate || null, qtd: t.quantity ?? null,
      pu: t.value ?? null, valor: t.amount ?? null, liquido: t.netAmount ?? null, taxa: t.agreedRate ?? null,
    }));
  } catch (e) {
    return null;
  }
}
async function comMovimentos(lista, h) {
  const alvo = lista.filter((x) => BANCARIA[String(x.subtype || "").toUpperCase()] &&
                                   x.status !== "TOTAL_WITHDRAWAL" && +x.balance > 0);
  let i = 0;
  const trabalhador = async () => { while (i < alvo.length) { const x = alvo[i++]; x.movimentos = await movimentosDe(x, h); } };
  await Promise.all([1, 2, 3, 4, 5, 6].map(trabalhador));
}

async function tratar(req) {
  const cab = cors(req);
  const responder = (corpo, status) => new Response(JSON.stringify(corpo),
    { status: status || 200, headers: Object.assign({ "Content-Type": "application/json" }, cab) });
  if (req.method === "OPTIONS") return new Response("ok", { headers: cab });
  if (req.method !== "POST") return responder({ erro: "metodo" }, 405);

  const env = (k) => String(Deno.env.get(k) || "").trim();
  const usuario = await usuarioDoToken(req);
  if (!usuario) return responder({ erro: "nao_autenticado" }, 401);
  const dono = env("DONO_UID");
  if (dono && usuario.id !== dono) return responder({ erro: "proibido" }, 403);
  const falta = ["PLUGGY_CLIENT_ID", "PLUGGY_CLIENT_SECRET", "PLUGGY_ITEM_IDS"].filter((k) => !env(k));
  if (falta.length) return responder({ erro: "configuracao", falta: falta }, 500);

  // apiKey vale 2 h; uma por sincronizacao basta
  let apiKey;
  try {
    const a = await fetch(API + "/auth", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ clientId: env("PLUGGY_CLIENT_ID"), clientSecret: env("PLUGGY_CLIENT_SECRET") }),
    });
    if (!a.ok) return responder({ erro: "pluggy_auth", status: a.status }, 502);
    apiKey = (await a.json()).apiKey;
  } catch (e) {
    return responder({ erro: "pluggy_rede" }, 502);
  }
  const h = { "X-API-KEY": apiKey };

  // Uma conexao com problema (consentimento vencido, instabilidade) nao derruba as
  // outras: o erro vai no item e o app decide o que fazer com a posicao dela.
  const saida = { geradoEm: new Date().toISOString(), itens: [], investimentos: [] };
  const nomes = {};
  for (const { rotulo, id } of lerItens(env("PLUGGY_ITEM_IDS"))) {
    const item = { id: id, conector: rotulo, status: null, atualizadoEm: null, consentimentoAte: null, erro: null };
    try {
      const ri = await fetch(API + "/items/" + encodeURIComponent(id), { headers: h });
      if (!ri.ok) item.erro = "item HTTP " + ri.status;
      else {
        const it = await ri.json();
        let nome = rotulo || (it.connector && it.connector.name) || null;
        // dois itens sem rotulo com o mesmo conector (todo item do Meu Pluggy) ganham numero
        if (nome && !rotulo) { nomes[nome] = (nomes[nome] || 0) + 1; if (nomes[nome] > 1) nome += " " + nomes[nome]; }
        item.conector = nome;
        item.status = it.status || null;
        item.atualizadoEm = it.lastUpdatedAt || it.updatedAt || null;
        item.consentimentoAte = it.consentExpiresAt || null;
        item.erro = (it.error && it.error.message) || null;
        const doItem = [];
        for (let pagina = 1; pagina <= 20; pagina++) {
          const rv = await fetch(API + "/investments?itemId=" + encodeURIComponent(id) +
                                 "&type=FIXED_INCOME&pageSize=500&page=" + pagina, { headers: h });
          if (!rv.ok) { item.erro = "investimentos HTTP " + rv.status; break; }
          const p = await rv.json();
          for (const x of p.results || []) doItem.push(enxuto(x, item.conector));
          if (pagina >= (p.totalPages || 1)) break;
        }
        await comMovimentos(doItem, h);
        saida.investimentos.push(...doItem);
      }
    } catch (e) {
      item.erro = "sem resposta da Pluggy";
    }
    saida.itens.push(item);
  }
  return responder(saida);
}

Deno.serve(tratar);
