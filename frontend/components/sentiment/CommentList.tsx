import { SentimentComment } from "@/lib/api";
import { ThumbsUp, MessageSquare, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";

interface CommentListProps {
    comments: SentimentComment[];
    type: "bullish" | "bearish";
}

export default function CommentList({ comments, type }: CommentListProps) {
    if (!comments || comments.length === 0) {
        return (
            <div className="text-sm text-muted-foreground p-4 bg-muted/50 rounded-lg">
                No highly {type} comments found at the moment.
            </div>
        );
    }

    const badgeColor =
        type === "bullish"
            ? "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300"
            : "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300";

    return (
        <ul className="space-y-4">
            {comments.map((comment, index) => {
                const date = new Date(comment.timestamp);
                return (
                    <li
                        key={index}
                        className="flex flex-col gap-2 p-4 border rounded-lg bg-card text-card-foreground shadow-sm hover:shadow-md transition-shadow"
                    >
                        <div className="flex items-center justify-between text-sm">
                            <div className="flex items-center gap-2">
                                <span className="font-semibold px-2 py-0.5 bg-primary/10 text-primary rounded-full text-xs flex items-center gap-1">
                                    <MessageSquare className="w-3 h-3" /> r/{comment.subreddit}
                                </span>
                                <span className="text-muted-foreground text-xs">
                                    {date.toLocaleDateString()} {date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </span>
                            </div>
                            <span
                                className={cn(
                                    "font-medium px-2 py-0.5 rounded-full text-xs",
                                    badgeColor
                                )}
                            >
                                {comment.sentiment_label}
                            </span>
                        </div>
                        <p className="text-sm leading-relaxed">{comment.text}</p>
                        <div className="flex items-center justify-between mt-1">
                            <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                                <ThumbsUp className="w-3.5 h-3.5 text-primary" />
                                {comment.upvotes} upvotes
                            </div>
                            <a
                                href={comment.url}
                                target="_blank"
                                rel="noreferrer"
                                className="text-xs text-primary hover:underline flex items-center gap-1"
                            >
                                View Thread <ExternalLink className="w-3 h-3" />
                            </a>
                        </div>
                    </li>
                );
            })}
        </ul>
    );
}
