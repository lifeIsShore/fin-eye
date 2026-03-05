"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";

interface User {
    id: string;
    email: string;
    is_pro: boolean;
    is_admin: boolean;
    name?: string | null;
}

interface AuthContextType {
    user: User | null;
    loading: boolean;
    login: (token: string, userData: User) => void;
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

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();
    const pathname = usePathname();

    // BYPASS: Read from our environment to see if we should enforce authentication
    const REQUIRE_AUTH = process.env.NEXT_PUBLIC_REQUIRE_AUTH === "true";

    useEffect(() => {
        // 1. If bypass is enabled, instantly set a mock user and stop loading.
        if (!REQUIRE_AUTH) {
            setUser({ id: "00000000-0000-0000-0000-000000000001", email: "dev@mock.local", is_pro: true, is_admin: true });
            setLoading(false);
            return;
        }

        // 2. Otherwise, check for an existing JWT token
        const token = localStorage.getItem("access_token");
        if (!token) {
            setLoading(false);
            // Auto-redirect to login if attempting access to protected routes
            if (pathname !== "/auth/login" && pathname !== "/auth/signup") {
                router.push("/auth/login");
            }
            return;
        }

        // 3. Optional: we could validate the token via API here. 
        // For now, we trust the cache and parse out user data stored at login
        const cachedUser = localStorage.getItem("user_data");
        if (cachedUser) {
            setUser(JSON.parse(cachedUser));
        }
        setLoading(false);
    }, [REQUIRE_AUTH, pathname, router]);

    const login = (token: string, userData: User) => {
        localStorage.setItem("access_token", token);
        localStorage.setItem("user_data", JSON.stringify(userData));
        setUser(userData);
        router.push("/");
    };

    const logout = () => {
        localStorage.removeItem("access_token");
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
            {/* Hide rendering until auth state determines if we should redirect or show app */}
            {!loading && children}
        </AuthContext.Provider>
    );
}

export const useAuth = () => useContext(AuthContext);
