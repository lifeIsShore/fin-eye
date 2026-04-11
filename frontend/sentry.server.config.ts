/**
 * sentry.server.config.ts — Sprint 44
 * Sentry server-side (Node.js / Next.js API routes) SDK initialisation.
 * Activate by setting SENTRY_DSN in .env.local (server-only, no NEXT_PUBLIC_)
 */
import * as Sentry from "@sentry/nextjs";

const SENTRY_DSN = process.env.SENTRY_DSN ?? process.env.NEXT_PUBLIC_SENTRY_DSN;

if (SENTRY_DSN) {
    Sentry.init({
        dsn: SENTRY_DSN,
        environment: process.env.NODE_ENV ?? "development",

        // Lower sample rate on server — high-volume routes would flood quota
        tracesSampleRate: 0.05,

        // Alert when error rate exceeds 1% — configured in Sentry dashboard
        // (set alert threshold there, not here)

        beforeSend(event) {
            // Strip sensitive fields from server-side events
            if (event.request?.headers) {
                delete event.request.headers["Authorization"];
                delete event.request.headers["Cookie"];
            }
            return event;
        },
    });
}
