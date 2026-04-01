"use client";

import { useRef, useCallback, KeyboardEvent } from "react";
import { SendHorizonal } from "lucide-react";
import { cn } from "@/lib/utils";

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled?: boolean;
  /** Shown below the input; defaults to private + global docs hint. */
  footnote?: string;
  /** When set, tints borders and send control to match chat mode. */
  accent?: "playground" | "ai_twin";
}

export default function ChatInput({
  onSend,
  disabled,
  footnote = "Answers grounded in your uploaded documents.",
  accent,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const resize = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, []);

  const handleSend = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    const text = el.value.trim();
    if (!text || disabled) return;
    onSend(text);
    el.value = "";
    el.style.height = "auto";
  }, [onSend, disabled]);

  const handleKey = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  return (
    <div
      className={cn(
        "border-t bg-white px-4 py-3 dark:bg-zinc-900 transition-colors",
        accent === "playground" &&
          "border-violet-200 dark:border-violet-800/80 bg-violet-50/40 dark:bg-violet-950/20",
        accent === "ai_twin" &&
          "border-emerald-200 dark:border-emerald-800/80 bg-emerald-50/40 dark:bg-emerald-950/20",
        !accent && "border-zinc-200 dark:border-zinc-800"
      )}
    >
      <div
        className={cn(
          "flex items-end gap-2 rounded-xl border bg-zinc-50 px-3 py-2 transition-colors dark:bg-zinc-800",
          accent === "playground" &&
            "border-violet-200 focus-within:border-violet-400 focus-within:ring-1 focus-within:ring-violet-400/30 dark:border-violet-700 dark:focus-within:border-violet-500 dark:focus-within:ring-violet-500/25",
          accent === "ai_twin" &&
            "border-emerald-200 focus-within:border-emerald-400 focus-within:ring-1 focus-within:ring-emerald-400/30 dark:border-emerald-700 dark:focus-within:border-emerald-500 dark:focus-within:ring-emerald-500/25",
          !accent &&
            "border-zinc-200 focus-within:border-zinc-400 dark:border-zinc-700 dark:focus-within:border-zinc-500"
        )}
      >
        <textarea
          ref={textareaRef}
          rows={1}
          placeholder={
            disabled ? "Generating response…" : "Ask a question… (Enter to send, Shift+Enter for newline)"
          }
          disabled={disabled}
          onChange={resize}
          onKeyDown={handleKey}
          className={cn(
            "flex-1 resize-none bg-transparent text-sm text-zinc-900 placeholder:text-zinc-400",
            "focus:outline-none dark:text-zinc-50 dark:placeholder:text-zinc-500",
            "disabled:cursor-not-allowed disabled:opacity-50",
            "max-h-[200px] py-1 leading-relaxed"
          )}
        />
        <button
          onClick={handleSend}
          disabled={disabled}
          className={cn(
            "mb-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg transition-colors",
            disabled && "text-zinc-300 dark:text-zinc-600 cursor-not-allowed",
            !disabled &&
              !accent &&
              "bg-zinc-900 text-white hover:bg-zinc-700 dark:bg-zinc-50 dark:text-zinc-900 dark:hover:bg-zinc-200",
            !disabled &&
              accent === "playground" &&
              "bg-violet-600 text-white hover:bg-violet-700 dark:bg-violet-600 dark:hover:bg-violet-500",
            !disabled &&
              accent === "ai_twin" &&
              "bg-emerald-600 text-white hover:bg-emerald-700 dark:bg-emerald-600 dark:hover:bg-emerald-500"
          )}
          title="Send message"
        >
          <SendHorizonal className="h-4 w-4" />
        </button>
      </div>
      <p
        className={cn(
          "mt-1.5 text-center text-xs",
          accent === "playground" && "text-violet-700/80 dark:text-violet-300/90",
          accent === "ai_twin" && "text-emerald-800/80 dark:text-emerald-300/90",
          !accent && "text-zinc-400 dark:text-zinc-500"
        )}
      >
        {footnote}
      </p>
    </div>
  );
}
