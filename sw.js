// Service Worker — offline-first shell caching for pritamdeka.github.io
const CACHE = 'pd-site-v1';
const SHELL = [
  './',
  './index.html',
  './education.html',
  './papers.html',
  './activities.html',
  './blog.html',
  './style-dynamic.css',
  './dynamic.js',
  './favicon.svg',
  './citations.json',
  './citations-history.json',
  './profile.jpg'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// Network-first for HTML/docs (fresh content), cache-first for static assets
self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  // Never cache cross-origin (CDN fonts, APIs) — let network handle them
  if (url.origin !== self.location.origin) return;

  const isDoc = req.destination === 'document' || url.pathname.endsWith('.json');

  if (isDoc) {
    e.respondWith(
      fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy));
        return res;
      }).catch(() => caches.match(req).then((r) => r || caches.match('./index.html')))
    );
  } else {
    e.respondWith(
      caches.match(req).then((r) => r || fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy));
        return res;
      }).catch(() => caches.match(req)))
    );
  }
});
