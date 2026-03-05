import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import Link from 'next/link';
import { ArrowLeft, Clock, Calendar } from 'lucide-react';
import { notFound } from 'next/navigation';

async function fetchPost(slug: string) {
    const API_BASE_URL =
        process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
    try {
        const res = await fetch(`${API_BASE_URL}/api/v1/cms/posts/by-slug/${encodeURIComponent(slug)}`, {
            cache: "no-store",
            signal: AbortSignal.timeout(5000),
        });
        if (res.ok) {
            return await res.json();
        }
    } catch {
        // API unreachable or error
    }
    return null;
}

export default async function BlogPost({ params }: { params: { slug: string } }) {
    const { slug } = params;
    const post = await fetchPost(slug);

    if (!post) {
        notFound();
    }

    const formattedDate = post.published_at
        ? new Date(post.published_at).toLocaleDateString("en-US", {
            year: "numeric",
            month: "long",
            day: "numeric",
        })
        : "—";

    return (
        <div className="container mx-auto px-4 py-8 max-w-4xl animate-fade-in-up">
            <Link
                href="/learn"
                className="inline-flex items-center gap-2 text-zinc-600 dark:text-zinc-400 hover:text-blue-600 dark:hover:text-blue-400 mb-8 transition-colors text-sm font-medium"
            >
                <ArrowLeft className="w-4 h-4" /> Back to Learn
            </Link>

            <article className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 md:p-10 shadow-sm">
                <header className="mb-10 text-center">
                    <span className="inline-block px-3 py-1 text-xs font-semibold text-blue-700 bg-blue-100 dark:text-blue-300 dark:bg-blue-900/30 rounded-full mb-4">
                        {post.category}
                    </span>
                    <h1 className="text-3xl md:text-5xl font-extrabold text-zinc-900 dark:text-zinc-100 mb-6 leading-tight">
                        {post.title}
                    </h1>
                    <div className="flex items-center justify-center gap-6 text-sm text-zinc-500 dark:text-zinc-400">
                        <div className="flex items-center gap-1.5">
                            <Calendar className="w-4 h-4" />
                            <span>{formattedDate}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                            <Clock className="w-4 h-4" />
                            <span>{post.read_time}</span>
                        </div>
                        <div className="flex items-center gap-1.5 border-l border-zinc-300 dark:border-zinc-700 pl-6">
                            <span>By {post.author}</span>
                        </div>
                    </div>
                </header>

                <div className="prose prose-zinc dark:prose-invert max-w-none prose-headings:font-bold prose-a:text-blue-600 dark:prose-a:text-blue-400 hover:prose-a:text-blue-500 prose-img:rounded-xl">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{post.content_md}</ReactMarkdown>
                </div>

                <hr className="my-12 border-zinc-200 dark:border-zinc-800" />

                <div className="bg-zinc-50 dark:bg-zinc-800/50 rounded-xl p-6 text-sm text-zinc-600 dark:text-zinc-400">
                    <strong>Disclaimer:</strong> The contents of this article are for
                    educational and informational purposes only and do not constitute
                    financial or investment advice. Always consult a qualified professional
                    before making any final investment decisions.
                </div>
            </article>
        </div>
    );
}
