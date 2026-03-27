"use client";

/**
 * ProGate.tsx — todos-v3.md §10 UX-MONETISE-01
 *
 * Reusable Pro-gate wrapper component.
 * Renders a 🔒 overlay with upgrade tooltip on any Pro-only feature.
 * Clicking opens the /billing page.
 *
 * Usage:
 *   <ProGate feature="Walk-Forward Analysis">
 *     <WalkForwardPanel />
 *   </ProGate>
 *
 * Props:
 *   feature     — human-readable feature name shown in the tooltip
 *   children    — the Pro-only content to render (shown blurred when locked)
 *   minHeight   — optional min-height for the locked placeholder (default 200px)
 */

import { useAuth } from "@/components/AuthProvider";
import { useRouter } from "next/navigation";
import { Lock, Zap } from "lucide-react";
import { useMemo } from "react";

interface ProGateProps {
    feature?: string;
    children: React.ReactNode;
    minHeight?: number;
}

export default function ProGate({ feature = "This feature", children, minHeight = 200 }: ProGateProps) {
    const { user } = useAuth();
    const router = useRouter();

    // Determine whether the user has Pro access (paid OR active trial)
    const hasProAccess = useMemo(() => {
        if (!user) return false;
        if (user.is_pro) return true;

        // Active trial
        const trialEnd = (user as any).trial_ends_at as string | null | undefined;
        if (trialEnd) {
            return new Date(trialEnd) > new Date();
        }
        return false;
    }, [user]);

    // Just render children for Pro/trial users
    if (hasProAccess) return <>{children}</>;

    return (
        <div className="relative overflow-hidden rounded-xl" style={{ minHeight }}>
            {/* Blurred content behind the gate */}
            <div className="pointer-events-none select-none blur-sm opacity-40 scale-[0.98]">
                {children}
            </div>

            {/* Lock overlay */}
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-slate-950/70 backdrop-blur-[2px]">
                <div className="flex flex-col items-center gap-3 text-center px-6">
                    <div className="flex h-12 w-12 items-center justify-center rounded-full border border-slate-700 bg-slate-900 shadow-lg">
                        <Lock className="h-5 w-5 text-slate-400" />
                    </div>
                    <div>
                        <p className="text-sm font-semibold text-slate-200">
                            {feature} is a Pro feature
                        </p>
                        <p className="mt-0.5 text-xs text-slate-500">
                            Upgrade for €14.99/mo — or start a free 7-day trial
                        </p>
                    </div>
                    <button
                        onClick={() => router.push("/billing")}
                        className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-md hover:bg-blue-500 transition-colors"
                    >
                        <Zap className="h-3.5 w-3.5" />
                        View Pro Plans
                    </button>
                </div>
            </div>
        </div>
    );
}
