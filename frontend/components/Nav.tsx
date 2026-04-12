"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import { useRef } from "react";
import { useAuth } from "@/components/AuthProvider";
import {
    Settings, CreditCard, LogOut, ChevronDown, User,
    Activity, BarChart2, FlaskConical, Menu, X, Zap,
    LayoutDashboard, Globe, Newspaper, Users,
    TrendingDown, Calendar, PieChart, Landmark, BarChart,
    Shield, FlaskConical as Backtest, Briefcase, Bell,
    ShoppingBag, BookOpen, MessageCircle, Eye, ChevronLeft,
    ChevronRight, LayoutList,
} from "lucide-react";

// ── Sidebar nav structure ─────────────────────────────────────────────────────

interface NavSection {
    title: string;
    items: NavItem[];
}

// Sprint 30 — per-item badges for feature discovery
type NavBadge = "NEW" | "BETA" | "AI";

interface NavItem {
    href: string;
    label: string;
    icon: React.ReactNode;
    badge?: NavBadge;
}

const BADGE_STYLES: Record<NavBadge, string> = {
    NEW:  "bg-emerald-600/80 text-emerald-100 border-emerald-500/40",
    BETA: "bg-amber-600/80  text-amber-100  border-amber-500/40",
    AI:   "bg-violet-600/80 text-violet-100 border-violet-500/40",
};

const SIDEBAR_SECTIONS: NavSection[] = [
    {
        title: "Core Analysis",
        items: [
            { href: "/", label: "Dashboard", icon: <LayoutDashboard className="h-4 w-4" /> },
            { href: "/macro", label: "Macro", icon: <Globe className="h-4 w-4" /> },
            { href: "/news-sentiment", label: "Sentiment", icon: <Newspaper className="h-4 w-4" /> },
        ],
    },
    {
        title: "Deep Signals",
        items: [
            { href: "/sentiment", label: "Retail Mood", icon: <Users className="h-4 w-4" /> },
            { href: "/sentiment-adv", label: "Adv. Sentiment", icon: <Zap className="h-4 w-4" />, badge: "NEW" },
            { href: "/options", label: "Options Flow", icon: <Activity className="h-4 w-4" /> },
            { href: "/insiders", label: "Insider Activity", icon: <Eye className="h-4 w-4" /> },
            { href: "/shorts", label: "Short Interest", icon: <TrendingDown className="h-4 w-4" /> },
            { href: "/earnings", label: "Earnings", icon: <Calendar className="h-4 w-4" /> },
        ],
    },
    {
        title: "Market Context",
        items: [
            { href: "/explore", label: "Explorer", icon: <Zap className="h-4 w-4" /> },
            { href: "/sectors", label: "Sectors", icon: <PieChart className="h-4 w-4" /> },
            { href: "/fed-policy", label: "Fed Policy", icon: <Landmark className="h-4 w-4" />, badge: "NEW" },
            { href: "/indicators", label: "Indicators", icon: <BarChart className="h-4 w-4" />, badge: "BETA" },
            { href: "/hedge", label: "Hedge", icon: <Shield className="h-4 w-4" /> },
        ],
    },
    {
        title: "Tools",
        items: [
            { href: "/watchlist-overview", label: "Watchlist Overview", icon: <LayoutList className="h-4 w-4" /> },
            { href: "/backtesting", label: "Backtesting", icon: <Backtest className="h-4 w-4" /> },
            { href: "/portfolios", label: "Portfolio", icon: <Briefcase className="h-4 w-4" /> },
            { href: "/portfolio/allocate", label: "Allocation Suggest", icon: <PieChart className="h-4 w-4" />, badge: "NEW" },
            { href: "/portfolio/retirement", label: "Retirement Risk", icon: <TrendingDown className="h-4 w-4" />, badge: "NEW" },
            { href: "/portfolio/build", label: "AI Allocator", icon: <Zap className="h-4 w-4" />, badge: "AI" },
            { href: "/alerts", label: "Alerts", icon: <Bell className="h-4 w-4" /> },
            { href: "/showcase", label: "Pro Tools", icon: <ShoppingBag className="h-4 w-4" /> },
        ],
    },
    {
        title: "Learn",
        items: [
            { href: "/learn", label: "Learn Hub", icon: <BookOpen className="h-4 w-4" /> },
            { href: "/learn/glossary", label: "Glossary", icon: <BookOpen className="h-4 w-4" />, badge: "NEW" as NavBadge },
            { href: "/lifestyle", label: "Lifestyle Finance", icon: <Globe className="h-4 w-4" />, badge: "NEW" as NavBadge },
            { href: "/community", label: "Community", icon: <MessageCircle className="h-4 w-4" /> },
        ],
    },
];

