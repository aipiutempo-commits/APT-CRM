// Service Worker – CRM PWA
// Strategia: Cache First per asset statici, Network First per API

const CACHE_NAME = 'crm-v1';
const API_CACHE = 'crm-api-v1';

// Asset da mettere in cache al primo avvio (app shell)
const SHELL_ASSETS = [
  '/',
  '/manifest.json',
  '/static/css/app.css',
  '/static/js/app.js',
  '/static/js/api.js',
];

// ─── Install ──────────────────────────────────────────────────────────────
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(SHELL_ASSETS))
      .then(() => self.skipWaiting())
  );
});

// ─── Activate ─────────────────────────────────────────────────────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => k !== CACHE_NAME && k !== API_CACHE)
            .map(k => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

// ─── Fetch ────────────────────────────────────────────────────────────────
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Ignora richieste non-GET
  if (event.request.method !== 'GET') return;

  // API: Network First, fallback su cache (solo GET)
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirstAPI(event.request));
    return;
  }

  // Asset statici e pagina: Cache First
  event.respondWith(cacheFirst(event.request));
});

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    // Offline e non in cache: ritorna pagina principale se possibile
    const fallback = await caches.match('/');
    return fallback || new Response('Offline', { status: 503 });
  }
}

async function networkFirstAPI(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(API_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    return new Response(JSON.stringify({ error: 'Offline', cached: false }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
