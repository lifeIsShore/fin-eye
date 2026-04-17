/**
 * frontend/lib/posthog.ts — Sprint 49
 * PostHog analytics helper. No-ops gracefully when NEXT_PUBLIC_POSTHOG_KEY is unset.
 */

const POSTHOG_KEY  = process.env.NEXT_PUBLIC_POSTHOG_KEY ?? "";
const POSTHOG_HOST = "https://app.posthog.com";

let _initialised = false;

export function initPostHog(): void {
    if (_initialised || !POSTHOG_KEY || typeof window === "undefined") return;
    import("posthog-js").then(({ default: posthog }) => {
        posthog.init(POSTHOG_KEY, {
            api_host:          POSTHOG_HOST,
            capture_pageview:  true,
            capture_pageleave: true,
            autocapture:       false,  // manual events only — reduce noise
        });
        _initialised = true;
    }).catch(() => {/* posthog-js not installed — silent no-op */});
}

export function trackEvent(name: string, props?: Record<string, unknown>): void {
    if (!POSTHOG_KEY || typeof window === "undefined") return;
    import("posthog-js").then(({ default: posthog }) => {
        posthog.capture(name, props ?? {});
    }).catch(() => {});
}

export function identifyUser(userId: string, traits?: Record<string, unknown>): void {
    if (!POSTHOG_KEY || typeof window === "undefined") return;
    import("posthog-js").then(({ default: posthog }) => {
        posthog.identify(userId, traits ?? {});
    }).catch(() => {});
}
