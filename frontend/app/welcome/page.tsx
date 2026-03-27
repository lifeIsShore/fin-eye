"use client";

/**
 * /app/welcome/page.tsx — todos-v3.md §9 UX-ONBOARD-01
 *
 * Shown once after email confirmation for new users.
 * 3-option goal selector → routes to most relevant feature.
 * Sets has_completed_onboarding in localStorage.
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { BarChart2, Brain, GraduationCap } from "lucide-react";

interface Goal {
    id: string;
    icon: React.ReactNode;
    title: string;
    description: string;
    destination: string;
    color: string;
    accent: string;
}

const GOALS: Goal[] = [
    {
        id: "learn",
        icon: <GraduationCap className="h-8 w-8" />,
        title: "Learn the Basics",
        description: "Understand how GAS scores, momentum signals, and market indicators work.",
        destination: "/learn",
        color: "from-violet-900/40 to-violet-900/10 border-violet-700/40",
        accent: "text-violet-400 bg-violet-900/30",
    },
    {
        id: "timing",
        icon: <BarChart2 className="h-8 w-8" />,
        title: "Improve Trade Timing",
        description: "Use AI-graded signals and backtests to find better entry and exit points.",
        destination: "/backtesting",
        color: "from-sky-900/40 to-sky-900/10 border-sky-700/40",
        accent: "text-sky-400 bg-sky-900/30",
    },
    {
        id: "research",
        icon: <Brain className="h-8 w-8" />,
        title: "Research Stocks",
        description: "Dive into macro context, insider activity, sentiment, and options flow.",
        destination: "/",
        color: "from-emerald-900/40 to-emerald-900/10 border-emerald-700/40",
        accent: "text-emerald-400 bg-emerald-900/30",
    },
];

export default function WelcomePage() {
    const { user } = useAuth();
    const router = useRouter();

    // Redirect if already onboarded
    useEffect(() => {
        const done = localStorage.getItem("has_completed_onboarding");
        if (done === "true") {
            router.replace("/");
        }
    }, [router]);

    const handleSelect = (goal: Goal) => {
        localStorage.setItem("has_completed_onboarding", "true");
        localStorage.setItem("onboarding_goal", goal.id);
        router.push(goal.destination);
    };

    return (
        <main className="min-h-screen bg-slate-950 flex flex-col items-center justify-center px-4 py-16">
            {/* Logo mark */}
            <div className="mb-8 flex flex-col items-center gap-2">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-sky-600 shadow-lg shadow-sky-900/40">
                    <BarChart2 className="h-6 w-6 text-white" />
                </div>
                <h1 className="text-2xl font-bold text-slate-100">
                    Welcome to Fin-Eye
                </h1>
                <p className="text-sm text-slate-400 max-w-xs text-center">
                    {user
                        ? `Good to have you, ${user.email.split("@")[0]}. Tell us what you're here to do.`
                        : "Tell us what you're here to do."}
                </p>
            </div>

            {/* Goal cards */}
            <div className="grid w-full max-w-2xl gap-4 sm:grid-cols-3">
                {GOALS.map((goal) => (
                    <button
                        key={goal.id}
                        onClick={() => handleSelect(goal)}
                        className={`group relative flex flex-col items-start gap-4 rounded-2xl border bg-gradient-to-b ${goal.color} p-6 text-left transition-all duration-200 hover:scale-[1.02] hover:shadow-xl hover:shadow-slate-900/60 focus:outline-none focus:ring-2 focus:ring-sky-500`}
                    >
                        <span className={`rounded-xl p-2 ${goal.accent}`}>
                            {goal.icon}
                        </span>
                        <div>
                            <h2 className="text-sm font-semibold text-slate-100 mb-1">
                                {goal.title}
                            </h2>
                            <p className="text-xs text-slate-400 leading-relaxed">
                                {goal.description}
                            </p>
                        </div>
                        <span className="mt-auto text-[11px] font-medium text-slate-500 group-hover:text-slate-300 transition-colors">
                            Get started →
                        </span>
                    </button>
                ))}
            </div>

            {/* Skip link */}
            <button
                onClick={() => {
                    localStorage.setItem("has_completed_onboarding", "true");
                    router.push("/");
                }}
                className="mt-8 text-xs text-slate-600 hover:text-slate-400 transition-colors"
            >
                Skip for now → go to Dashboard
            </button>
        </main>
    );
}
