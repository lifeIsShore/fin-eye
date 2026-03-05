"use client";

import { useAuth } from "@/components/AuthProvider";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import {
    MessageSquare,
    Hash,
    ExternalLink,
    Users,
    BookOpen,
    TrendingUp,
    ShieldAlert,
    Bell,
} from "lucide-react";

// ─── Config — update URLs here when you have real community links ─────────────

const DISCORD_INVITE = "https://discord.gg/fin-eye";           // replace with real invite
const REDDIT_URL     = "https://reddit.com/r/fineye";          // replace with real sub

const DISCORD_CHANNELS = [
    {
        name: "#general",
        description: "Introductions, general discussion, and questions about the platform.",
        icon: Hash,
        color: "text-sky-400",
    },
    {
        name: "#macro-101",
        description: "Discuss macro indicators, Fed policy, yield curves, and regime signals.",
        icon: TrendingUp,
        color: "text-emerald-400",
    },
    {
        name: "#strategy-discussion",
        description: "Share backtesting ideas, compare strategies, and review GAS readings.",
        icon: BookOpen,
        color: "text-violet-400",
    },
    {
        name: "#alerts-and-signals",
        description: "Community-posted GAS threshold alerts and notable regime changes.",
        icon: Bell,
        color: "text-amber-400",
    },
    {
        name: "#risk-and-hedging",
        description: "Collar strategies, protective puts, portfolio construction, and drawdown management.",
        icon: ShieldAlert,
        color: "text-rose-400",
    },
];

const REDDIT_CHANNELS = [
    {
        name: "r/fineye",
        description: "Main community hub for Fin-Eye users — questions, feedback, and market discussion.",
        icon: MessageSquare,
        color: "text-orange-400",
    },
];

const GUIDELINES = [
    "No trading tips or investment recommendations — educational discussion only.",
    "Be constructive. Critique ideas, not people.",
    "No spam, self-promotion, or affiliate links.",
    "Respect the non-advisory nature of Fin-Eye signals.",
    "Clearly label speculative discussion as such.",
];

// ─── Sub-components ───────────────────────────────────────────────────────────

function ChannelCard({
    name,
    description,
    icon: Icon,
    color,
}: {
    name: string;
    description: string;
    icon: React.ElementType;
    color: string;
}) {
    return (
        <div className="flex items-start gap-3 rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-3.5">
            <Icon className={`h-4 w-4 mt-0.5 flex-shrink-0 ${color}`} />
            <div>
                <p className="text-sm font-semibold text-slate-200">{name}</p>
                <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{description}</p>
            </div>
        </div>
    );
}

function PlatformCard({
    title,
    subtitle,
    href,
    icon: Icon,
    iconColor,
    buttonLabel,
    buttonColor,
    children,
}: {
    title: string;
    subtitle: string;
    href: string;
    icon: React.ElementType;
    iconColor: string;
    buttonLabel: string;
    buttonColor: string;
    children: React.ReactNode;
}) {
    return (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/30 p-6 flex flex-col gap-5">
            {/* Header */}
            <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-3">
                    <div className={`flex h-10 w-10 items-center justify-center rounded-xl border ${iconColor} bg-slate-900`}>
                        <Icon className="h-5 w-5" />
                    </div>
                    <div>
                        <h2 className="text-base font-bold text-slate-100">{title}</h2>
                        <p className="text-xs text-slate-500">{subtitle}</p>
                    </div>
                </div>
                <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-semibold text-white transition-colors flex-shrink-0 ${buttonColor}`}
                >
                    {buttonLabel}
                    <ExternalLink className="h-3.5 w-3.5" />
                </a>
            </div>

            {/* Channels */}
            <div className="space-y-2">{children}</div>
        </div>
    );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function CommunityPage() {
    const { user, loading } = useAuth();
    const router = useRouter();

    // Gate: must be logged in
    useEffect(() => {
        if (!loading && !user) {
            router.replace("/auth/login?next=/community");
        }
    }, [user, loading, router]);

    if (loading || !user) {
        return (
            <div className="flex items-center justify-center py-24 text-slate-500 text-sm">
                Loading…
            </div>
        );
    }

    return (
        <div className="space-y-8 max-w-3xl">
            {/* ── Header ─────────────────────────────────────────────────────── */}
            <header className="border-b border-slate-800 pb-6">
                <div className="flex items-center gap-3 mb-2">
                    <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-900/40 border border-indigo-700/30">
                        <Users className="h-5 w-5 text-indigo-400" />
                    </div>
                    <h1 className="text-3xl font-black tracking-tight text-slate-100">
                        Community
                    </h1>
                </div>
                <p className="text-sm text-slate-400 max-w-xl">
                    Connect with other Fin-Eye users to discuss macro regimes, GAS signals,
                    and backtesting ideas. All discussion is educational — not investment advice.
                </p>
            </header>

            {/* ── Platforms ──────────────────────────────────────────────────── */}
            <div className="space-y-5">
                {/* Discord */}
                <PlatformCard
                    title="Discord"
                    subtitle="Real-time chat · structured channels · fastest responses"
                    href={DISCORD_INVITE}
                    icon={MessageSquare}
                    iconColor="border-indigo-700/40 text-indigo-400"
                    buttonLabel="Join Discord"
                    buttonColor="bg-indigo-600 hover:bg-indigo-500"
                >
                    {DISCORD_CHANNELS.map((ch) => (
                        <ChannelCard key={ch.name} {...ch} />
                    ))}
                </PlatformCard>

                {/* Reddit */}
                <PlatformCard
                    title="Reddit"
                    subtitle="Longer-form posts · community questions · public discussion"
                    href={REDDIT_URL}
                    icon={MessageSquare}
                    iconColor="border-orange-700/40 text-orange-400"
                    buttonLabel="Open Reddit"
                    buttonColor="bg-orange-600 hover:bg-orange-500"
                >
                    {REDDIT_CHANNELS.map((ch) => (
                        <ChannelCard key={ch.name} {...ch} />
                    ))}
                </PlatformCard>
            </div>

            {/* ── Community guidelines ────────────────────────────────────────── */}
            <div className="rounded-2xl border border-slate-800 bg-slate-900/30 p-6">
                <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
                    <ShieldAlert className="h-4 w-4 text-amber-400" />
                    Community Guidelines
                </h3>
                <ul className="space-y-2">
                    {GUIDELINES.map((g, i) => (
                        <li key={i} className="flex items-start gap-2.5 text-sm text-slate-400">
                            <span className="mt-1 h-1.5 w-1.5 rounded-full bg-slate-600 flex-shrink-0" />
                            {g}
                        </li>
                    ))}
                </ul>
            </div>

            {/* ── Disclaimer ──────────────────────────────────────────────────── */}
            <p className="text-xs text-slate-600 border-t border-slate-800/50 pt-4">
                Community platforms are moderated independently. Fin-Eye is not responsible
                for content posted by community members. Nothing discussed constitutes
                investment advice. Always conduct your own research.
            </p>
        </div>
    );
}
