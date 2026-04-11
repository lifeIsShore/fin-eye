/**
 * public/sw.js — Fin-Eye Service Worker (Sprint 44)
 *
 * Strategy: Cache-first for static assets, network-first for API calls,
 * stale-while-revalidate for dashboard data so the app loads offline
 * showing the last-seen GAS snapshot / macro data.
 *
 * Cached API routes (stale-while-revalidate, 5-min TTL):
 *   /api/v1/admin/gas/snapshots/*
 *   /api/v1/macro/latest
 *   /api/v1/watchlist
 */

const CACHE_VERSION = "fin-eye-v1";
const STATIC_CACHE  = `${CACHE_VERSION}-static`;
const DATA_CACHE    = `${CACHE_VERSION}-data`;

const STATIC_ASSETS = ["/", "/explore", "/macro", "/learn"];

const DATA_ROUTES = [
    "/api/v1/admin/gas/snapshots/",
    "/api/v1/macro/latest",
    "/api/v1/watchlist",
];

// ── Install: pre-cache static shell ─────────────────────────────────────────
self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(STATIC_CACHE).then((cache) =>
            cache.addAll(STATIC_ASSETS).catch(() => {
                // Non-fatal — routes may not be pre-renderable
            })
        )
    );
    self.skipWaiting();
});

// ── Activate: purge old caches ───────────────────────────────────────────────
self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(
                keys
                    .filter((k) => k.startsWith("fin-eye-") && k !== STATIC_CACHE && k !== DATA_CACHE)
                    .map((k) => caches.delete(k))
            )
        )
    );
    self.clients.claim();
});

// ── Fetch: route-aware strategy ──────────────────────────────────────────────
self.addEventListener("fetch", (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // Only handle GET requests on same origin (or API calls)
    if (request.method !== "GET") return;

    const isDataRoute = DATA_ROUTES.some((r) => url.pathname.startsWith(r));

    if (isDataRoute) {
        // Stale-while-revalidate: serve cache immediately, update in background
        event.respondWith(
            caches.open(DATA_CACHE).then(async (cache) => {
                const cached = await cache.match(request);
                const fetchPromise = fetch(request)
                    .then((res) => {
                        if (res.ok) cache.put(request, res.clone());
                        return res;
                    })
                    .catch(() => cached); // network failed — fall back to cache

                return cached ?? fetchPromise;
            })
        );
        return;
    }

    // Network-first for everything else (auth, SSE, mutations)
    // Falls back to cache only for navigation requests
    if (request.mode === "navigate") {
        event.respondWith(
            fetch(request).catch(() =>
                caches.match(request).then((r) => r ?? caches.match("/"))
            )
        );
    }
});
