import Link from "next/link";
import { Clock, Calendar } from "lucide-react";

interface BlogCardProps {
    title: string;
    summary: string;
    readTime: string;
    date: string;
    category: string;
    slug: string;
}

export function BlogCard({
    title,
    summary,
    readTime,
    date,
    category,
    slug,
}: BlogCardProps) {
    return (
        <Link href={`/learn/${slug}`} className="block group h-full">
            <div className="flex flex-col justify-between h-full p-6 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl transition-all duration-300 hover:shadow-lg hover:border-blue-500/50 dark:hover:border-blue-500/50">
                <div>
                    <div className="flex items-center justify-between mb-4">
                        <span className="px-3 py-1 text-xs font-medium text-blue-700 bg-blue-100 dark:text-blue-300 dark:bg-blue-900/30 rounded-full">
                            {category}
                        </span>
                    </div>
                    <h3 className="text-xl font-bold mb-2 text-zinc-900 dark:text-zinc-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                        {title}
                    </h3>
                    <p className="text-zinc-600 dark:text-zinc-400 mb-6 line-clamp-3">
                        {summary}
                    </p>
                </div>
                <div className="flex items-center gap-4 text-sm text-zinc-500 dark:text-zinc-500">
                    <div className="flex items-center gap-1.5">
                        <Calendar className="w-4 h-4" />
                        <span>{date}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                        <Clock className="w-4 h-4" />
                        <span>{readTime}</span>
                    </div>
                </div>
            </div>
        </Link>
    );
}