// Flat list for mobile drawer
const ALL_NAV_FLAT = SIDEBAR_SECTIONS.flatMap((s) => s.items);

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
                            <Link href="/admin/gas" onClick={() => setOpen(false)}
                                className="flex items-center gap-2.5 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800 hover:text-slate-100 transition-colors">
                                <Zap className="h-4 w-4 text-sky-400" /> GAS Precompute
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

// ── Desktop Sidebar ───────────────────────────────────────────────────────────

export function Sidebar() {
    const pathname = usePathname();
    const [collapsed, setCollapsed] = useState(false);

    // Persist collapse state
    useEffect(() => {
        const stored = localStorage.getItem("fin-eye-sidebar-collapsed");
        if (stored === "true") setCollapsed(true);
    }, []);

    const toggleCollapse = () => {
        setCollapsed((c) => {
            localStorage.setItem("fin-eye-sidebar-collapsed", String(!c));
            return !c;
        });
    };

    return (
        <aside
            className={`hidden lg:flex flex-col flex-shrink-0 border-r border-slate-800 bg-slate-950 transition-all duration-300 ${collapsed ? "w-14" : "w-56"
                }`}
            style={{ minHeight: "100vh" }}
        >
            {/* Logo area */}
            <div className={`flex items-center border-b border-slate-800 px-3 py-4 ${collapsed ? "justify-center" : "justify-between"}`}>
                {!collapsed && (
                    <Link href="/" className="flex flex-col">
                        <span className="text-base font-bold text-slate-100 leading-tight hover:text-white transition-colors">
                            Fin-Eye
                        </span>
                        <span className="text-[10px] text-slate-500 leading-tight">Market Intelligence</span>
                    </Link>
                )}
                <button
                    onClick={toggleCollapse}
                    className="rounded-md p-1 text-slate-500 hover:bg-slate-800 hover:text-slate-300 transition-colors flex-shrink-0"
                    title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
                >
                    {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
                </button>
            </div>

            {/* Nav sections */}
            <nav className="flex-1 overflow-y-auto py-3 space-y-4 px-2">
                {SIDEBAR_SECTIONS.map((section) => (
                    <div key={section.title}>
                        {/* Section header — hidden when collapsed */}
                        {!collapsed && (
                            <p className="px-2 pb-1 text-[10px] font-semibold tracking-widest text-slate-600 uppercase">
                                {section.title}
                            </p>
                        )}
                        {collapsed && <div className="border-t border-slate-800/60 mx-1 mb-1" />}

                        <ul className="space-y-0.5">
                            {section.items.map((item) => {
                                const active = pathname === item.href;
                                return (
                                    <li key={item.href}>
                                        <Link
                                        href={item.href}
                                        title={collapsed ? item.label : undefined}
                                        className={`flex items-center gap-2.5 rounded-lg px-2 py-2 text-sm font-medium transition-colors ${active
                                        ? "bg-slate-800 text-sky-400 border-l-2 border-sky-500"
                                        : "text-slate-400 hover:bg-slate-900 hover:text-slate-100 border-l-2 border-transparent"
                                        } ${collapsed ? "justify-center px-0" : ""}`}
                                        >
                                        <span className={`flex-shrink-0 ${active ? "text-sky-400" : "text-slate-500"}`}>
                                        {item.icon}
                                        </span>
                                        {!collapsed && (
                                                <span className="flex items-center gap-1.5 min-w-0 flex-1">
                                    <span className="truncate">{item.label}</span>
                                    {item.badge && (
                                        <span className={`flex-shrink-0 rounded-full border px-1.5 py-px text-[8px] font-bold leading-none ${BADGE_STYLES[item.badge]}`}>
                                            {item.badge}
                                        </span>
                                    )}
                                </span>
                            )}
                        </Link>
                                    </li>
                                );
                            })}
                        </ul>
                    </div>
                ))}
            </nav>

            {/* Sidebar footer — Settings */}
            <div className={`border-t border-slate-800 py-3 px-2`}>
                <Link
                    href="/settings"
                    title={collapsed ? "Settings" : undefined}
                    className={`flex items-center gap-2.5 rounded-lg px-2 py-2 text-sm font-medium text-slate-400 hover:bg-slate-900 hover:text-slate-100 transition-colors ${collapsed ? "justify-center px-0" : ""
                        }`}
                >
                    <Settings className="h-4 w-4 flex-shrink-0 text-slate-500" />
                    {!collapsed && <span>Settings</span>}
                </Link>
            </div>
        </aside>
    );
}

// ── Mobile Drawer Nav ─────────────────────────────────────────────────────────

export function MobileNav() {
    const pathname = usePathname();
    const [open, setOpen] = useState(false);

    useEffect(() => { setOpen(false); }, [pathname]);

    return (
        <>
            <button
                onClick={() => setOpen(true)}
                className="lg:hidden flex items-center justify-center rounded-lg border border-slate-700 bg-slate-900 p-2 text-slate-300 hover:text-slate-100 transition-colors"
                aria-label="Open menu"
            >
                <Menu className="h-5 w-5" />
            </button>

            {open && (
                <div className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
                    onClick={() => setOpen(false)} />
            )}

            <div className={`fixed top-0 left-0 z-50 h-full w-72 bg-slate-950 border-r border-slate-800 flex flex-col transition-transform duration-300 lg:hidden ${open ? "translate-x-0" : "-translate-x-full"
                }`}>
                <div className="flex items-center justify-between px-4 py-4 border-b border-slate-800">
                    <div>
                        <span className="text-base font-bold text-slate-100">Fin-Eye</span>
                        <p className="text-[10px] text-slate-500">Market Intelligence</p>
                    </div>
                    <button onClick={() => setOpen(false)}
                        className="rounded-lg p-1.5 text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors">
                        <X className="h-5 w-5" />
                    </button>
                </div>

                <nav className="flex-1 overflow-y-auto py-3 px-2">
                    {SIDEBAR_SECTIONS.map((section) => (
                        <div key={section.title} className="mb-4">
                            <p className="px-3 pb-1 text-[10px] font-semibold tracking-widest text-slate-600 uppercase">
                                {section.title}
                            </p>
                            <ul className="space-y-0.5">
                                {section.items.map((item) => {
                                    const active = pathname === item.href;
                                    return (
                                        <li key={item.href}>
                                            <Link href={item.href}
                                            className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${active ? "bg-slate-800 text-sky-400" : "text-slate-300 hover:bg-slate-800/60 hover:text-slate-100"
                                            }`}>
                                            <span className={active ? "text-sky-400" : "text-slate-500"}>
                                            {item.icon}
                                            </span>
                                            <span className="flex items-center gap-1.5 flex-1">
                                                    {item.label}
                                    {item.badge && (
                                        <span className={`rounded-full border px-1.5 py-px text-[8px] font-bold leading-none ${BADGE_STYLES[item.badge]}`}>
                                            {item.badge}
                                        </span>
                                    )}
                                </span>
                            </Link>
                                        </li>
                                    );
                                })}
                            </ul>
                        </div>
                    ))}
                </nav>

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

// Nav export kept for backward compat — no longer used in layout but safe to keep
export function Nav() { return null; }