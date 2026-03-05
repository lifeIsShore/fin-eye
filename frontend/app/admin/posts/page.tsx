"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import {
    PlusCircle, Edit2, Trash2, Eye, EyeOff,
    Loader2, AlertTriangle, BookOpen, RefreshCw,
} from "lucide-react";
import {
    adminFetchAllPosts, adminDeletePost,
    adminPublishPost, adminUnpublishPost,
    type BlogPostSummary,
} from "@/lib/api";

function StatusBadge({ status }: { status: string }) {
    const published = status === "published";
    return (
        <span className={`
            inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider
            ${published
                ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-400"
                : "bg-slate-700/50 border border-slate-600/50 text-slate-400"
            }
        `}>
            {published ? "Published" : "Draft"}
        </span>
    );
}

export default function AdminPostsPage() {
    const { user, loading: authLoading } = useAuth();
    const router = useRouter();

    const [posts, setPosts] = useState<BlogPostSummary[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [actionId, setActionId] = useState<number | null>(null);

    // Admin guard
    useEffect(() => {
        if (!authLoading && user && !(user as any).is_admin) {
            router.replace("/");
        }
    }, [user, authLoading, router]);

    const loadPosts = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await adminFetchAllPosts();
            setPosts(data);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed to load posts");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { loadPosts(); }, []);

    const handleTogglePublish = async (post: BlogPostSummary) => {
        setActionId(post.id);
        try {
            const updated = post.status === "published"
                ? await adminUnpublishPost(post.id)
                : await adminPublishPost(post.id);
            setPosts((prev) => prev.map((p) => p.id === updated.id ? updated : p));
        } catch (e: unknown) {
            alert(e instanceof Error ? e.message : "Action failed");
        } finally {
            setActionId(null);
        }
    };

    const handleDelete = async (post: BlogPostSummary) => {
        if (!confirm(`Permanently delete "${post.title}"? This cannot be undone.`)) return;
        setActionId(post.id);
        try {
            await adminDeletePost(post.id);
            setPosts((prev) => prev.filter((p) => p.id !== post.id));
        } catch (e: unknown) {
            alert(e instanceof Error ? e.message : "Delete failed");
        } finally {
            setActionId(null);
        }
    };

    if (authLoading || loading) {
        return (
            <div className="flex items-center justify-center py-32">
                <Loader2 className="h-8 w-8 animate-spin text-slate-500" />
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center py-32 gap-4">
                <AlertTriangle className="h-8 w-8 text-red-400" />
                <p className="text-red-400 text-sm">{error}</p>
                <button onClick={loadPosts} className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1">
                    <RefreshCw className="h-3 w-3" /> Retry
                </button>
            </div>
        );
    }

    return (
        <div className="mx-auto max-w-5xl space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-xl font-semibold flex items-center gap-2">
                        <BookOpen className="h-5 w-5 text-blue-400" />
                        Blog Posts
                    </h2>
                    <p className="text-sm text-slate-400 mt-0.5">
                        {posts.length} post{posts.length !== 1 ? "s" : ""} ·{" "}
                        {posts.filter((p) => p.status === "published").length} published
                    </p>
                </div>
                <Link
                    href="/admin/posts/new"
                    className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 transition-colors"
                >
                    <PlusCircle className="h-4 w-4" />
                    New Post
                </Link>
            </div>

            {/* Table */}
            {posts.length === 0 ? (
                <div className="rounded-xl border border-slate-800 bg-slate-900/50 flex flex-col items-center justify-center py-20 gap-3">
                    <BookOpen className="h-10 w-10 text-slate-600" />
                    <p className="text-slate-400 text-sm">No posts yet.</p>
                    <Link href="/admin/posts/new" className="text-blue-400 text-sm hover:text-blue-300 underline">
                        Create your first post →
                    </Link>
                </div>
            ) : (
                <div className="rounded-xl border border-slate-800 bg-slate-900/50 overflow-hidden">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b border-slate-800 text-xs font-medium text-slate-500 uppercase tracking-wider">
                                <th className="px-4 py-3 text-left">Title</th>
                                <th className="px-4 py-3 text-left hidden md:table-cell">Category</th>
                                <th className="px-4 py-3 text-left hidden lg:table-cell">Updated</th>
                                <th className="px-4 py-3 text-left">Status</th>
                                <th className="px-4 py-3 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {posts.map((post) => (
                                <tr
                                    key={post.id}
                                    className="border-b border-slate-800/50 last:border-0 hover:bg-slate-800/30 transition-colors"
                                >
                                    <td className="px-4 py-3">
                                        <Link
                                            href={`/admin/posts/${post.id}`}
                                            className="font-medium text-slate-200 hover:text-blue-400 transition-colors line-clamp-1"
                                        >
                                            {post.title}
                                        </Link>
                                        <p className="text-xs text-slate-600 mt-0.5 line-clamp-1">
                                            /{post.slug}
                                        </p>
                                    </td>
                                    <td className="px-4 py-3 hidden md:table-cell text-slate-400 text-xs">
                                        {post.category}
                                    </td>
                                    <td className="px-4 py-3 hidden lg:table-cell text-slate-500 text-xs">
                                        {new Date(post.updated_at).toLocaleDateString("en-US", {
                                            month: "short", day: "numeric", year: "numeric"
                                        })}
                                    </td>
                                    <td className="px-4 py-3">
                                        <StatusBadge status={post.status} />
                                    </td>
                                    <td className="px-4 py-3">
                                        <div className="flex items-center justify-end gap-1">
                                            <Link
                                                href={`/admin/posts/${post.id}`}
                                                className="rounded p-1.5 text-slate-500 hover:text-slate-200 hover:bg-slate-700 transition-colors"
                                                title="Edit"
                                            >
                                                <Edit2 className="h-3.5 w-3.5" />
                                            </Link>
                                            <button
                                                onClick={() => handleTogglePublish(post)}
                                                disabled={actionId === post.id}
                                                className="rounded p-1.5 text-slate-500 hover:text-slate-200 hover:bg-slate-700 transition-colors disabled:opacity-40"
                                                title={post.status === "published" ? "Unpublish" : "Publish"}
                                            >
                                                {actionId === post.id
                                                    ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                                    : post.status === "published"
                                                        ? <EyeOff className="h-3.5 w-3.5" />
                                                        : <Eye className="h-3.5 w-3.5" />
                                                }
                                            </button>
                                            <button
                                                onClick={() => handleDelete(post)}
                                                disabled={actionId === post.id}
                                                className="rounded p-1.5 text-slate-500 hover:text-red-400 hover:bg-red-950/30 transition-colors disabled:opacity-40"
                                                title="Delete"
                                            >
                                                <Trash2 className="h-3.5 w-3.5" />
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
