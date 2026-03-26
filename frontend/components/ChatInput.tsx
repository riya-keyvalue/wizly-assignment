"use client";

import { useRef, useCallback, KeyboardEvent } from "react";
import { SendHorizonal } from "lucide-react";
import { cn } from "@/lib/utils";

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled?: boolean;
}

export default function ChatInput({ onSend, disabled }: ChatInputProps) {
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
    <div className="border-t border-zinc-200 bg-white px-4 py-3 dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex items-end gap-2 rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 focus-within:border-zinc-400 dark:border-zinc-700 dark:bg-zinc-800 dark:focus-within:border-zinc-500 transition-colors">
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
            disabled
              ? "text-zinc-300 dark:text-zinc-600 cursor-not-allowed"
              : "bg-zinc-900 text-white hover:bg-zinc-700 dark:bg-zinc-50 dark:text-zinc-900 dark:hover:bg-zinc-200"
          )}
          title="Send message"
        >
          <SendHorizonal className="h-4 w-4" />
        </button>
      </div>
      <p className="mt-1.5 text-center text-xs text-zinc-400 dark:text-zinc-500">
        Answers grounded in your uploaded documents.
      </p>
    </div>
  );
}
