import "./globals.css";
import type { ReactNode } from "react";
import Link from "next/link";
import { Sidebar, UserMenu, MobileNav } from "../components/Nav";
import { GlobalTickerSearch } from "../components/GlobalTickerSearch";
import { AuthProvider } from "../components/AuthProvider";
import { ConsentGate } from "../components/ConsentGate";
import { SymbolProvider } from "../lib/symbolContext";
import { ToastProvider } from "../components/ToastProvider";

export const metadata = {
    title: "Fin-Eye",
    description: "Understand the forces behind price movements",
};

export default function RootLayout({ children }: { children: ReactNode }) {
    return (
        <html lang="en">
            <body className="min-h-screen bg-slate-950 text-slate-50 antialiased">
                <AuthProvider>
                    <ConsentGate>
                        <SymbolProvider>
                            {/* ToastProvider wraps everything so any component can call useToast() */}
                            <ToastProvider>
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

                                        {/* ── Page content ────────────────────── */}
                                        <main className="flex-1 px-4 sm:px-6 py-6">
                                            {children}
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
                        </SymbolProvider>
                    </ConsentGate>
                </AuthProvider>
            </body>
        </html>
    );
}
