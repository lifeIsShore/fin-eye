"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useRef, useEffect } from "react";
import { useAuth } from "@/components/AuthProvider";
import {
    Settings, CreditCard, LogOut, ChevronDown, User,
    Activity, BarChart2, FlaskConical, Menu, X
} from "lucide-react";

// ── Nav item definitions ──────────────────────────────────────────────────────

const PRIMARY_NAV = [
    { href: "/",              label: "Dashboard" },
    { href: "/macro",         label: "Macro" },
    { href: "/news-sentiment",label: "Sentiment" },
    { href: "/backtesting",   label: "Backtest" },
    { href: "/portfolios",    label: "Portfolio" },
];

const MORE_NAV = [
    { href: "/sentiment",     label: "Retail Sentiment" },
    { href: "/sentiment-adv", label: "Adv. Sentiment" },
    { href: "/options",       label: "Options" },
    { href: "/sectors",       label: "Sectors" },
    { href: "/insiders",      label: "Insiders" },
    { href: "/earnings",      label: "Earnings" },
    { href: "/shorts",        label: "Shorts" },
    { href: "/fed-policy",    label: "Fed Policy" },
    { href: "/indicators",    label: "Indicators" },
    { href: "/hedge",         label: "Hedge" },
    { href: "/alerts",        label: "Alerts" },
    { href: "/learn",         label: "Learn" },
    { href: "/showcase",      label: "Pro Tools" },
    { href: "/community",     label: "Community" },
];

const ALL_NAV = [...PRIMARY_NAV, ...MORE_NAV];

// ── UserMenu ──────────────────────────────────────────────────────────────────

