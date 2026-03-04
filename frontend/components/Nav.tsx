"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
    { href: "/", label: "Dashboard" },
    { href: "/macro", label: "Macro" },
    { href: "/news-sentiment", label: "News & Sentiment" },
    { href: "/sentiment", label: "Retail Sentiment" },
    { href: "/hedge", label: "Hedge" },
    { href: "/backtesting", label: "Backtesting" },
    { href: "/learn", label: "Learn" },
];

export function Nav() {
    const pathname = usePathname();

    return (
        <nav className="flex gap-3 text-sm text-slate-400">
            {navItems.map((item) => {
                const active = pathname === item.href;
                return (
                    <Link
                        key={item.href}
                        href={item.href}
                        className={`
                            ${item.label === "Learn" ? "tour-learn-tab" : ""}
                            ${active
                                ? "rounded-md bg-slate-800 px-3 py-1 text-slate-50"
                                : "rounded-md px-3 py-1 hover:bg-slate-900 hover:text-slate-100"
                            }
                        `}
                    >
                        {item.label}
                    </Link>
                );
            })}
        </nav>
    );
}
