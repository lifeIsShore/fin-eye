"use client";
/**
 * TickerComments.tsx — Sprint 52
 * Collapsible per-ticker discussion thread panel.
 * Place below <SocialSignalsPanel /> in app/page.tsx.
 */
import { useState, useEffect, useRef } from "react";
import { ChevronDown, ChevronUp, ThumbsUp, ThumbsDown, Trash2, Send } from "lucide-react";
import {
  fetchComments,
  postComment,
  deleteComment,
  reactToComment,
  type CommentDto,
} from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { formatDistanceToNow } from "date-fns";

interface Props {
  symbol: string;
}

export default function TickerComments({ symbol }: Props) {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [comments, setComments] = useState<CommentDto[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const [posting, setPosting] = useState(false);
  const [body, setBody] = useState("");
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const load = async (reset = false) => {
    setLoading(true);
    setError(null);
    try {
      const beforeId = reset ? undefined : comments[comments.length - 1]?.id;
      const data = await fetchComments(symbol, 20, reset ? undefined : beforeId);
      setComments(prev => reset ? data.comments : [...prev, ...data.comments]);
      setHasMore(data.has_more);
    } catch {
      setError("Failed to load comments.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) load(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, symbol]);

  const handlePost = async () => {
    if (!body.trim() || body.length < 10 || body.length > 500) return;
    setPosting(true);
    setError(null);
    try {
      const comment = await postComment(symbol, body.trim());
      setComments(prev => [comment, ...prev]);
      setBody("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to post comment.");
    } finally {
      setPosting(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteComment(id);
      setComments(prev => prev.filter(c => c.id !== id));
    } catch {
      setError("Failed to delete comment.");
    }
  };

  const handleReact = async (id: string, reaction: "up" | "down") => {
    try {
      const updated = await reactToComment(id, reaction);
      setComments(prev =>
        prev.map(c =>
          c.id === id
            ? {
                ...c,
                upvotes: updated.upvotes,
                downvotes: updated.downvotes,
                user_reaction: c.user_reaction === reaction ? null : reaction,
              }
            : c,
        ),
      );
    } catch {
      /* silent */
    }
  };

  const charCount = body.length;
  const charOk = charCount >= 10 && charCount <= 500;

  return (
    <div className="rounded-xl border border-slate-700/50 bg-slate-900/60 backdrop-blur-sm">
      {/* Header / toggle */}
      <button
        onClick={() => setOpen(o => !o)}
        className="flex w-full items-center justify-between px-4 py-3 text-left"
      >
        <span className="text-sm font-medium text-slate-300">
          💬 Discussion
          {comments.length > 0 && (
            <span className="ml-2 rounded-full bg-slate-700 px-2 py-0.5 text-xs text-slate-400">
              {comments.length}{hasMore ? "+" : ""}
            </span>
          )}
        </span>
        {open ? (
          <ChevronUp className="h-4 w-4 text-slate-500" />
        ) : (
          <ChevronDown className="h-4 w-4 text-slate-500" />
        )}
      </button>

      {open && (
        <div className="border-t border-slate-700/50 px-4 pb-4 pt-3 space-y-4">
          {/* Compose */}
          {user ? (
            <div className="space-y-2">
              <textarea
                value={body}
                onChange={e => setBody(e.target.value)}
                placeholder="Share your analysis… (10–500 chars)"
                rows={3}
                className="w-full resize-none rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:border-emerald-500 focus:outline-none"
              />
              <div className="flex items-center justify-between">
                <span className={`text-xs ${charOk ? "text-slate-500" : "text-rose-400"}`}>
                  {charCount}/500
                </span>
                <button
                  onClick={handlePost}
                  disabled={!charOk || posting}
                  className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-500 disabled:opacity-40"
                >
                  <Send className="h-3 w-3" />
                  {posting ? "Posting…" : "Post"}
                </button>
              </div>
            </div>
          ) : (
            <p className="text-xs text-slate-500">Sign in to post a comment.</p>
          )}

          {error && <p className="text-xs text-rose-400">{error}</p>}

          {/* Comment list */}
          {loading && comments.length === 0 ? (
            <p className="text-xs text-slate-500">Loading…</p>
          ) : comments.length === 0 ? (
            <p className="text-xs text-slate-500">No comments yet. Be the first.</p>
          ) : (
            <ul className="space-y-3">
              {comments.map(c => (
                <li key={c.id} className="rounded-lg bg-slate-800/60 px-3 py-2.5 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-emerald-400">{c.username}</span>
                    <span className="text-xs text-slate-500">
                      {formatDistanceToNow(new Date(c.created_at), { addSuffix: true })}
                    </span>
                  </div>
                  <p className="text-sm text-slate-200 leading-snug">{c.body}</p>
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => handleReact(c.id, "up")}
                      className={`flex items-center gap-1 text-xs ${c.user_reaction === "up" ? "text-emerald-400" : "text-slate-500 hover:text-emerald-400"}`}
                    >
                      <ThumbsUp className="h-3 w-3" /> {c.upvotes}
                    </button>
                    <button
                      onClick={() => handleReact(c.id, "down")}
                      className={`flex items-center gap-1 text-xs ${c.user_reaction === "down" ? "text-rose-400" : "text-slate-500 hover:text-rose-400"}`}
                    >
                      <ThumbsDown className="h-3 w-3" /> {c.downvotes}
                    </button>
                    {user && c.username.startsWith(user.username?.slice(0, 3) ?? "___") && (
                      <button
                        onClick={() => handleDelete(c.id)}
                        className="ml-auto text-xs text-slate-600 hover:text-rose-400"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}

          {hasMore && (
            <button
              onClick={() => load()}
              disabled={loading}
              className="text-xs text-slate-400 hover:text-emerald-400 disabled:opacity-40"
            >
              {loading ? "Loading…" : "Load more"}
            </button>
          )}

          <p className="text-xs text-slate-600">
            Comments are moderated. Be respectful and constructive.
          </p>

          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
}
