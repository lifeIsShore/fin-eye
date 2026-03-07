"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
    Save, FileText, ArrowLeft, Loader2,
    Eye, EyeOff, Columns,
} from "lucide-react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { adminCreatePost, adminUpdatePost, type BlogPostFull } from "@/lib/api";

// ─── Types ─────────────────────────────────────────────────────────────────

interface PostEditorProps {
    initialData?: BlogPostFull;
}

type EditorView = "write" | "preview" | "split";

// ─── Markdown preview styles ───────────────────────────────────────────────
// Uses Tailwind Typography prose classes for clean rendered output.

const proseClasses = [
    "prose prose-invert max-w-none",
    "prose-headings:font-bold prose-headings:text-slate-100",
    "prose-h1:text-2xl prose-h2:text-xl prose-h3:text-lg",
    "prose-p:text-slate-300 prose-p:leading-relaxed",
    "prose-a:text-blue-400 prose-a:no-underline hover:prose-a:underline",
    "prose-strong:text-slate-200",
    "prose-code:bg-slate-800 prose-code:text-emerald-300 prose-code:rounded prose-code:px-1 prose-code:py-0.5 prose-code:text-sm",
    "prose-pre:bg-slate-900 prose-pre:border prose-pre:border-slate-700 prose-pre:rounded-lg",
    "prose-blockquote:border-l-blue-500 prose-blockquote:text-slate-400 prose-blockquote:bg-slate-900/40 prose-blockquote:py-1 prose-blockquote:px-4 prose-blockquote:rounded-r-lg",
    "prose-table:text-sm prose-th:text-slate-300 prose-td:text-slate-400",
    "prose-hr:border-slate-700",
    "prose-li:text-slate-300",
].join(" ");

// ─── Sub-components ────────────────────────────────────────────────────────

