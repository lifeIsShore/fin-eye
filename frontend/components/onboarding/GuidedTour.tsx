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

        // Optional: Expose a global function to restart the tour manually
        (window as any).restartFinEyeTour = () => {
            setRun(true);
        };
    }, []);

    const steps: Step[] = [
        {
            target: "body",
            content: "Welcome to Fin-Eye! Let's take a quick tour of your financial intelligence dashboard.",
            placement: "center",
            disableBeacon: true,
        },
        {
            target: ".tour-gas-score",
            content: "This is the Global Alignment Score (GAS). It aggregates Technical, Sentiment, and Macro data into a single 0-100 metric. Higher is better!",
            placement: "bottom",
        },
        {
            target: ".tour-regime",
            content: "Here we identify the current Market Regime (Volatility and Trend) so you know exactly what game the market is playing today.",
            placement: "bottom",
        },
        {
            target: ".tour-timeframes",
            content: "The Technical Consensus grid shows AI-driven momentum predictions ranging from the 1-minute chart up to the 1-week chart.",
            placement: "left",
        },
        {
            target: ".tour-why-moving",
            content: "Don't know why a stock is jumping? The 'Why is it moving?' panel synthesizes all data layers to give you a plain-English explanation.",
            placement: "top",
        },
        {
            target: ".tour-learn-tab",
            content: "Want to master the platform? Check out our Educational Content in the Learn section to read up on Macro, Backtesting, and more! You're all set.",
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
                    textColor: "#334155", // slate-700
                    backgroundColor: "#ffffff",
                },
            }}
        />
    );
}
