/**
 * sentry.client.config.ts — Sprint 44
 * Sentry browser-side SDK initialisation.
 * Activate by setting NEXT_PUBLIC_SENTRY_DSN in .env.local
 */
import * as Sentry from "@sentry/nextjs";

const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (SENTRY_DSN) {
    Sentry.init({
        dsn: SENTRY_DSN,
        environment: process.env.NODE_ENV ?? "development",

        // Capture 10% of transactions for performance monitoring
        tracesSampleRate: 0.1,

        // Session replay: 1% of sessions, 100% on error
        replaysSessionSampleRate: 0.01,
        replaysOnErrorSampleRate: 1.0,

        integrations: [
            Sentry.replayIntegration({
                maskAllText: true,
                blockAllMedia: true,
            }),
        ],

        // Ignore noisy browser errors that aren't actionable
        ignoreErrors: [
            "ResizeObserver loop limit exceeded",
            "ResizeObserver loop completed with undelivered notifications",
            "Non-Error promise rejection captured",
            /^Network request failed/,
            /^Failed to fetch/,
        ],

        beforeSend(event) {
            // Strip auth tokens from breadcrumbs
            if (event.request?.headers) {
                delete event.request.headers["Authorization"];
                delete event.request.headers["authorization"];
            }
            return event;
        },
    });
}
