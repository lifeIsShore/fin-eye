"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useRef, useEffect } from "react";
import { useAuth } from "@/components/AuthProvider";
import { Settings, CreditCard, LogOut, ChevronDown, User, Activity, BarChart2, FlaskConical } from "lucide-react";

const NAV_ITEMS = [
    { href: "/", label: "Dashboard" },
    { href: "/macro", label: "Macro" },
    { href: "/news-sentiment", label: "Sentiment" },
    { href: "/sentiment", label: "Retail" },
    { href: "/options", label: "Options" },
    { href: "/sectors", label: "Sectors" },
    { href: "/insiders", label: "Insiders" },
    { href: "/earnings", label: "Earnings" },
    { href: "/shorts", label: "Shorts" },
    { href: "/hedge", label: "Hedge" },
    { href: "/backtesting", label: "Backtest" },
    { href: "/portfolios", label: "Portfolio" },
    { href: "/alerts", label: "Alerts" },
    { href: "/learn", label: "Learn" },
    { href: "/showcase", label: "Pro Tools" },
    { href: "/community", label: "Community" },
];

function UserMenu() {
    const { user, logout } = useAuth();
    const [open, setOpen] = useState(false);
    const ref = useRef<HTMLDivElement>(null);

    // Close on outside click
    useEffect(() => {
        function handler(e: MouseEvent) {
            if (ref.current && !ref.current.contains(e.target as Node)) {
                setOpen(false);
            }
        }
        document.addEventListener("mousedown", handler);
        return () => document.removeEventListener("mousedown", handler);
    }, []);

    if (!user) return null;

    const initial = user.email[0].toUpperCase();

    return (
        <div className="relative ml-2" ref={ref}>
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
                    {/* User info */}
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

                    {/* Menu items */}
                    <div className="py-1.5">
                        <Link
                            href="/settings"
                            onClick={() => setOpen(false)}
                            className="flex items-center gap-2.5 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800 hover:text-slate-100 transition-colors"
                        >
                            <Settings className="h-4 w-4 text-slate-400" />
                            Settings
                        </Link>
                        {user.is_admin && (
                            <>
                            <Link
                                href="/admin/ops"
                                onClick={() => setOpen(false)}
                                className="flex items-center gap-2.5 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800 hover:text-slate-100 transition-colors"
                            >
                                <Activity className="h-4 w-4 text-slate-400" />
                                Ops Dashboard
                            </Link>
                            <Link
                                href="/admin/analytics"
                                onClick={() => setOpen(false)}
                                className="flex items-center gap-2.5 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800 hover:text-slate-100 transition-colors"
                            >
                                <BarChart2 className="h-4 w-4 text-indigo-400" />
                                Analytics
                            </Link>
                            <Link
                                href="/admin/experiments"
                                onClick={() => setOpen(false)}
                                className="flex items-center gap-2.5 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800 hover:text-slate-100 transition-colors"
                            >
                                <FlaskConical className="h-4 w-4 text-emerald-400" />
                                Experiments
                                <span className="ml-auto rounded-full bg-emerald-600/20 border border-emerald-500/30 px-1.5 py-0.5 text-[9px] font-bold text-emerald-400">
                                    NEW
                                </span>
                            </Link>
                            </>
                        )}
                        <Link
                            href="/billing"
                            onClick={() => setOpen(false)}
                            className="flex items-center gap-2.5 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800 hover:text-slate-100 transition-colors"
                        >
                            <CreditCard className="h-4 w-4 text-slate-400" />
                            Billing &amp; Plans
                            {!user.is_pro && (
                                <span className="ml-auto rounded-full bg-blue-600/20 border border-blue-500/30 px-1.5 py-0.5 text-[9px] font-bold text-blue-400">
                                    UPGRADE
                                </span>
                            )}
                        </Link>
                    </div>

                    <div className="border-t border-slate-800 py-1.5">
                        <button
                            onClick={() => { logout(); setOpen(false); }}
                            className="flex w-full items-center gap-2.5 px-4 py-2 text-sm text-red-400 hover:bg-red-950/30 hover:text-red-300 transition-colors"
                        >
                            <LogOut className="h-4 w-4" />
                            Sign Out
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}

export function Nav() {
    const pathname = usePathname();

    return (
        <div className="flex items-center gap-1">
            <nav className="flex flex-wrap gap-1 text-sm text-slate-400">
                {NAV_ITEMS.map((item) => {
                    const active = pathname === item.href;
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={`
                                ${item.label === "Learn" ? "tour-learn-tab" : ""}
                                rounded-md px-2.5 py-1 text-xs font-medium transition-colors
                                ${active
                                    ? "bg-slate-800 text-slate-50"
                                    : "text-slate-400 hover:bg-slate-900 hover:text-slate-100"
                                }
                            `}
                        >
                            {item.label}
                        </Link>
                    );
                })}
            </nav>
            <UserMenu />
        </div>
    );
}
