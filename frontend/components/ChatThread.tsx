"use client";

import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import SourcePanel from "@/components/SourcePanel";
import type { ChatMessage } from "@/lib/hooks/useStreamingChat";

interface ChatThreadProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  /** Replaces the default subtitle under “Ask your first question”. */
  emptyDescription?: string;
}

export default function ChatThread({
  messages,
  isStreaming,
  emptyDescription = "Start a conversation about the documents you've uploaded.",
}: ChatThreadProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Smooth scroll to bottom on new content
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (!messages.length) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center text-center px-4">
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-zinc-100 dark:bg-zinc-800">
          <svg
            className="h-7 w-7 text-zinc-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z"
            />
          </svg>
        </div>
        <p className="text-base font-medium text-zinc-700 dark:text-zinc-300">
          Ask your first question
        </p>
        <p className="mt-1.5 max-w-sm text-sm text-zinc-400 dark:text-zinc-500">
          {emptyDescription}
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col overflow-y-auto px-4 py-6 space-y-6">
      {messages.map((msg) => (
        <div
          key={msg.id}
          className={cn(
            "flex",
            msg.role === "user" ? "justify-end" : "justify-start"
          )}
        >
          <div
            className={cn(
              "max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed",
              msg.role === "user"
                ? "bg-zinc-900 text-white dark:bg-zinc-50 dark:text-zinc-900 rounded-br-sm"
                : "bg-white border border-zinc-200 text-zinc-800 dark:bg-zinc-900 dark:border-zinc-700 dark:text-zinc-100 rounded-bl-sm"
            )}
          >
            {msg.role === "assistant" ? (
              <>
                <div className="prose prose-sm prose-zinc dark:prose-invert max-w-none">
                  <ReactMarkdown>{msg.content || " "}</ReactMarkdown>
                </div>
                {msg.streaming && (
                  <span className="mt-1 inline-flex items-center gap-1 text-xs text-zinc-400">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    Generating…
                  </span>
                )}
                {!msg.streaming && msg.sources && msg.sources.length > 0 && (
                  <SourcePanel sources={msg.sources} />
                )}
              </>
            ) : (
              <p className="whitespace-pre-wrap">{msg.content}</p>
            )}
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
