"use client";

import { AlertTriangle } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useState } from "react";
import { X } from "lucide-react";

export function OverfittingWarning() {
    const [visible, setVisible] = useState(true);

    if (!visible) return null;

    return (
        <Alert variant="destructive" className="mb-6 relative">
            <AlertTriangle className="h-5 w-5" />
            <AlertTitle className="text-lg font-semibold tracking-tight">Warning: Overfitting Risk</AlertTitle>
            <AlertDescription className="text-sm leading-relaxed mt-2 opacity-90">
                Backtests use historical data, and tweaking parameters to maximize past performance often leads to <strong>overfitting</strong>.
                A strategy that performs exceptionally well in a backtest is not guaranteed—and is often unlikely—to produce similar results in live trading.
                Always test strategies with out-of-sample data and forward testing.
            </AlertDescription>
            <button
                className="absolute top-4 right-4 opacity-70 hover:opacity-100 transition-opacity"
                onClick={() => setVisible(false)}
                aria-label="Dismiss warning"
            >
                <X className="h-4 w-4" />
            </button>
        </Alert>
    );
}
