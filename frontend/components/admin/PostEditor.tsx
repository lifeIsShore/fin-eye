"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Save, FileText, ArrowLeft, Loader2 } from "lucide-react";
import Link from "next/link";
import { adminCreatePost, adminUpdatePost, type BlogPostFull } from "@/lib/api";

interface PostEditorProps {
    initialData?: BlogPostFull;
}

export function PostEditor({ initialData }: PostEditorProps) {
    const router = useRouter();
    const isEditing = !!initialData;

    const [title, setTitle] = useState(initialData?.title ?? "");
    const [slug, setSlug] = useState(initialData?.slug ?? "");
    const [summary, setSummary] = useState(initialData?.summary ?? "");
    const [category, setCategory] = useState(initialData?.category ?? "General");
    const [readTime, setReadTime] = useState(initialData?.read_time ?? "5 min read");
    const [author, setAuthor] = useState(initialData?.author ?? "Fin-Eye Team");
    const [contentMd, setContentMd] = useState(initialData?.content_md ?? "");

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        try {
            const payload = {
                title,
                slug: slug || undefined,
                summary,
                category,
                read_time: readTime,
                author,
                content_md: contentMd,
            };

            if (isEditing) {
                await adminUpdatePost(initialData.id, payload);
            } else {
                await adminCreatePost(payload);
            }
            router.push("/admin/posts");
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to save post");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="mx-auto max-w-5xl space-y-6">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <Link
                        href="/admin/posts"
                        className="p-2 -ml-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                    >
                        <ArrowLeft className="h-5 w-5" />
                    </Link>
                    <div>
                        <h2 className="text-xl font-semibold flex items-center gap-2">
                            <FileText className="h-5 w-5 text-blue-400" />
                            {isEditing ? "Edit Post" : "New Post"}
                        </h2>
                        {isEditing && (
                            <p className="text-sm text-slate-400 mt-0.5">
                                Editing post #{initialData.id}
                            </p>
                        )}
                    </div>
                </div>

                <button
                    onClick={handleSave}
                    disabled={loading || !title || !summary || !contentMd}
                    className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2 text-sm font-semibold text-white hover:bg-blue-500 transition-colors disabled:opacity-50"
                >
                    {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                    Save Draft
                </button>
            </div>

            {error && (
                <div className="p-4 rounded-lg bg-red-900/30 border border-red-500/50 text-red-200 text-sm">
                    {error}
                </div>
            )}

            <form onSubmit={handleSave} className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Left Column (Metadata) */}
                <div className="space-y-6">
                    <div className="space-y-4 rounded-xl border border-slate-800 bg-slate-900/50 p-6">
                        <h3 className="text-sm font-medium text-slate-300">Metadata</h3>
                        
                        <div className="space-y-1">
                            <label className="text-xs font-medium text-slate-400">Title <span className="text-red-400">*</span></label>
                            <input
                                type="text"
                                required
                                value={title}
                                onChange={(e) => setTitle(e.target.value)}
                                className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                                placeholder="E.g. Understanding Market Regimes"
                            />
                        </div>

                        <div className="space-y-1">
                            <label className="text-xs font-medium text-slate-400">Slug (Optional)</label>
                            <input
                                type="text"
                                value={slug}
                                onChange={(e) => setSlug(e.target.value)}
                                className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                                placeholder="understanding-market-regimes"
                            />
                            <p className="text-[10px] text-slate-500 leading-tight">Leave blank to auto-generate from title.</p>
                        </div>

                        <div className="space-y-1">
                            <label className="text-xs font-medium text-slate-400">Summary <span className="text-red-400">*</span></label>
                            <textarea
                                required
                                value={summary}
                                rows={3}
                                onChange={(e) => setSummary(e.target.value)}
                                className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
                                placeholder="A brief 1-2 sentence description of the post..."
                            />
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-1">
                                <label className="text-xs font-medium text-slate-400">Category</label>
                                <input
                                    type="text"
                                    value={category}
                                    onChange={(e) => setCategory(e.target.value)}
                                    className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
                                />
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-medium text-slate-400">Read Time</label>
                                <input
                                    type="text"
                                    value={readTime}
                                    onChange={(e) => setReadTime(e.target.value)}
                                    className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
                                />
                            </div>
                        </div>

                        <div className="space-y-1">
                            <label className="text-xs font-medium text-slate-400">Author</label>
                            <input
                                type="text"
                                value={author}
                                onChange={(e) => setAuthor(e.target.value)}
                                className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
                            />
                        </div>
                    </div>
                </div>

                {/* Right Column (Markdown Editor) */}
                <div className="lg:col-span-2 space-y-4">
                    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6 h-full flex flex-col">
                        <h3 className="text-sm font-medium text-slate-300 mb-4">Content (Markdown) <span className="text-red-400">*</span></h3>
                        <textarea
                            required
                            value={contentMd}
                            onChange={(e) => setContentMd(e.target.value)}
                            className="flex-1 w-full min-h-[500px] rounded-md border border-slate-700 bg-slate-950 p-4 text-sm text-slate-300 font-mono focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-y"
                            placeholder="# Heading 1&#10;&#10;Write your markdown content here...&#10;&#10;## Subheading&#10;- Bullet point 1&#10;- Bullet point 2"
                        />
                        <p className="text-xs text-slate-500 mt-3">
                            Uses standard GitHub-flavored Markdown. Note: the post will be saved as a Draft by default. You can publish it from the main list.
                        </p>
                    </div>
                </div>
            </form>
        </div>
    );
}
