/* Service Worker: haelt die App offline verfuegbar.
   Bei jeder Aenderung an index.html die Version hochzaehlen - sonst
   liefern Geraete weiter den alten Stand aus dem Cache. */
const VERSION = "aufmass-v1";
const SCHALE = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./icon-192.png",
  "./icon-512.png",
  "https://cdnjs.cloudflare.com/ajax/libs/pdf-lib/1.17.1/pdf-lib.min.js"
];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(SCHALE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(namen => Promise.all(namen.filter(n => n !== VERSION).map(n => caches.delete(n))))
      .then(() => self.clients.claim())
  );
});

/* Netz zuerst, Cache als Rueckfall: online gibt es immer den neuen Stand,
   ohne Empfang laeuft die App aus dem Cache weiter. */
self.addEventListener("fetch", e => {
  if(e.request.method !== "GET") return;
  e.respondWith(
    fetch(e.request)
      .then(antwort => {
        const kopie = antwort.clone();
        caches.open(VERSION).then(c => c.put(e.request, kopie)).catch(() => {});
        return antwort;
      })
      .catch(() => caches.match(e.request).then(t => t || caches.match("./index.html")))
  );
});
