"use client";

import { useEffect, useState } from "react";
import Joyride, { CallBackProps, STATUS, Step } from "react-joyride";

export function GuidedTour() {
    const [run, setRun] = useState(false);

    useEffect(() => {
        // Only run the tour if the user hasn't completed it before
        const hasCompleted = localStorage.getItem("hasCompletedTour");
        if (!hasCompleted) {
            setRun(true);
        }

        // Expose a global function to restart the tour manually
        (window as any).restartFinEyeTour = () => {
            setRun(true);
        };
    }, []);

    const steps: Step[] = [
        // ── Core dashboard ──────────────────────────────────────────────────
        {
            target: "body",
            content:
                "Welcome to Fin-Eye! Let's take a quick tour of your financial intelligence dashboard.",
            placement: "center",
            disableBeacon: true,
        },
        {
            target: ".tour-gas-score",
            content:
                "This is the Global Alignment Score (GAS) — your single 0–100 market health metric. It blends Technical (40%), Sentiment (30%), and Macro (30%). Above 60 = bullish alignment.",
            placement: "bottom",
        },
        {
            target: ".tour-regime",
            content:
                "The Regime widget classifies the current market environment as Risk-On, Risk-Off, or Transitional — so you know which playbook applies right now.",
            placement: "bottom",
        },
        {
            target: ".tour-timeframes",
            content:
                "The Technical Consensus grid shows AI-driven ML signals across all trained timeframes (1m to 1wk), each weighted by its Sharpe Ratio so better models count more.",
            placement: "left",
        },
        {
            target: ".tour-why-moving",
            content:
                "The 'Why is it moving?' panel synthesizes all data layers into plain-English bullets — great for quick pre-market prep.",
            placement: "top",
        },

        // ── Watchlist Overview (Sprint 10+) ──────────────────────────────────
        {
            target: ".tour-watchlist",
            content:
                "Your Watchlist sidebar shows live GAS scores and signal grades for all tracked symbols. Click any symbol to switch the active dashboard view instantly.",
            placement: "right",
        },

        // ── Explore (Sprint 13) ──────────────────────────────────────────────
        {
            target: "[href='/explore']",
            content:
                "The Explore page shows a sector heatmap, Relative Rotation Graph, and a Grade Leaderboard — great for scanning the full market at a glance.",
            placement: "right",
        },

        // ── Backtesting (Sprint 14+) ─────────────────────────────────────────
        {
            target: "[href='/backtesting']",
            content:
                "Backtesting lets you test 5 built-in strategies (Trend Follow, Mean Reversion, Macro-Responsive…) with Walk-Forward validation and a full trade log — no guesswork.",
            placement: "right",
        },

        // ── Macro / FOMC (Sprint 21+) ────────────────────────────────────────
        {
            target: "[href='/macro']",
            content:
                "The Macro page tracks Fed Funds Rate, CPI, Unemployment, and the Yield Curve — including an FOMC Countdown so you're never caught off-guard by rate decisions.",
            placement: "right",
        },

        // ── AI Allocator (Sprint 27) ─────────────────────────────────────────
        {
            target: "[href='/portfolio/build']",
            content:
                "The AI Allocator builds a grade-weighted portfolio from your watchlist — A+ stocks get up to 20% allocation, F-rated symbols are excluded. Includes an AI explanation of every suggestion.",
            placement: "right",
        },

        // ── Learn Hub ────────────────────────────────────────────────────────
        {
            target: ".tour-learn-tab",
            content:
                "The Learn Hub has deep-dives on GAS, FinBERT, Kelly Criterion, Walk-Forward validation, and more. The Glossary explains every term — hover any [?] icon on the dashboard to jump straight there.",
            placement: "right",
        },
    ];

    const handleJoyrideCallback = (data: CallBackProps) => {
        const { status } = data;
        if (([STATUS.FINISHED, STATUS.SKIPPED] as string[]).includes(status)) {
            setRun(false);
            localStorage.setItem("hasCompletedTour", "true");
        }
    };

    if (!run) return null;

    return (
        <Joyride
            steps={steps}
            run={run}
            continuous
            scrollToFirstStep
            showProgress
            showSkipButton
            callback={handleJoyrideCallback}
            styles={{
                options: {
                    zIndex: 10000,
                    primaryColor: "#0ea5e9", // sky-500
                    textColor: "#334155",    // slate-700
                    backgroundColor: "#ffffff",
                },
            }}
        />
    );
}
