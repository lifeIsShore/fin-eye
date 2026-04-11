/**
 * frontend/lib/experiments.ts
 * Sprint 44 — A/B experiment hook.
 * Fetches variant assignments from GET /api/v1/experiments/assignments
 * and exposes a useExperiment(name) hook that returns the assigned variant.
 *
 * Usage:
 *   const variant = useExperiment("onboarding_flow"); // "control" | "goal_selector" | ...
 */

import useSWR from "swr";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export interface ExperimentAssignment {
    experiment_name: string;
    variant: string;
}

interface AssignmentsResponse {
    assignments: ExperimentAssignment[];
}

async function fetchAssignments(): Promise<AssignmentsResponse> {
    const token = typeof window !== "undefined"
        ? (localStorage.getItem("access_token") ?? "")
        : "";
    const res = await fetch(`${API_BASE}/api/v1/experiments/assignments`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) return { assignments: [] };
    return res.json();
}

/**
 * Returns the variant string assigned to this user for the given experiment.
 * Falls back to "control" if the experiment is not found or request fails.
 */
export function useExperiment(experimentName: string): string {
    const { data } = useSWR<AssignmentsResponse>(
        "experiment-assignments",
        fetchAssignments,
        {
            revalidateOnFocus: false,
            dedupingInterval: 60_000, // re-fetch at most once per minute
        },
    );

    if (!data) return "control";
    const match = data.assignments.find((a) => a.experiment_name === experimentName);
    return match?.variant ?? "control";
}
