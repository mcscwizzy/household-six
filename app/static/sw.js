const CACHE = 'household-six-shell-v2';
const SHELL = ['/', '/style.css', '/app.js', '/offline.js', '/manifest.webmanifest', '/logo.svg', '/icon.svg'];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys
    .filter(key => key.startsWith('household-six-shell-') && key !== CACHE)
    .map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== location.origin || !SHELL.includes(url.pathname) || url.search) return;
  event.respondWith(fetch(request).catch(() => caches.open(CACHE).then(cache => cache.match(url.pathname))));
});
