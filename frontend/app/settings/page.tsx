"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/components/AuthProvider";
import {
    User, Lock, Bell, Palette, LogOut, Construction,
    Download, Trash2, AlertTriangle, Loader2, CheckCircle2, X, Eye, EyeOff,
    ShieldCheck, ShieldOff, QrCode, KeyRound,
} from "lucide-react";
import {
    downloadDataExport, deleteAccount, updateProfile, changePassword,
    setup2fa, enable2fa, disable2fa, get2faStatus,
    type TotpSetupDto,
} from "@/lib/api";

// ─── Shared sub-components ───────────────────────────────────────────────────

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

function StatusMessage({ type, message }: { type: "success" | "error"; message: string }) {
    return (
        <div
            className={`flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium ${
                type === "success"
                    ? "border border-emerald-800/40 bg-emerald-950/30 text-emerald-400"
                    : "border border-red-800/40 bg-red-950/30 text-red-400"
            }`}
        >
            {type === "success" ? (
                <CheckCircle2 className="h-3.5 w-3.5 flex-shrink-0" />
            ) : (
                <X className="h-3.5 w-3.5 flex-shrink-0" />
            )}
            {message}
        </div>
    );
}

// ─── Delete Account modal ────────────────────────────────────────────────────

function DeleteAccountModal({
    onClose,
    onConfirm,
    loading,
    error,
}: {
    onClose: () => void;
    onConfirm: () => void;
    loading: boolean;
    error: string | null;
}) {
    const [typed, setTyped] = useState("");
    const PHRASE = "DELETE MY ACCOUNT";

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm px-4">
            <div className="w-full max-w-md rounded-2xl border border-red-900/50 bg-slate-900 shadow-2xl">
                <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
                    <div className="flex items-center gap-3">
                        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-red-950/50 border border-red-900/40">
                            <AlertTriangle className="h-4 w-4 text-red-400" />
                        </div>
                        <h2 className="text-base font-semibold text-slate-50">Delete Account</h2>
                    </div>
                    <button onClick={onClose} className="text-slate-500 hover:text-slate-300 transition-colors">
                        <X className="h-4 w-4" />
                    </button>
                </div>

                <div className="px-6 py-5 space-y-4">
                    <div className="rounded-lg border border-red-900/30 bg-red-950/10 p-4 text-sm text-red-300/90 space-y-1">
                        <p className="font-semibold">This action is permanent and cannot be undone.</p>
                        <ul className="mt-2 list-disc pl-4 space-y-1 text-red-300/70 text-xs">
                            <li>Your email and password will be irreversibly anonymised.</li>
                            <li>Your watchlist and portfolios will be deleted.</li>
                            <li>Legal consent records are retained as required by law.</li>
                            <li>You will be immediately logged out.</li>
                        </ul>
                    </div>

                    <div>
                        <label className="mb-2 block text-xs font-medium text-slate-400">
                            Type <span className="font-mono text-red-400">{PHRASE}</span> to confirm
                        </label>
                        <input
                            type="text"
                            value={typed}
                            onChange={(e) => setTyped(e.target.value)}
                            placeholder={PHRASE}
                            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:border-red-500 focus:outline-none focus:ring-1 focus:ring-red-500"
                        />
                    </div>

                    {error && <p className="text-xs text-red-400">{error}</p>}
                </div>

                <div className="border-t border-slate-800 px-6 py-4 flex justify-end gap-3">
                    <button
                        onClick={onClose}
                        disabled={loading}
                        className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm text-slate-300 hover:bg-slate-700 disabled:opacity-50 transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={onConfirm}
                        disabled={typed !== PHRASE || loading}
                        className="flex items-center gap-2 rounded-lg bg-red-700 px-4 py-2 text-sm font-semibold text-white hover:bg-red-600 disabled:cursor-not-allowed disabled:opacity-40 transition-colors"
                    >
                        {loading ? (
                            <><Loader2 className="h-4 w-4 animate-spin" /> Deleting…</>
                        ) : (
                            <><Trash2 className="h-4 w-4" /> Delete My Account</>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}

// ─── Password field with show/hide toggle ────────────────────────────────────

function PasswordField({
    label,
    value,
    onChange,
    placeholder,
}: {
    label: string;
    value: string;
    onChange: (v: string) => void;
    placeholder?: string;
}) {
    const [show, setShow] = useState(false);
    return (
        <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-400">{label}</label>
            <div className="relative">
                <input
                    type={show ? "text" : "password"}
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    placeholder={placeholder ?? "••••••••"}
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 pr-10 text-sm text-slate-200 placeholder-slate-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
                <button
                    type="button"
                    onClick={() => setShow((s) => !s)}
                    className="absolute inset-y-0 right-0 flex items-center px-3 text-slate-500 hover:text-slate-300 transition-colors"
                >
                    {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
            </div>
        </div>
    );
}

// ─── Two-Factor Authentication section ─────────────────────────────────────

type TwoFaStep = "idle" | "setup-qr" | "setup-confirm" | "disable-confirm";

function TwoFactorSection() {
    const [enabled, setEnabled] = useState<boolean | null>(null);
    const [step, setStep] = useState<TwoFaStep>("idle");
    const [setupData, setSetupData] = useState<TotpSetupDto | null>(null);
    const [code, setCode] = useState("");
    const [loading, setLoading] = useState(false);
    const [status, setStatus] = useState<{ type: "success" | "error"; message: string } | null>(null);
    const [showSecret, setShowSecret] = useState(false);

    useEffect(() => {
        get2faStatus().then((s) => setEnabled(s.totp_enabled)).catch(() => setEnabled(false));
    }, []);

    const startSetup = async () => {
        setLoading(true);
        setStatus(null);
        try {
            const data = await setup2fa();
            setSetupData(data);
            setStep("setup-qr");
        } catch (e) {
            setStatus({ type: "error", message: e instanceof Error ? e.message : "Failed to start setup." });
        } finally {
            setLoading(false);
        }
    };

    const confirmEnable = async () => {
        if (code.length !== 6) return;
        setLoading(true);
        setStatus(null);
        try {
            await enable2fa(code);
            setEnabled(true);
            setStep("idle");
            setSetupData(null);
            setCode("");
            setStatus({ type: "success", message: "Two-factor authentication is now active." });
        } catch (e) {
            setStatus({ type: "error", message: e instanceof Error ? e.message : "Invalid code." });
            setCode("");
        } finally {
            setLoading(false);
        }
    };

    const confirmDisable = async () => {
        if (code.length !== 6) return;
        setLoading(true);
        setStatus(null);
        try {
            await disable2fa(code);
            setEnabled(false);
            setStep("idle");
            setCode("");
            setStatus({ type: "success", message: "Two-factor authentication has been disabled." });
        } catch (e) {
            setStatus({ type: "error", message: e instanceof Error ? e.message : "Invalid code." });
            setCode("");
        } finally {
            setLoading(false);
        }
    };

    const cancel = () => { setStep("idle"); setCode(""); setSetupData(null); setStatus(null); setShowSecret(false); };

    // QR code via Google Charts API (no npm dep)
    const qrUrl = setupData
        ? `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(setupData.uri)}`
        : null;

    return (
        <div className="rounded-lg border border-slate-700 bg-slate-950/50 overflow-hidden">
            {/* Header row */}
            <div className="flex items-center justify-between px-4 py-3">
                <div className="flex items-center gap-2.5">
                    {enabled ? (
                        <ShieldCheck className="h-4 w-4 text-emerald-400" />
                    ) : (
                        <Lock className="h-4 w-4 text-slate-400" />
                    )}
                    <span className="text-sm text-slate-300">Two-Factor Authentication</span>
                    {enabled === null ? null : enabled ? (
                        <span className="rounded-full bg-emerald-900/40 border border-emerald-700/40 px-2 py-0.5 text-[10px] font-bold text-emerald-400 uppercase tracking-wider">On</span>
                    ) : (
                        <span className="rounded-full bg-slate-800 border border-slate-700 px-2 py-0.5 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Off</span>
                    )}
                </div>
                {step === "idle" && (
                    enabled ? (
                        <button
                            onClick={() => setStep("disable-confirm")}
                            className="rounded-md border border-red-800/50 bg-red-950/30 px-3 py-1 text-xs font-medium text-red-400 hover:bg-red-900/40 transition-colors"
                        >
                            Disable
                        </button>
                    ) : (
                        <button
                            onClick={startSetup}
                            disabled={loading || enabled === null}
                            className="rounded-md border border-indigo-700/50 bg-indigo-900/30 px-3 py-1 text-xs font-medium text-indigo-400 hover:bg-indigo-900/50 disabled:opacity-40 transition-colors"
                        >
                            {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Enable"}
                        </button>
                    )
                )}
            </div>

            {/* QR code step */}
            {step === "setup-qr" && qrUrl && (
                <div className="border-t border-slate-800 px-4 py-5 space-y-4">
                    <p className="text-xs text-slate-400">
                        Scan this QR code with <span className="text-slate-300 font-medium">Google Authenticator</span>, <span className="text-slate-300 font-medium">Authy</span>, or <span className="text-slate-300 font-medium">1Password</span>.
                    </p>
                    <div className="flex justify-center">
                        <div className="rounded-xl bg-white p-3 shadow-lg">
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img src={qrUrl} alt="TOTP QR Code" width={180} height={180} />
                        </div>
                    </div>
                    <div>
                        <button
                            onClick={() => setShowSecret((s) => !s)}
                            className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
                        >
                            <KeyRound className="h-3.5 w-3.5" />
                            {showSecret ? "Hide" : "Can't scan? Show"} manual entry key
                        </button>
                        {showSecret && (
                            <div className="mt-2 rounded-lg bg-slate-900 border border-slate-700 px-3 py-2">
                                <p className="text-xs text-slate-500 mb-1">Enter this key manually in your app:</p>
                                <p className="font-mono text-sm text-slate-200 break-all select-all">{setupData?.secret}</p>
                            </div>
                        )}
                    </div>
                    <button
                        onClick={() => setStep("setup-confirm")}
                        className="w-full rounded-lg bg-indigo-600 hover:bg-indigo-500 px-4 py-2 text-sm font-semibold text-white transition-colors"
                    >
                        I've scanned it — next
                    </button>
                    <button onClick={cancel} className="w-full text-xs text-slate-500 hover:text-slate-300">Cancel</button>
                </div>
            )}

            {/* Confirm step (enable) */}
            {step === "setup-confirm" && (
                <div className="border-t border-slate-800 px-4 py-5 space-y-4">
                    <p className="text-xs text-slate-400">
                        Enter the 6-digit code from your authenticator app to confirm setup.
                    </p>
                    <input
                        type="text"
                        inputMode="numeric"
                        maxLength={6}
                        value={code}
                        onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                        placeholder="000000"
                        className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-2 text-center text-xl font-mono tracking-[0.4em] text-slate-50 placeholder-slate-600 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                    />
                    {status && <StatusMessage type={status.type} message={status.message} />}
                    <div className="flex gap-3">
                        <button onClick={cancel} className="flex-1 rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm text-slate-400 hover:bg-slate-700 transition-colors">Cancel</button>
                        <button
                            onClick={confirmEnable}
                            disabled={loading || code.length !== 6}
                            className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-emerald-700 hover:bg-emerald-600 disabled:opacity-40 px-4 py-2 text-sm font-semibold text-white transition-colors"
                        >
                            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
                            Activate 2FA
                        </button>
                    </div>
                </div>
            )}

            {/* Confirm step (disable) */}
            {step === "disable-confirm" && (
                <div className="border-t border-slate-800 px-4 py-5 space-y-4">
                    <div className="rounded-lg border border-red-900/30 bg-red-950/10 p-3 text-xs text-red-300/80">
                        Enter a valid code from your authenticator app to disable 2FA. This will make your account less secure.
                    </div>
                    <input
                        type="text"
                        inputMode="numeric"
                        maxLength={6}
                        value={code}
                        onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                        placeholder="000000"
                        className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-2 text-center text-xl font-mono tracking-[0.4em] text-slate-50 placeholder-slate-600 focus:border-red-500 focus:outline-none focus:ring-1 focus:ring-red-500"
                    />
                    {status && <StatusMessage type={status.type} message={status.message} />}
                    <div className="flex gap-3">
                        <button onClick={cancel} className="flex-1 rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm text-slate-400 hover:bg-slate-700 transition-colors">Cancel</button>
                        <button
                            onClick={confirmDisable}
                            disabled={loading || code.length !== 6}
                            className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-red-700 hover:bg-red-600 disabled:opacity-40 px-4 py-2 text-sm font-semibold text-white transition-colors"
                        >
                            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldOff className="h-4 w-4" />}
                            Disable 2FA
                        </button>
                    </div>
                </div>
            )}

            {/* Success/error feedback at idle */}
            {step === "idle" && status && (
                <div className="border-t border-slate-800 px-4 py-3">
                    <StatusMessage type={status.type} message={status.message} />
                </div>
            )}
        </div>
    );
}

// ─── Main page ───────────────────────────────────────────────────────────────

export default function SettingsPage() {
    const { user, logout, updateUser } = useAuth();

    // ── Profile state ──────────────────────────────────────────────────────
    const [displayName, setDisplayName] = useState(user?.name ?? "");
    const [profileLoading, setProfileLoading] = useState(false);
    const [profileStatus, setProfileStatus] = useState<{ type: "success" | "error"; message: string } | null>(null);

    const handleSaveProfile = async () => {
        setProfileLoading(true);
        setProfileStatus(null);
        try {
            const updated = await updateProfile(displayName.trim());
            updateUser({ name: updated.name });
            setProfileStatus({ type: "success", message: "Display name saved." });
        } catch (err: unknown) {
            setProfileStatus({ type: "error", message: err instanceof Error ? err.message : "Save failed." });
        } finally {
            setProfileLoading(false);
            setTimeout(() => setProfileStatus(null), 4000);
        }
    };

    // ── Security state ─────────────────────────────────────────────────────
    const [currentPw, setCurrentPw] = useState("");
    const [newPw, setNewPw] = useState("");
    const [confirmPw, setConfirmPw] = useState("");
    const [pwLoading, setPwLoading] = useState(false);
    const [pwStatus, setPwStatus] = useState<{ type: "success" | "error"; message: string } | null>(null);

    const handleChangePassword = async () => {
        if (newPw !== confirmPw) {
            setPwStatus({ type: "error", message: "New passwords don't match." });
            return;
        }
        if (newPw.length < 8) {
            setPwStatus({ type: "error", message: "New password must be at least 8 characters." });
            return;
        }
        setPwLoading(true);
        setPwStatus(null);
        try {
            await changePassword(currentPw, newPw);
            setCurrentPw("");
            setNewPw("");
            setConfirmPw("");
            setPwStatus({ type: "success", message: "Password updated successfully." });
        } catch (err: unknown) {
            setPwStatus({ type: "error", message: err instanceof Error ? err.message : "Password change failed." });
        } finally {
            setPwLoading(false);
            setTimeout(() => setPwStatus(null), 5000);
        }
    };

    // ── Data export state ──────────────────────────────────────────────────
    const [exportLoading, setExportLoading] = useState(false);
    const [exportDone, setExportDone] = useState(false);
    const [exportError, setExportError] = useState<string | null>(null);

    const handleExport = async () => {
        setExportLoading(true);
        setExportError(null);
        setExportDone(false);
        try {
            await downloadDataExport();
            setExportDone(true);
            setTimeout(() => setExportDone(false), 4000);
        } catch (err: unknown) {
            setExportError(err instanceof Error ? err.message : "Export failed.");
        } finally {
            setExportLoading(false);
        }
    };

    // ── Delete account state ───────────────────────────────────────────────
    const [showDeleteModal, setShowDeleteModal] = useState(false);
    const [deleteLoading, setDeleteLoading] = useState(false);
    const [deleteError, setDeleteError] = useState<string | null>(null);

    const handleDeleteConfirm = async () => {
        setDeleteLoading(true);
        setDeleteError(null);
        try {
            await deleteAccount();
            logout();
        } catch (err: unknown) {
            setDeleteError(err instanceof Error ? err.message : "Deletion failed.");
            setDeleteLoading(false);
        }
    };

    return (
        <>
            {showDeleteModal && (
                <DeleteAccountModal
                    onClose={() => { setShowDeleteModal(false); setDeleteError(null); }}
                    onConfirm={handleDeleteConfirm}
                    loading={deleteLoading}
                    error={deleteError}
                />
            )}

            <div className="mx-auto max-w-2xl space-y-6">
                <div>
                    <h2 className="text-xl font-semibold tracking-tight">Settings</h2>
                    <p className="mt-1 text-sm text-slate-400">
                        Manage your profile, privacy, and account.
                    </p>
                </div>

                {/* Profile */}
                <SectionCard title="Profile">
                    <div className="flex items-center gap-4 mb-4">
                        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-600 text-white font-semibold text-lg">
                            {(user?.name?.[0] ?? user?.email?.[0] ?? "?").toUpperCase()}
                        </div>
                        <div>
                            <p className="text-sm font-medium text-slate-200">{user?.email ?? "—"}</p>
                            <span className={`text-xs font-medium ${user?.is_pro ? "text-amber-400" : "text-slate-500"}`}>
                                {user?.is_pro ? "Pro Plan" : "Free Plan"}
                            </span>
                        </div>
                    </div>

                    <div>
                        <label className="mb-1.5 block text-xs font-medium text-slate-400">Display Name</label>
                        <input
                            type="text"
                            value={displayName}
                            onChange={(e) => setDisplayName(e.target.value)}
                            placeholder="Your name"
                            maxLength={128}
                            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                        />
                    </div>

                    {profileStatus && <StatusMessage type={profileStatus.type} message={profileStatus.message} />}

                    <div className="mt-2">
                        <button
                            onClick={handleSaveProfile}
                            disabled={profileLoading || displayName.trim() === (user?.name ?? "")}
                            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
                        >
                            {profileLoading ? (
                                <><Loader2 className="h-4 w-4 animate-spin" /> Saving…</>
                            ) : (
                                "Save Changes"
                            )}
                        </button>
                    </div>
                </SectionCard>

                {/* Security */}
                <SectionCard title="Security">
                    <PasswordField label="Current Password" value={currentPw} onChange={setCurrentPw} />
                    <PasswordField label="New Password" value={newPw} onChange={setNewPw} placeholder="Min. 8 characters" />
                    <PasswordField label="Confirm New Password" value={confirmPw} onChange={setConfirmPw} placeholder="Repeat new password" />

                    <TwoFactorSection />

                    {pwStatus && <StatusMessage type={pwStatus.type} message={pwStatus.message} />}

                    <div className="mt-2">
                        <button
                            onClick={handleChangePassword}
                            disabled={pwLoading || !currentPw || !newPw || !confirmPw}
                            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
                        >
                            {pwLoading ? (
                                <><Loader2 className="h-4 w-4 animate-spin" /> Updating…</>
                            ) : (
                                "Update Password"
                            )}
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

                {/* Data & Privacy */}
                <SectionCard title="Data & Privacy">
                    <p className="text-xs text-slate-500 leading-relaxed">
                        Under GDPR and applicable privacy law you have the right to access all data
                        we hold about you and to request permanent deletion of your account. These
                        actions are immediate and irreversible.
                    </p>

                    <div className="rounded-lg border border-slate-700 bg-slate-950/50 px-4 py-4">
                        <div className="flex items-start justify-between gap-4">
                            <div className="flex items-start gap-3">
                                <Download className="mt-0.5 h-4 w-4 flex-shrink-0 text-blue-400" />
                                <div>
                                    <p className="text-sm font-medium text-slate-200">Request Data Export</p>
                                    <p className="mt-0.5 text-xs text-slate-500">
                                        Download a JSON file containing your account details, watchlist,
                                        portfolios, and consent records.
                                    </p>
                                </div>
                            </div>
                            <button
                                onClick={handleExport}
                                disabled={exportLoading}
                                className="flex flex-shrink-0 items-center gap-1.5 rounded-lg border border-blue-600/40 bg-blue-600/10 px-3 py-1.5 text-xs font-semibold text-blue-400 hover:bg-blue-600/20 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
                            >
                                {exportLoading ? (
                                    <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Exporting…</>
                                ) : exportDone ? (
                                    <><CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" /> Downloaded</>
                                ) : (
                                    <><Download className="h-3.5 w-3.5" /> Export</>
                                )}
                            </button>
                        </div>
                        {exportError && <p className="mt-2 text-xs text-red-400">{exportError}</p>}
                    </div>

                    <div className="rounded-lg border border-red-900/30 bg-red-950/10 px-4 py-4">
                        <div className="flex items-start justify-between gap-4">
                            <div className="flex items-start gap-3">
                                <Trash2 className="mt-0.5 h-4 w-4 flex-shrink-0 text-red-400" />
                                <div>
                                    <p className="text-sm font-medium text-red-300">Delete Account</p>
                                    <p className="mt-0.5 text-xs text-red-400/70">
                                        Permanently anonymises your account and deletes all personal data.
                                        This cannot be undone.
                                    </p>
                                </div>
                            </div>
                            <button
                                onClick={() => setShowDeleteModal(true)}
                                className="flex flex-shrink-0 items-center gap-1.5 rounded-lg border border-red-800/50 bg-red-950/30 px-3 py-1.5 text-xs font-semibold text-red-400 hover:bg-red-900/40 transition-colors"
                            >
                                <Trash2 className="h-3.5 w-3.5" />
                                Delete
                            </button>
                        </div>
                    </div>
                </SectionCard>

                {/* Account actions */}
                <SectionCard title="Account">
                    <button
                        onClick={logout}
                        className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm text-slate-300 hover:bg-slate-700 transition-colors"
                    >
                        <LogOut className="h-4 w-4" />
                        Sign Out
                    </button>
                </SectionCard>
            </div>
        </>
    );
}
