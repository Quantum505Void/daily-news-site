const CACHE = "xiaoxin-v1";
const PRECACHE = [
  "/daily-news-site/",
  "/daily-news-site/manifest.json",
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(PRECACHE))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);

  // manifest & JSON data: network first, fall back to cache
  if (url.pathname.includes("manifest.json") || url.pathname.includes("/data/")) {
    e.respondWith(
      fetch(e.request)
        .then((r) => {
          const clone = r.clone();
          caches.open(CACHE).then((c) => c.put(e.request, clone));
          return r;
        })
        .catch(() => caches.match(e.request))
    );
    return;
  }

  // assets: cache first
  if (url.pathname.includes("/_assets/")) {
    e.respondWith(
      caches.match(e.request).then((r) => r ?? fetch(e.request).then((res) => {
        caches.open(CACHE).then((c) => c.put(e.request, res.clone()));
        return res;
      }))
    );
    return;
  }

  // HTML: network first
  e.respondWith(
    fetch(e.request).catch(() => caches.match(e.request))
  );
});
