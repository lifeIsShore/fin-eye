"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { PostEditor } from "@/components/admin/PostEditor";
import { adminFetchPost, type BlogPostFull } from "@/lib/api";
import { Loader2, AlertTriangle, RefreshCw } from "lucide-react";

export default function EditPostPage() {
    const { user, loading: authLoading } = useAuth();
    const router = useRouter();
    const params = useParams();
    const postId = Number(params.id);

    const [post, setPost] = useState<BlogPostFull | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!authLoading && user && !(user as any).is_admin) {
            router.replace("/");
        }
    }, [user, authLoading, router]);

    const loadPost = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await adminFetchPost(postId);
            setPost(data);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed to load post");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (!authLoading && user && (user as any).is_admin) {
            loadPost();
        }
    }, [user, authLoading, postId]);

    if (authLoading || loading) {
        return (
            <div className="flex items-center justify-center py-32">
                <Loader2 className="h-8 w-8 animate-spin text-slate-500" />
            </div>
        );
    }

    if (!user || !(user as any).is_admin) return null;

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center py-32 gap-4">
                <AlertTriangle className="h-8 w-8 text-red-400" />
                <p className="text-red-400 text-sm">{error}</p>
                <button onClick={loadPost} className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1">
                    <RefreshCw className="h-3 w-3" /> Retry
                </button>
            </div>
        );
    }

    return post ? <PostEditor initialData={post} /> : null;
}
