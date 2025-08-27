const CACHE_NAME = 'refiloe-v1';
const urlsToCache = [
  '/',
  '/static/manifest.json'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;

  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) {
          return response;
        }
        return fetch(event.request).then(response => {
          if (!response || response.status !== 200) {
            return response;
          }
          const responseToCache = response.clone();
          caches.open(CACHE_NAME).then(cache => {
            if (event.request.url.includes('/d/') || 
                event.request.url.includes('/dashboard/')) {
              cache.put(event.request, responseToCache);
            }
          });
          return response;
        });
      })
      .catch(() => {
        if (event.request.destination === 'document') {
          return new Response('<h1>Offline</h1><p>Please check your connection</p>', {
            headers: { 'Content-Type': 'text/html' }
          });
        }
      })
  );
});
