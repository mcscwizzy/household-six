const CACHE = 'household-six-shell-v19';
const SHELL = ['/', '/style.css', '/app.js', '/offline.js', '/shopping.js', '/html.js', '/calendar.js', '/chores.js', '/rewards.js', '/meals.js', '/six.js', '/members-life.js', '/inventory.js', '/property-care.js', '/announcements.js', '/dashboard.js', '/dates.js', '/manifest.webmanifest', '/logo.svg', '/icon.svg',
  '/apple-touch-icon.png', '/pwa-192.png', '/pwa-512.png', '/pwa-maskable-512.png'];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(SHELL.map(path => new Request(path, { cache: 'reload' })))).then(() => self.skipWaiting()));
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
