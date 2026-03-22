"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";

export interface User {
    id: string;
    email: string;
    is_pro: boolean;
    is_admin: boolean;
    name?: string | null;
    default_symbol?: string | null;  // Sprint 23
    risk_profile?: string | null;     // Sprint 24
}

interface AuthContextType {
    user: User | null;
    loading: boolean;
    login: (accessToken: string, userData: User, refreshToken?: string) => void;
    logout: () => void;
    updateUser: (patch: Partial<User>) => void;
}

const AuthContext = createContext<AuthContextType>({
    user: null,
    loading: true,
    login: () => { },
    logout: () => { },
    updateUser: () => { },
});

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();
    const pathname = usePathname();

    const REQUIRE_AUTH = process.env.NEXT_PUBLIC_REQUIRE_AUTH === "true";

    useEffect(() => {
        // 1. Dev bypass — instant mock user
        if (!REQUIRE_AUTH) {
            setUser({ id: "00000000-0000-0000-0000-000000000001", email: "dev@mock.local", is_pro: true, is_admin: true });
            setLoading(false);
            return;
        }

        // 2. Check for existing access token in localStorage
        const token = localStorage.getItem("access_token");
        if (!token) {
            setLoading(false);
            if (pathname !== "/auth/login" && pathname !== "/auth/signup") {
                router.push("/auth/login");
            }
            return;
        }

        // 3. Restore user from cache (token trusted; could add /me call here for stricter auth)
        const cachedUser = localStorage.getItem("user_data");
        if (cachedUser) {
            try {
                setUser(JSON.parse(cachedUser));
            } catch {
                localStorage.removeItem("user_data");
            }
        }
        setLoading(false);
    }, [REQUIRE_AUTH, pathname, router]);

    const login = (accessToken: string, userData: User, refreshToken?: string) => {
        localStorage.setItem("access_token", accessToken);
        localStorage.setItem("user_data", JSON.stringify(userData));
        // SEC-04: store refresh token so logout can blacklist its JTI
        if (refreshToken) {
            localStorage.setItem("refresh_token", refreshToken);
        }
        setUser(userData);
        router.push("/");
    };

    const logout = () => {
        // SEC-04: revoke refresh token on the backend before clearing local state
        const refreshToken = localStorage.getItem("refresh_token");
        if (refreshToken) {
            // Fire-and-forget — don't block the UI on the network call
            fetch(`${API_BASE}/api/v1/auth/logout`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ refresh_token: refreshToken }),
                keepalive: true,   // survives page unload
            }).catch(() => {
                // Ignore errors — local state is cleared regardless
            });
        }

        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("user_data");
        setUser(null);
        router.push("/auth/login");
    };

    const updateUser = (patch: Partial<User>) => {
        setUser((prev) => {
            if (!prev) return prev;
            const updated = { ...prev, ...patch };
            localStorage.setItem("user_data", JSON.stringify(updated));
            return updated;
        });
    };

    return (
        <AuthContext.Provider value={{ user, loading, login, logout, updateUser }}>
            {!loading && children}
        </AuthContext.Provider>
    );
}

export const useAuth = () => useContext(AuthContext);
