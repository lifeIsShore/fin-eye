"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { PostEditor } from "@/components/admin/PostEditor";
import { Loader2 } from "lucide-react";

export default function NewPostPage() {
    const { user, loading: authLoading } = useAuth();
    const router = useRouter();

    useEffect(() => {
        if (!authLoading && user && !(user as any).is_admin) {
            router.replace("/");
        }
    }, [user, authLoading, router]);

    if (authLoading) {
        return (
            <div className="flex items-center justify-center py-32">
                <Loader2 className="h-8 w-8 animate-spin text-slate-500" />
            </div>
        );
    }

    if (!user || !(user as any).is_admin) return null;

    return <PostEditor />;
}
