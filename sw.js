// Service worker do app Financas.
// Navegacao e NETWORK-FIRST de proposito: assim uma mudanca no index.html
// chega sem precisar de bump de cache. O cache so entra quando a rede falha.
const CACHE = "fin-v4";
const ESTATICOS = ["./", "./index.html", "./manifest.json",
                   "./icon-192.png", "./icon-512.png", "./icon-180.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ESTATICOS)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  // nunca cachear a API: dado financeiro velho servido como novo e pior que erro
  if (req.url.indexOf("supabase.co") !== -1) return;

  e.respondWith(
    fetch(req)
      .then(r => {
        if (r && r.ok && new URL(req.url).origin === location.origin){
          const copia = r.clone();
          caches.open(CACHE).then(c => c.put(req, copia));
        }
        return r;
      })
      .catch(() => caches.match(req).then(r => r || caches.match("./index.html")))
  );
});
