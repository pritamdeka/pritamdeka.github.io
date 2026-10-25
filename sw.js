// Service Worker — network-first for ALL resources (always fresh, offline fallback)
const CACHE = 'pd-site-v24';

self.addEventListener('install', (e) => {
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  // Leave cross-origin requests (CDNs, APIs, analytics) to the browser
  if (new URL(req.url).origin !== self.location.origin) return;

  // Network-first for everything: always try to fetch fresh content,
  // fall back to cache only when offline.
  e.respondWith(
    fetch(req).then((res) => {
      // Cache a copy of good responses for offline use
      if (res.ok) {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy));
      }
      return res;
    }).catch(() => caches.match(req))
  );
});
