"use client";

import { useAuth } from "@/components/AuthProvider";
import { User, Lock, Bell, Palette, LogOut, Construction } from "lucide-react";

function ComingSoonBadge() {
    return (
        <span className="ml-2 inline-flex items-center gap-1 rounded-full border border-amber-500/30 bg-amber-950/40 px-2 py-0.5 text-[10px] font-semibold text-amber-400 uppercase tracking-wider">
            <Construction className="h-2.5 w-2.5" />
            Coming Soon
        </span>
    );
}

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
    return (
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
            <h3 className="mb-5 text-sm font-semibold text-slate-200">{title}</h3>
            <div className="space-y-4">{children}</div>
        </div>
    );
}

function FieldRow({ label, value, disabled = true }: { label: string; value?: string; disabled?: boolean }) {
    return (
        <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-400">{label}</label>
            <input
                type="text"
                defaultValue={value ?? ""}
                disabled={disabled}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-400 placeholder-slate-600 disabled:cursor-not-allowed disabled:opacity-60"
                placeholder="—"
            />
        </div>
    );
}

export default function SettingsPage() {
    const { user, logout } = useAuth();

    return (
        <div className="mx-auto max-w-2xl space-y-6">
            <div>
                <h2 className="text-xl font-semibold tracking-tight">Settings</h2>
                <p className="mt-1 text-sm text-slate-400">
                    Manage your profile and preferences.
                </p>
            </div>

            {/* Profile */}
            <SectionCard title="Profile">
                <div className="flex items-center gap-4 mb-4">
                    <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-600 text-white font-semibold text-lg">
                        {user?.email?.[0]?.toUpperCase() ?? "?"}
                    </div>
                    <div>
                        <p className="text-sm font-medium text-slate-200">{user?.email ?? "—"}</p>
                        <span className={`text-xs font-medium ${user?.is_pro ? "text-amber-400" : "text-slate-500"}`}>
                            {user?.is_pro ? "Pro Plan" : "Free Plan"}
                        </span>
                    </div>
                </div>
                <FieldRow label="Display Name" value="" />
                <div className="mt-4">
                    <button
                        disabled
                        className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm text-slate-400 cursor-not-allowed opacity-50"
                    >
                        Save Changes
                        <ComingSoonBadge />
                    </button>
                </div>
            </SectionCard>

            {/* Security */}
            <SectionCard title="Security">
                <FieldRow label="Current Password" />
                <FieldRow label="New Password" />
                <FieldRow label="Confirm New Password" />
                <div className="flex items-center justify-between rounded-lg border border-slate-700 bg-slate-950/50 px-4 py-3">
                    <div className="flex items-center gap-2">
                        <Lock className="h-4 w-4 text-slate-400" />
                        <span className="text-sm text-slate-300">Two-Factor Authentication</span>
                        <ComingSoonBadge />
                    </div>
                    <button
                        disabled
                        className="rounded-md border border-slate-700 bg-slate-800 px-3 py-1 text-xs text-slate-400 cursor-not-allowed opacity-50"
                    >
                        Enable
                    </button>
                </div>
                <div className="mt-2">
                    <button
                        disabled
                        className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm text-slate-400 cursor-not-allowed opacity-50"
                    >
                        Update Password
                        <ComingSoonBadge />
                    </button>
                </div>
            </SectionCard>

            {/* Notifications */}
            <SectionCard title="Notifications">
                {[
                    "GAS threshold alerts",
                    "Regime change alerts",
                    "Weekly market digest email",
                    "Onboarding email sequence",
                ].map((item) => (
                    <div
                        key={item}
                        className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/30 px-4 py-3"
                    >
                        <div className="flex items-center gap-2">
                            <Bell className="h-4 w-4 text-slate-500" />
                            <span className="text-sm text-slate-400">{item}</span>
                            <ComingSoonBadge />
                        </div>
                        <button
                            disabled
                            className="relative inline-flex h-5 w-9 items-center rounded-full bg-slate-700 cursor-not-allowed opacity-50"
                        >
                            <span className="inline-block h-3.5 w-3.5 translate-x-1 rounded-full bg-slate-400 transition-transform" />
                        </button>
                    </div>
                ))}
            </SectionCard>

            {/* Preferences */}
            <SectionCard title="Preferences">
                <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/30 px-4 py-3">
                    <div className="flex items-center gap-2">
                        <Palette className="h-4 w-4 text-slate-500" />
                        <span className="text-sm text-slate-400">Theme</span>
                        <ComingSoonBadge />
                    </div>
                    <span className="text-xs text-slate-500">Dark (default)</span>
                </div>
            </SectionCard>

            {/* Danger zone */}
            <SectionCard title="Account">
                <div className="flex flex-col gap-3 sm:flex-row">
                    <button
                        onClick={logout}
                        className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm text-slate-300 hover:bg-slate-700 transition-colors"
                    >
                        <LogOut className="h-4 w-4" />
                        Sign Out
                    </button>
                    <button
                        disabled
                        className="flex items-center gap-2 rounded-lg border border-red-900/50 bg-red-950/20 px-4 py-2 text-sm text-red-400/60 cursor-not-allowed opacity-50"
                    >
                        Delete Account
                        <ComingSoonBadge />
                    </button>
                </div>
            </SectionCard>
        </div>
    );
}
