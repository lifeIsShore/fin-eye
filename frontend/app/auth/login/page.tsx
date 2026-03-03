"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "../../../components/AuthProvider";

export default function LoginPage() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const router = useRouter();
    const { login } = useAuth();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setError("");

        try {
            // 1. Send Login Request
            const formData = new URLSearchParams();
            formData.append("username", email);
            formData.append("password", password);

            const res = await fetch("http://localhost:8000/api/v1/auth/login", {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                body: formData,
            });

            if (!res.ok) {
                throw new Error("Invalid credentials");
            }

            const data = await res.json();

            // 2. Hydrate token to get User Profile
            const meRes = await fetch("http://localhost:8000/api/v1/auth/me", {
                headers: {
                    Authorization: `Bearer ${data.access_token}`,
                },
            });

            if (!meRes.ok) throw new Error("Failed to fetch user profile");

            const userData = await meRes.json();

            // 3. Complete context login
            login(data.access_token, userData);

        } catch (err: any) {
            setError(err.message || "An expected error occurred");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex flex-col flex-1 items-center justify-center p-4">
            <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900/50 p-8 shadow-2xl backdrop-blur-sm">
                <div className="mb-8 text-center">
                    <h1 className="text-3xl font-bold tracking-tight text-slate-50">Welcome back</h1>
                    <p className="mt-2 text-sm text-slate-400">Log in to view your market consensus</p>
                </div>

                {error && (
                    <div className="mb-6 rounded-md bg-red-500/10 p-4 text-sm text-red-400 border border-red-500/20">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-6">
                    <div>
                        <label className="block text-sm font-medium text-slate-300">Email Address</label>
                        <input
                            type="email"
                            required
                            className="mt-2 block w-full rounded-md border border-slate-700 bg-slate-950 px-4 py-2 placeholder-slate-500 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 sm:text-sm text-slate-50 transition-colors"
                            placeholder="you@example.com"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-300">Password</label>
                        <input
                            type="password"
                            required
                            className="mt-2 block w-full rounded-md border border-slate-700 bg-slate-950 px-4 py-2 placeholder-slate-500 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 sm:text-sm text-slate-50 transition-colors"
                            placeholder="••••••••"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                        />
                    </div>

                    <button
                        type="submit"
                        disabled={isLoading}
                        className="w-full rounded-md bg-white px-4 py-2 text-sm font-medium text-slate-900 shadow-sm hover:bg-slate-200 focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-slate-950 disabled:opacity-50 transition-all font-semibold"
                    >
                        {isLoading ? "Authenticating..." : "Sign In"}
                    </button>
                </form>

                <p className="mt-8 text-center text-sm text-slate-400">
                    Don't have an account?{" "}
                    <Link href="/auth/signup" className="font-semibold text-white hover:text-blue-400 transition-colors">
                        Sign up
                    </Link>
                </p>
            </div>
        </div>
    );
}
