import "./globals.css";
import type { ReactNode } from "react";
import Link from "next/link";
import { Nav, UserMenu } from "../components/Nav";
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
                        <div className="mx-auto flex min-h-screen max-w-6xl flex-col px-4 py-6">
                            <header className="mb-6 flex flex-col gap-4 border-b border-slate-800 pb-4 lg:flex-row lg:items-center lg:justify-between lg:gap-8">
                                <div className="flex items-center justify-between gap-4">
                                    <div className="flex-shrink-0">
                                        <h1 className="text-2xl font-semibold tracking-tight">Fin-Eye</h1>
                                        <p className="text-sm text-slate-400">
                                            Educational market intelligence · not investment advice
                                        </p>
                                    </div>
                                    <div className="lg:hidden flex-shrink-0">
                                        <UserMenu />
                                    </div>
                                </div>
                                <div className="flex w-full min-w-0 flex-1 items-center lg:w-auto lg:justify-end">
                                    <Nav />
                                    <div className="hidden lg:block ml-4 flex-shrink-0">
                                        <UserMenu />
                                    </div>
                                </div>
                            </header>
                            <main className="flex-1">{children}</main>

                            {/* Footer with legal links */}
                            <footer className="mt-8 border-t border-slate-800 pt-5">
                                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                                    <p className="text-xs text-slate-500">
                                        Fin-Eye is for educational purposes only and does not constitute
                                        investment advice. Trading involves risk of loss.
                                    </p>
                                    <nav className="flex flex-wrap gap-3 text-xs text-slate-500">
                                        <Link href="/legal/terms" className="hover:text-slate-300 transition-colors">
                                            Terms of Service
                                        </Link>
                                        <span className="text-slate-700">·</span>
                                        <Link href="/legal/privacy" className="hover:text-slate-300 transition-colors">
                                            Privacy Policy
                                        </Link>
                                        <span className="text-slate-700">·</span>
                                        <Link href="/legal/disclaimer" className="hover:text-slate-300 transition-colors">
                                            Risk Disclaimer
                                        </Link>
                                        <span className="text-slate-700">·</span>
                                        <Link href="/community" className="hover:text-slate-300 transition-colors">
                                            Community
                                        </Link>
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
