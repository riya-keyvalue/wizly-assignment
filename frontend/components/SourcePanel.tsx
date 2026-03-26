"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, FileText } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Source } from "@/lib/hooks/useStreamingChat";

interface SourcePanelProps {
  sources: Source[];
}

export default function SourcePanel({ sources }: SourcePanelProps) {
  const [open, setOpen] = useState(false);

  if (!sources.length) return null;

  return (
    <div className="mt-2 rounded-lg border border-zinc-200 dark:border-zinc-700 overflow-hidden text-xs">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-3 py-2 bg-zinc-50 hover:bg-zinc-100 dark:bg-zinc-800 dark:hover:bg-zinc-700 transition-colors text-zinc-500 dark:text-zinc-400"
      >
        <span className="font-medium">
          {sources.length} source{sources.length !== 1 ? "s" : ""}
        </span>
        {open ? (
          <ChevronUp className="h-3.5 w-3.5" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5" />
        )}
      </button>

      {open && (
        <div className="divide-y divide-zinc-100 dark:divide-zinc-800">
          {sources.map((src, i) => (
            <div
              key={i}
              className="flex items-start gap-2 px-3 py-2 bg-white dark:bg-zinc-900"
            >
              <FileText className="h-3.5 w-3.5 mt-0.5 shrink-0 text-zinc-400" />
              <div>
                <p className="font-medium text-zinc-700 dark:text-zinc-300 truncate max-w-xs">
                  {src.filename}
                </p>
                <p className="text-zinc-400 dark:text-zinc-500">
                  Page {src.page}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
