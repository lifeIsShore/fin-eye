"use client";

/**
 * hooks/useExperiment.ts
 *
 * React hook for A/B experiment variant resolution (CORE-EXPERIMENT-01).
 *
 * Usage in any page/component:
 *
 *   const variant = useExperiment("onboarding_flow_v2");
 *
 *   if (variant.variant === "treatment") {
 *     return <NewOnboardingFlow />;
 *   }
 *   return <OriginalOnboardingFlow />;
 *
 * Behaviour:
 *   - Calls GET /api/v1/experiments/{key}/assign on first render.
 *   - Caches the result in module-level memory so subsequent renders
 *     (and other components using the same key) are instant — no extra
 *     network calls.
 *   - Returns "control" immediately while loading (safe default, no flash).
 *   - Silently falls back to "control" on any network/API error — experiments
 *     must never break the UI.
 *
 * Anonymous users:
 *   - A stable anon_id is generated from a random UUID stored in sessionStorage.
 *   - This provides consistent assignment within a browser session for
 *     pre-login users.
 */

import { useEffect, useState, useRef } from "react";
import { assignVariant, type AssignmentDto } from "@/lib/api";

// Module-level cache: experimentKey → AssignmentDto
const _assignmentCache = new Map<string, AssignmentDto>();

// Stable anon_id for the browser session
function getAnonId(): string {
  if (typeof window === "undefined") return "";
  const KEY = "fin_eye_anon_id";
  let id = sessionStorage.getItem(KEY);
  if (!id) {
    id =
      typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID()
        : Math.random().toString(36).slice(2) + Date.now().toString(36);
    sessionStorage.setItem(KEY, id);
  }
  return id;
}

export type ExperimentState = {
  /** Assigned variant key. Defaults to "control" while loading. */
  variant: string;
  /** Human-readable variant name */
  variantName: string;
  /** True while the assignment request is in-flight */
  loading: boolean;
  /** True if the user is inside the experiment's traffic slice */
  inTraffic: boolean;
  /**
   * Attach experiment context to analytics event properties.
   *
   * Example:
   *   track(AnalyticsEvent.BACKTEST_RUN, {
   *     properties: { ...exp.withExperiment(), symbol: "AAPL" },
   *   });
   */
  withExperiment: () => Record<string, string>;
};

export function useExperiment(experimentKey: string): ExperimentState {
  const cached = _assignmentCache.get(experimentKey);
  const [assignment, setAssignment] = useState<AssignmentDto | null>(cached ?? null);
  const [loading, setLoading] = useState(!cached);
  const fetchedRef = useRef(false);

  useEffect(() => {
    if (cached || fetchedRef.current) return;
    fetchedRef.current = true;

    const anonId = getAnonId();
    assignVariant(experimentKey, anonId)
      .then((result) => {
        _assignmentCache.set(experimentKey, result);
        setAssignment(result);
      })
      .catch(() => {
        const fallback: AssignmentDto = {
          experiment_key: experimentKey,
          experiment_id: 0,
          variant_key: "control",
          variant_name: "Control",
          in_traffic: false,
          assigned_at: new Date().toISOString(),
        };
        _assignmentCache.set(experimentKey, fallback);
        setAssignment(fallback);
      })
      .finally(() => setLoading(false));
  }, [experimentKey, cached]);

  const variant = assignment?.variant_key ?? "control";
  const variantName = assignment?.variant_name ?? "Control";
  const inTraffic = assignment?.in_traffic ?? false;

  const withExperiment = () => ({
    experiment_key: experimentKey,
    experiment_variant: variant,
  });

  return { variant, variantName, loading, inTraffic, withExperiment };
}

/**
 * Convenience: returns true if current user is in the specified variant.
 *
 *   const isTreatment = useVariant("onboarding_flow_v2", "treatment");
 */
export function useVariant(experimentKey: string, variantKey: string): boolean {
  const { variant, loading } = useExperiment(experimentKey);
  return !loading && variant === variantKey;
}
