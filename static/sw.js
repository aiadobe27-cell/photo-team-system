const CACHE_NAME = 'phototeam-erp-v11-11-offline-v1';
const CORE_ASSETS = [
  '/',
  '/reservations',
  '/daily-sales',
  '/bank-accounts',
  '/static/img/photo_team_icon.png',
  '/static/css/core/base.css',
  '/static/css/core/components.css',
  '/static/css/core/interactions.css',
  '/static/css/core/context-menu.css',
  '/static/css/core/command-dock.css',
  '/static/js/core/app.js',
  '/static/js/pages/reservations.js',
  '/static/js/pages/daily_sales.js',
  '/static/js/pages/bank_accounts.js'
];

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return Promise.allSettled(CORE_ASSETS.map((url) => cache.add(url)));
    })
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // For API calls: network-first, fallback to cache if offline
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(req)
        .then((res) => {
          if (res && res.status === 200) {
            const copy = res.clone();
            caches.open(CACHE_NAME).then((c) => c.put(req, copy));
          }
          return res;
        })
        .catch(() => caches.match(req))
    );
    return;
  }

  // For HTML pages & static assets: network-first with cache fallback so updates arrive immediately when online
  event.respondWith(
    fetch(req)
      .then((res) => {
        if (res && res.status === 200) {
          const copy = res.clone();
          caches.open(CACHE_NAME).then((c) => c.put(req, copy));
        }
        return res;
      })
      .catch(() => caches.match(req).then((cached) => cached || caches.match('/')))
  );
});
