import fs from 'fs';
import path from 'path';
import matter from 'gray-matter';
import { BlogCard } from '@/components/learn/BlogCard';

export const metadata = {
    title: 'Learn | Fin-Eye',
    description: 'Educational resources and guides for using Fin-Eye and understanding the market.',
};

export default function LearnPage() {
    const contentDir = path.join(process.cwd(), 'content', 'blog');
    const files = fs.readdirSync(contentDir);

    const posts = files.map((filename) => {
        const slug = filename.replace('.md', '');
        const markdownWithMeta = fs.readFileSync(path.join(contentDir, filename), 'utf-8');
        const { data: frontmatter } = matter(markdownWithMeta);

        return {
            slug,
            title: frontmatter.title as string,
            summary: frontmatter.summary as string,
            readTime: frontmatter.readTime as string,
            date: frontmatter.date as string,
            category: frontmatter.category as string,
        };
    });

    // Sort by date descending
    posts.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());

    return (
        <div className="container mx-auto px-4 py-8 max-w-7xl animate-fade-in-up">
            <div className="mb-12">
                <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-zinc-900 to-zinc-500 dark:from-white dark:to-zinc-400 mb-4">
                    Learn & Insights
                </h1>
                <p className="text-lg text-zinc-600 dark:text-zinc-400 max-w-2xl">
                    Master the concepts behind the Global Alignment Score, understand macro indicators, and learn how to navigate different market regimes.
                </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {posts.map((post) => (
                    <BlogCard key={post.slug} {...post} />
                ))}
            </div>
        </div>
    );
}
