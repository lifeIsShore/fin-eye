import fs from "fs";
import path from "path";
import matter from "gray-matter";
import { BlogCard } from "@/components/learn/BlogCard";

export const metadata = {
    title: "Learn | Fin-Eye",
    description:
        "Educational resources and guides for using Fin-Eye and understanding the market.",
};

/**
 * Load posts from the DB API (CMS).
 * Falls back to filesystem markdown files if the API is unavailable so that
 * the Learn tab always works even when the backend is down or in dev mode.
 */
async function loadPosts(): Promise<
    {
        slug: string;
        title: string;
        summary: string;
        readTime: string;
        date: string;
        category: string;
        source: "db" | "file";
    }[]
> {
    const API_BASE_URL =
        process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

    // --- Try DB first ---
    try {
        const res = await fetch(`${API_BASE_URL}/api/v1/cms/posts/published`, {
            cache: "no-store",
            signal: AbortSignal.timeout(3000),
        });
        if (res.ok) {
            const data = await res.json();
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            return data.map((p: any) => ({
                slug: `db-${p.slug}`,          // prefix prevents collision with file slugs
                title: p.title,
                summary: p.summary,
                readTime: p.read_time,
                date: p.published_at
                    ? new Date(p.published_at).toLocaleDateString("en-US", {
                          year: "numeric",
                          month: "long",
                          day: "numeric",
                      })
                    : "—",
                category: p.category,
                source: "db" as const,
            }));
        }
    } catch {
        // API unreachable — fall through to filesystem
    }

    // --- Filesystem fallback ---
    const contentDir = path.join(process.cwd(), "content", "blog");
    if (!fs.existsSync(contentDir)) return [];

    const files = fs.readdirSync(contentDir).filter((f) => f.endsWith(".md"));
    return files.map((filename) => {
        const slug = filename.replace(".md", "");
        const raw = fs.readFileSync(path.join(contentDir, filename), "utf-8");
        const { data: fm } = matter(raw);
        return {
            slug,
            title: fm.title as string,
            summary: fm.summary as string,
            readTime: fm.readTime as string,
            date: fm.date as string,
            category: fm.category as string,
            source: "file" as const,
        };
    });
}

export default async function LearnPage() {
    const posts = await loadPosts();
    posts.sort(
        (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
    );

    return (
        <div className="container mx-auto px-4 py-8 max-w-7xl animate-fade-in-up">
            <div className="mb-12">
                <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-zinc-900 to-zinc-500 dark:from-white dark:to-zinc-400 mb-4">
                    Learn &amp; Insights
                </h1>
                <p className="text-lg text-zinc-600 dark:text-zinc-400 max-w-2xl">
                    Master the concepts behind the Global Alignment Score, understand macro
                    indicators, and learn how to navigate different market regimes.
                </p>
            </div>

            {posts.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-24 text-center">
                    <p className="text-slate-500 text-lg">No articles published yet.</p>
                    <p className="text-slate-600 text-sm mt-2">
                        Check back soon — educational content is on the way.
                    </p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {posts.map((post) => (
                        <BlogCard key={post.slug} {...post} />
                    ))}
                </div>
            )}
        </div>
    );
}
