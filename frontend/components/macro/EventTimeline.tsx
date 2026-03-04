"use client";

import useSWR from "swr";
import { getUpcomingEvents, MarketEvent } from "@/lib/api";
import { Calendar, MapPin } from "lucide-react";

export default function EventTimeline() {
    const { data, error, isLoading } = useSWR(
        "/api/v1/events/upcoming",
        () => getUpcomingEvents(),
        { revalidateOnFocus: false }
    );

    if (isLoading) {
        return (
            <div className="flex justify-center items-center py-12">
                <div className="w-8 h-8 rounded-full border-4 border-slate-700 border-t-sky-400 animate-spin" />
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-4 bg-rose-900/40 text-rose-400 rounded-xl border border-rose-800">
                <p className="font-semibold text-sm">Failed to fetch economic events.</p>
                <p className="text-xs mt-1">{error.message}</p>
            </div>
        );
    }

    const events = data?.events || [];

    if (events.length === 0) {
        return (
            <div className="p-8 text-center text-slate-400 border border-slate-800 rounded-xl bg-slate-900/30 text-sm">
                No upcoming high or medium impact events found.
            </div>
        );
    }

    // Group events by date
    const groupedEvents = events.reduce((acc, event) => {
        const date = event.date;
        if (!acc[date]) acc[date] = [];
        acc[date].push(event);
        return acc;
    }, {} as Record<string, MarketEvent[]>);

    const formatDate = (dateString: string) => {
        // Treat as UTC to avoid timezone shifting
        const date = new Date(dateString + 'T00:00:00Z');
        return new Intl.DateTimeFormat('en-US', { weekday: 'long', month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' }).format(date);
    };

    return (
        <div className="space-y-6">
            <div className="relative border-l border-slate-800 ml-3 space-y-6 pb-2">
                {Object.entries(groupedEvents).map(([date, dayEvents]) => (
                    <div key={date} className="relative">
                        <div className="absolute -left-3.5 mt-1.5 w-7 h-7 bg-slate-950 rounded-full border border-slate-700 flex items-center justify-center">
                            <Calendar className="w-3.5 h-3.5 text-sky-400" />
                        </div>
                        <div className="pl-8">
                            <h3 className="text-sm font-semibold mb-3 text-slate-200">
                                {formatDate(date)}
                            </h3>

                            <div className="space-y-3">
                                {dayEvents.map((event) => (
                                    <div
                                        key={event.id}
                                        className={`p-4 rounded-xl border bg-slate-950/60 shadow-sm ${event.impact === "High" ? "border-l-4 border-l-rose-500" :
                                                event.impact === "Medium" ? "border-l-4 border-l-amber-500" : "border-slate-800 border-l-4 border-l-sky-500"
                                            }`}
                                    >
                                        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                                            <div className="space-y-1">
                                                <div className="flex flex-wrap items-center gap-2">
                                                    <span className="font-semibold text-sm text-slate-100">{event.title}</span>
                                                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${event.impact === "High" ? "bg-rose-900/30 text-rose-400 border border-rose-800/50" :
                                                            event.impact === "Medium" ? "bg-amber-900/30 text-amber-400 border border-amber-800/50" :
                                                                "bg-sky-900/30 text-sky-400 border border-sky-800/50"
                                                        }`}>
                                                        {event.impact} Impact
                                                    </span>
                                                </div>
                                                {event.description && (
                                                    <p className="text-xs text-slate-400 pt-1 leading-relaxed">{event.description}</p>
                                                )}
                                                <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-500 pt-2">
                                                    <span className="flex items-center gap-1 font-medium bg-slate-800/50 px-2 py-1 rounded-md text-slate-300">
                                                        <MapPin className="w-3 h-3" />
                                                        {event.country}
                                                    </span>
                                                    {event.time && (
                                                        <span className="flex items-center gap-1 text-slate-400">
                                                            @ {event.time}
                                                        </span>
                                                    )}
                                                </div>
                                            </div>

                                            {/* Metric Data Table style */}
                                            {(event.estimate || event.previous || event.actual) && (
                                                <div className="grid grid-cols-2 lg:grid-cols-3 gap-2 text-xs bg-slate-900/50 p-2.5 rounded-lg border border-slate-800/50 min-w-[200px]">
                                                    {event.previous && (
                                                        <div className="flex flex-col">
                                                            <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">Prev</span>
                                                            <span className="font-medium text-slate-300 text-xs mt-0.5">{event.previous}</span>
                                                        </div>
                                                    )}
                                                    {event.estimate && (
                                                        <div className="flex flex-col">
                                                            <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">Est</span>
                                                            <span className="font-medium text-slate-300 text-xs mt-0.5">{event.estimate}</span>
                                                        </div>
                                                    )}
                                                    {event.actual && (
                                                        <div className="flex flex-col">
                                                            <span className="text-[10px] text-sky-500 uppercase tracking-wider font-semibold">Act</span>
                                                            <span className="font-bold text-sky-400 text-xs mt-0.5">{event.actual}</span>
                                                        </div>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