export function UserMenu() {
    const { user, logout } = useAuth();
    const [open, setOpen] = useState(false);
    const ref = useRef<HTMLDivElement>(null);

    useEffect(() => {
        function handler(e: MouseEvent) {
            if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
        }
        document.addEventListener("mousedown", handler);
        return () => document.removeEventListener("mousedown", handler);
    }, []);

    if (!user) return null;
    const initial = user.email[0].toUpperCase();

    return (
        <div className="relative" ref={ref}>
            <button
                onClick={() => setOpen((o) => !o)}
                className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 px-2 py-1.5 text-sm text-slate-300 hover:border-slate-600 hover:text-slate-100 transition-colors"
            >
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">
                    {initial}
                </span>
                <ChevronDown className={`h-3.5 w-3.5 text-slate-500 transition-transform ${open ? "rotate-180" : ""}`} />
            </button>

            {open && (
                <div className="absolute right-0 top-10 z-50 w-52 rounded-xl border border-slate-700 bg-slate-900 shadow-2xl">
                    <div className="border-b border-slate-800 px-4 py-3">
                        <div className="flex items-center gap-2">
                            <User className="h-4 w-4 text-slate-400" />
                            <div className="min-w-0">
                                <p className="truncate text-xs font-medium text-slate-200">{user.email}</p>
                                <p className={`text-[10px] font-medium ${user.is_pro ? "text-amber-400" : "text-slate-500"}`}>
                                    {user.is_pro ? "Pro Plan" : "Free Plan"}
                                </p>
                            </div>
                        </div>
                    </div>
                    <div className="py-1.5">
                        <Link href="/settings" onClick={() => setOpen(false)}
                            className="flex items-center gap-2.5 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800 hover:text-slate-100 transition-colors">
                            <Settings className="h-4 w-4 text-slate-400" /> Settings
                        </Link>
                        {user.is_admin && (<>
                            <Link href="/admin/ops" onClick={() => setOpen(false)}
                                className="flex items-center gap-2.5 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800 hover:text-slate-100 transition-colors">
                                <Activity className="h-4 w-4 text-slate-400" /> Ops Dashboard
                            </Link>
                            <Link href="/admin/analytics" onClick={() => setOpen(false)}
                                className="flex items-center gap-2.5 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800 hover:text-slate-100 transition-colors">
                                <BarChart2 className="h-4 w-4 text-indigo-400" /> Analytics
                            </Link>
                            <Link href="/admin/experiments" onClick={() => setOpen(false)}
                                className="flex items-center gap-2.5 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800 hover:text-slate-100 transition-colors">
                                <FlaskConical className="h-4 w-4 text-emerald-400" /> Experiments
                                <span className="ml-auto rounded-full bg-emerald-600/20 border border-emerald-500/30 px-1.5 py-0.5 text-[9px] font-bold text-emerald-400">NEW</span>
                            </Link>
                        </>)}
                        <Link href="/billing" onClick={() => setOpen(false)}
                            className="flex items-center gap-2.5 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800 hover:text-slate-100 transition-colors">
                            <CreditCard className="h-4 w-4 text-slate-400" /> Billing &amp; Plans
                            {!user.is_pro && (
                                <span className="ml-auto rounded-full bg-blue-600/20 border border-blue-500/30 px-1.5 py-0.5 text-[9px] font-bold text-blue-400">UPGRADE</span>
                            )}
                        </Link>
                    </div>
                    <div className="border-t border-slate-800 py-1.5">
                        <button onClick={() => { logout(); setOpen(false); }}
                            className="flex w-full items-center gap-2.5 px-4 py-2 text-sm text-red-400 hover:bg-red-950/30 hover:text-red-300 transition-colors">
                            <LogOut className="h-4 w-4" /> Sign Out
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}

// ── Desktop Nav ───────────────────────────────────────────────────────────────

export function Nav() {
    const pathname = usePathname();
    const [moreOpen, setMoreOpen] = useState(false);
    const moreRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        function handler(e: MouseEvent) {
            if (moreRef.current && !moreRef.current.contains(e.target as Node)) setMoreOpen(false);
        }
        document.addEventListener("mousedown", handler);
        return () => document.removeEventListener("mousedown", handler);
    }, []);

    const isMoreActive = MORE_NAV.some((item) => pathname === item.href);

    return (
        <nav className="hidden md:flex items-center gap-1">
            {PRIMARY_NAV.map((item) => {
                const active = pathname === item.href;
                return (
                    <Link key={item.href} href={item.href}
                        className={`whitespace-nowrap rounded-md px-2.5 py-1.5 text-sm font-medium transition-colors ${
                            active ? "bg-slate-800 text-slate-50" : "text-slate-400 hover:bg-slate-900 hover:text-slate-100"
                        }`}>
                        {item.label}
                    </Link>
                );
            })}

            {/* More dropdown */}
            <div className="relative" ref={moreRef}>
                <button
                    onClick={() => setMoreOpen((o) => !o)}
                    className={`flex items-center gap-1 whitespace-nowrap rounded-md px-2.5 py-1.5 text-sm font-medium transition-colors ${
                        isMoreActive || moreOpen ? "bg-slate-800 text-slate-50" : "text-slate-400 hover:bg-slate-900 hover:text-slate-100"
                    }`}
                >
                    More
                    <ChevronDown className={`h-3.5 w-3.5 transition-transform ${moreOpen ? "rotate-180" : ""}`} />
                </button>

                {moreOpen && (
                    <div className="absolute left-0 top-10 z-50 w-52 rounded-xl border border-slate-700 bg-slate-900 shadow-2xl py-1.5">
                        {MORE_NAV.map((item) => {
                            const active = pathname === item.href;
                            return (
                                <Link key={item.href} href={item.href} onClick={() => setMoreOpen(false)}
                                    className={`block px-4 py-2 text-sm transition-colors ${
                                        active ? "text-sky-400 bg-slate-800" : "text-slate-300 hover:bg-slate-800 hover:text-slate-100"
                                    }`}>
                                    {item.label}
                                </Link>
                            );
                        })}
                    </div>
                )}
            </div>
        </nav>
    );
}

// ── Mobile Drawer Nav ─────────────────────────────────────────────────────────

export function MobileNav() {
    const pathname = usePathname();
    const [open, setOpen] = useState(false);

    // Close drawer on route change
    useEffect(() => { setOpen(false); }, [pathname]);

    return (
        <>
            {/* Hamburger trigger */}
            <button
                onClick={() => setOpen(true)}
                className="md:hidden flex items-center justify-center rounded-lg border border-slate-700 bg-slate-900 p-2 text-slate-300 hover:text-slate-100 transition-colors"
                aria-label="Open menu"
            >
                <Menu className="h-5 w-5" />
            </button>

            {/* Overlay */}
            {open && (
                <div className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden"
                    onClick={() => setOpen(false)} />
            )}

            {/* Drawer */}
            <div className={`fixed top-0 left-0 z-50 h-full w-72 bg-slate-950 border-r border-slate-800 flex flex-col transition-transform duration-300 md:hidden ${
                open ? "translate-x-0" : "-translate-x-full"
            }`}>
                {/* Drawer header */}
                <div className="flex items-center justify-between px-4 py-4 border-b border-slate-800">
                    <span className="text-lg font-semibold text-slate-100">Fin-Eye</span>
                    <button onClick={() => setOpen(false)}
                        className="rounded-lg p-1.5 text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors">
                        <X className="h-5 w-5" />
                    </button>
                </div>

                {/* Drawer links */}
                <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
                    {ALL_NAV.map((item) => {
                        const active = pathname === item.href;
                        return (
                            <Link key={item.href} href={item.href}
                                className={`flex items-center rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                                    active ? "bg-slate-800 text-sky-400" : "text-slate-300 hover:bg-slate-800/60 hover:text-slate-100"
                                }`}>
                                {item.label}
                            </Link>
                        );
                    })}
                </nav>

                {/* Drawer footer */}
                <div className="border-t border-slate-800 px-4 py-3">
                    <Link href="/settings"
                        className="flex items-center gap-2 text-sm text-slate-400 hover:text-slate-200 transition-colors">
                        <Settings className="h-4 w-4" /> Settings
                    </Link>
                </div>
            </div>
        </>
    );
}
