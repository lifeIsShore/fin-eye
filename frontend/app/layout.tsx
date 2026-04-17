import "./globals.css";
import type { ReactNode } from "react";
import Link from "next/link";
import { Sidebar, UserMenu, MobileNav } from "../components/Nav";
import { GlobalTickerSearch } from "../components/GlobalTickerSearch";
import { AuthProvider } from "../components/AuthProvider";
import { ConsentGate } from "../components/ConsentGate";
import { SymbolProvider } from "../lib/symbolContext";
import { ToastProvider } from "../components/ToastProvider";
import CommandPalette from "../components/CommandPalette";
import EmailVerificationBanner from "../components/EmailVerificationBanner";
import { PageTransition } from "../components/PageTransition";
import { NpsSurvey } from "../components/NpsSurvey";

export const metadata = {
    title: "Fin-Eye",
    description: "Understand the forces behind price movements",
};

// Sprint 44 — Service worker registration script (runs once after first paint)
const REGISTER_SW_SCRIPT = `
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
      navigator.serviceWorker.register('/sw.js').catch(function() {});
    });
  }
`;

// Sprint 43 — Restore compact/currency prefs on page load
const RESTORE_PREFS_SCRIPT = `
  try {
    if (localStorage.getItem('fin-eye-compact') === 'true') {
      document.documentElement.classList.add('fin-eye-compact');
    }
  } catch (e) {}
`;

export default function RootLayout({ children }: { children: ReactNode }) {
    return (
        <html lang="en">
            <head>
                {/* Restore compact mode before first paint to avoid flash */}
                <script dangerouslySetInnerHTML={{ __html: RESTORE_PREFS_SCRIPT }} />
                {/* Sprint 44 — PWA manifest + SW registration */}
                <link rel="manifest" href="/manifest.json" />
                <meta name="theme-color" content="#020617" />
                <script dangerouslySetInnerHTML={{ __html: REGISTER_SW_SCRIPT }} />
            </head>
            <body className="min-h-screen bg-slate-950 text-slate-50 antialiased">
                <AuthProvider>
                    <ConsentGate>
                        <SymbolProvider>
                            {/* ToastProvider wraps everything so any component can call useToast() */}
                            <ToastProvider>
                                {/* Global ⌘K / Ctrl+K command palette */}
                                <CommandPalette />
                                {/* Sprint 49 — NPS survey (fires on 7th session or 30 days) */}
                                <NpsSurvey />
                                {/*
                                 * Layout:
                                 * ┌──────────┬───────────────────────────────────────────────┐
                                 * │          │  Top bar: [mobile logo] [ticker search] [user] │
                                 * │ Sidebar  ├───────────────────────────────────────────────┤
                                 * │ (lg+)    │  Page content                                 │
                                 * └──────────┴───────────────────────────────────────────────┘
                                 */}
                                <div className="flex min-h-screen">

                                    {/* ── Left Sidebar (desktop lg+) ──────────── */}
                                    <Sidebar />

                                    {/* ── Right: top bar + content + footer ───── */}
                                    <div className="flex flex-1 flex-col min-w-0">

                                        {/* ── Top bar ─────────────────────────── */}
                                        <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-slate-800 bg-slate-950/95 backdrop-blur-sm px-4 sm:px-6 py-3">

                                            {/* Mobile logo (hidden on desktop — logo lives in sidebar) */}
                                            <div className="lg:hidden flex-shrink-0">
                                                <Link href="/">
                                                    <span className="text-base font-bold text-slate-100">Fin-Eye</span>
                                                </Link>
                                            </div>

                                            {/* Global ticker search — centre of top bar */}
                                            <div className="flex flex-1 justify-center lg:justify-start">
                                                <GlobalTickerSearch />
                                            </div>

                                            {/* Right side: user menu + mobile hamburger */}
                                            <div className="flex items-center gap-2 flex-shrink-0">
                                                <UserMenu />
                                                <MobileNav />
                                            </div>
                                        </header>

                                        {/* ── Email verification banner (SEC-07) ─── */}
                                        <EmailVerificationBanner />

                                        {/* ── Page content ────────────────────── */}
                                        <main className="flex-1 px-4 sm:px-6 py-6">
                                            <PageTransition>{children}</PageTransition>
                                        </main>

                                        {/* ── Footer ──────────────────────────── */}
                                        <footer className="border-t border-slate-800 px-4 sm:px-6 py-5">
                                            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                                                <p className="text-xs text-slate-500">
                                                    Fin-Eye is for educational purposes only and does not constitute
                                                    investment advice. Trading involves risk of loss.
                                                </p>
                                                <nav className="flex flex-wrap gap-3 text-xs text-slate-500">
                                                    <Link href="/legal/terms" className="hover:text-slate-300 transition-colors">Terms of Service</Link>
                                                    <span className="text-slate-700">·</span>
                                                    <Link href="/legal/privacy" className="hover:text-slate-300 transition-colors">Privacy Policy</Link>
                                                    <span className="text-slate-700">·</span>
                                                    <Link href="/legal/disclaimer" className="hover:text-slate-300 transition-colors">Risk Disclaimer</Link>
                                                    <span className="text-slate-700">·</span>
                                                    <Link href="/community" className="hover:text-slate-300 transition-colors">Community</Link>
                                                </nav>
                                            </div>
                                        </footer>
                                    </div>

                                </div>
                            </ToastProvider>
                            <NpsSurvey />
                        </SymbolProvider>
                    </ConsentGate>
                </AuthProvider>
            </body>
        </html>
    );
}