function ViewToggle({
    view,
    onChange,
}: {
    view: EditorView;
    onChange: (v: EditorView) => void;
}) {
    const btn = (v: EditorView, label: string, Icon: React.ElementType) => (
        <button
            type="button"
            onClick={() => onChange(v)}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                view === v
                    ? "bg-slate-700 text-slate-100"
                    : "text-slate-500 hover:text-slate-300 hover:bg-slate-800"
            }`}
        >
            <Icon className="h-3.5 w-3.5" />
            {label}
        </button>
    );

    return (
        <div className="flex items-center gap-1 rounded-lg border border-slate-800 bg-slate-900/50 p-0.5">
            {btn("write", "Write", FileText)}
            {btn("split", "Split", Columns)}
            {btn("preview", "Preview", Eye)}
        </div>
    );
}

function MarkdownPreview({ content }: { content: string }) {
    if (!content.trim()) {
        return (
            <div className="flex flex-col items-center justify-center h-full gap-2 text-slate-600">
                <Eye className="h-8 w-8" />
                <p className="text-sm">Start writing to see a preview</p>
            </div>
        );
    }
    return (
        <div className={`${proseClasses} p-6 h-full overflow-y-auto`}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        </div>
    );
}

// ─── Main Component ────────────────────────────────────────────────────────

export function PostEditor({ initialData }: PostEditorProps) {
    const router   = useRouter();
    const isEditing = !!initialData;

    // ── Form state ──────────────────────────────────────────────────────────
    const [title,     setTitle]     = useState(initialData?.title      ?? "");
    const [slug,      setSlug]      = useState(initialData?.slug       ?? "");
    const [summary,   setSummary]   = useState(initialData?.summary    ?? "");
    const [category,  setCategory]  = useState(initialData?.category   ?? "General");
    const [readTime,  setReadTime]  = useState(initialData?.read_time  ?? "5 min read");
    const [author,    setAuthor]    = useState(initialData?.author     ?? "Fin-Eye Team");
    const [contentMd, setContentMd] = useState(initialData?.content_md ?? "");

    // ── UI state ─────────────────────────────────────────────────────────────
    const [view,    setView]    = useState<EditorView>("split");
    const [loading, setLoading] = useState(false);
    const [error,   setError]   = useState<string | null>(null);

    // ── Handlers ─────────────────────────────────────────────────────────────
    const handleSave = useCallback(async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        try {
            const payload = {
                title,
                slug:      slug || undefined,
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
    }, [title, slug, summary, category, readTime, author, contentMd, isEditing, initialData, router]);

    const canSave = title.trim() && summary.trim() && contentMd.trim();

    // ── Render ────────────────────────────────────────────────────────────────
    return (
        <div className="mx-auto max-w-7xl space-y-5">

            {/* ── Top bar ──────────────────────────────────────────────────── */}
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
                            {isEditing ? `Editing: ${initialData.title}` : "New Post"}
                        </h2>
                        {isEditing && (
                            <p className="text-xs text-slate-500 mt-0.5">
                                Post #{initialData.id} · slug: /{initialData.slug}
                            </p>
                        )}
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <ViewToggle view={view} onChange={setView} />
                    <button
                        onClick={handleSave}
                        disabled={loading || !canSave}
                        className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2 text-sm font-semibold text-white hover:bg-blue-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {loading
                            ? <Loader2 className="h-4 w-4 animate-spin" />
                            : <Save className="h-4 w-4" />
                        }
                        Save Draft
                    </button>
                </div>
            </div>

            {/* ── Error banner ─────────────────────────────────────────────── */}
            {error && (
                <div className="p-4 rounded-lg bg-red-900/30 border border-red-500/50 text-red-200 text-sm">
                    {error}
                </div>
            )}

            {/* ── Body ─────────────────────────────────────────────────────── */}
            <form onSubmit={handleSave} className="grid grid-cols-1 lg:grid-cols-4 gap-6">

                {/* ─── Left sidebar: metadata ──────────────────────────────── */}
                <aside className="lg:col-span-1 space-y-4">
                    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-5 space-y-4">
                        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                            Post Metadata
                        </h3>

                        <Field label="Title" required>
                            <input
                                type="text"
                                required
                                value={title}
                                onChange={(e) => setTitle(e.target.value)}
                                className={inputClass}
                                placeholder="Understanding Market Regimes"
                            />
                        </Field>

                        <Field label="Slug" hint="Auto-generated from title if blank.">
                            <input
                                type="text"
                                value={slug}
                                onChange={(e) => setSlug(e.target.value)}
                                className={inputClass}
                                placeholder="understanding-market-regimes"
                            />
                        </Field>

                        <Field label="Summary" required>
                            <textarea
                                required
                                value={summary}
                                rows={3}
                                onChange={(e) => setSummary(e.target.value)}
                                className={`${inputClass} resize-none`}
                                placeholder="1–2 sentence description shown in the article list."
                            />
                        </Field>

                        <div className="grid grid-cols-2 gap-3">
                            <Field label="Category">
                                <input
                                    type="text"
                                    value={category}
                                    onChange={(e) => setCategory(e.target.value)}
                                    className={inputClass}
                                />
                            </Field>
                            <Field label="Read Time">
                                <input
                                    type="text"
                                    value={readTime}
                                    onChange={(e) => setReadTime(e.target.value)}
                                    className={inputClass}
                                />
                            </Field>
                        </div>

                        <Field label="Author">
                            <input
                                type="text"
                                value={author}
                                onChange={(e) => setAuthor(e.target.value)}
                                className={inputClass}
                            />
                        </Field>
                    </div>

                    {/* Word count helper */}
                    <p className="text-xs text-slate-600 text-right">
                        {contentMd.split(/\s+/).filter(Boolean).length} words ·{" "}
                        {contentMd.length} chars
                    </p>
                </aside>

                {/* ─── Right main: editor + preview ────────────────────────── */}
                <div className={`${view === "split" ? "lg:col-span-3 grid grid-cols-2 gap-4" : "lg:col-span-3"}`}>
                    {/* Editor */}
                    {(view === "write" || view === "split") && (
                        <div className="rounded-xl border border-slate-800 bg-slate-900/50 flex flex-col" style={{ minHeight: 600 }}>
                            <div className="flex items-center justify-between px-4 py-2.5 border-b border-slate-800">
                                <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                                    Markdown
                                </span>
                                <span className="text-[10px] text-slate-700">GFM supported</span>
                            </div>
                            <textarea
                                required
                                value={contentMd}
                                onChange={(e) => setContentMd(e.target.value)}
                                className="flex-1 w-full bg-transparent p-4 text-sm text-slate-300 font-mono focus:outline-none resize-none leading-relaxed"
                                placeholder={"# Heading 1\n\nWrite your article here...\n\n## Subheading\n\n- Bullet point 1\n- Bullet point 2\n\n> Blockquote\n\n| Col1 | Col2 |\n|------|------|\n| A    | B    |"}
                                spellCheck={false}
                            />
                        </div>
                    )}

                    {/* Preview */}
                    {(view === "preview" || view === "split") && (
                        <div className="rounded-xl border border-slate-800 bg-slate-900/30 flex flex-col overflow-hidden" style={{ minHeight: 600 }}>
                            <div className="flex items-center px-4 py-2.5 border-b border-slate-800">
                                <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                                    Preview
                                </span>
                            </div>
                            <div className="flex-1 overflow-y-auto">
                                <MarkdownPreview content={contentMd} />
                            </div>
                        </div>
                    )}
                </div>
            </form>
        </div>
    );
}

// ─── Helpers ───────────────────────────────────────────────────────────────

const inputClass =
    "w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white " +
    "placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

function Field({
    label,
    required,
    hint,
    children,
}: {
    label: string;
    required?: boolean;
    hint?: string;
    children: React.ReactNode;
}) {
    return (
        <div className="space-y-1">
            <label className="text-xs font-medium text-slate-400">
                {label}
                {required && <span className="text-red-400 ml-0.5">*</span>}
            </label>
            {children}
            {hint && <p className="text-[10px] text-slate-600 leading-snug">{hint}</p>}
        </div>
    );
}
