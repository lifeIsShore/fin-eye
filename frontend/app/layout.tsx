import "./globals.css";
import type { ReactNode } from "react";
import Link from "next/link";
import { Nav, UserMenu, MobileNav } from "../components/Nav";
import { AuthProvider } from "../components/AuthProvider";
import { ConsentGate } from "../components/ConsentGate";

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
                        <div className="mx-auto flex min-h-screen max-w-7xl flex-col px-4 sm:px-6 py-4 sm:py-6">

                            {/* ── Header ──────────────────────────────────────── */}
                            <header className="mb-6 border-b border-slate-800 pb-4">
                                <div className="flex items-center justify-between gap-4">

                                    {/* Left — Logo (always fixed width, never squeezed) */}
                                    <div className="flex-shrink-0">
                                        <Link href="/" className="block">
                                            <h1 className="text-xl font-bold tracking-tight text-slate-100 hover:text-white transition-colors">
                                                Fin-Eye
                                            </h1>
                                        </Link>
                                        <p className="hidden sm:block text-xs text-slate-500 mt-0.5">
                                            Market intelligence · not investment advice
                                        </p>
                                    </div>

                                    {/* Centre — Desktop nav */}
                                    <div className="flex-1 flex justify-center">
                                        <Nav />
                                    </div>

                                    {/* Right — User menu + mobile hamburger */}
                                    <div className="flex-shrink-0 flex items-center gap-2">
                                        <UserMenu />
                                        <MobileNav />
                                    </div>

                                </div>
                            </header>

                            {/* ── Main ────────────────────────────────────────── */}
                            <main className="flex-1">{children}</main>

                            {/* ── Footer ──────────────────────────────────────── */}
                            <footer className="mt-8 border-t border-slate-800 pt-5">
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
                    </ConsentGate>
                </AuthProvider>
            </body>
        </html>
    );
}
