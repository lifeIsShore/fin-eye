"use client";
/**
 * components/PageTransition.tsx
 * Sprint 43 — Lightweight CSS-based page transition wrapper.
 * Uses usePathname to key each page, triggering a re-mount + fade-slide animation
 * defined in globals.css (.page-transition-enter). No framer-motion needed.
 */

import { usePathname } from "next/navigation";

export function PageTransition({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();

    return (
        <div key={pathname} className="page-transition-enter">
            {children}
        </div>
    );
}
