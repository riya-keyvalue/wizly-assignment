"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { MessageSquare, Plus, Loader2 } from "lucide-react";
import { conversationsApi } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Conversation {
  id: string;
  title: string | null;
  session_id: string;
  created_at: string;
}

interface SidebarProps {
  activeId?: string;
  onSelect?: (id: string) => void;
  isOpen: boolean;
  onClose: () => void;
}

export default function Sidebar({ activeId, onSelect, isOpen, onClose }: SidebarProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const overlayRef = useRef<HTMLDivElement>(null);

  const { data: conversations, isLoading } = useQuery<Conversation[]>({
    queryKey: ["conversations"],
    queryFn: async () => {
      const res = await conversationsApi.list();
      return res.data.data;
    },
  });

  const createMutation = useMutation({
    mutationFn: () => conversationsApi.create(),
    onSuccess: (res) => {
      const id = res.data.data.id;
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      onSelect?.(id);
      onClose();
      router.push(`/chat?id=${id}`);
    },
  });

  // Close on overlay click (mobile)
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (overlayRef.current === e.target) onClose();
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [onClose]);

  const sidebarContent = (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-zinc-200 dark:border-zinc-800">
        <span className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">
          Conversations
        </span>
        <button
          onClick={() => createMutation.mutate()}
          disabled={createMutation.isPending}
          className="inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium bg-zinc-900 text-white hover:bg-zinc-700 disabled:opacity-50 dark:bg-zinc-50 dark:text-zinc-900 dark:hover:bg-zinc-200 transition-colors"
          title="New chat"
        >
          {createMutation.isPending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Plus className="h-3.5 w-3.5" />
          )}
          New chat
        </button>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
        {isLoading ? (
          <div className="space-y-1.5 p-2">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-9 rounded-lg bg-zinc-100 dark:bg-zinc-800 animate-pulse"
              />
            ))}
          </div>
        ) : !conversations?.length ? (
          <div className="flex flex-col items-center justify-center py-10 text-center">
            <MessageSquare className="h-6 w-6 text-zinc-300 dark:text-zinc-600 mb-2" />
            <p className="text-xs text-zinc-400 dark:text-zinc-500">No conversations yet</p>
          </div>
        ) : (
          conversations.map((conv) => (
            <button
              key={conv.id}
              onClick={() => {
                onSelect?.(conv.id);
                onClose();
                router.push(`/chat?id=${conv.id}`);
              }}
              className={cn(
                "w-full rounded-lg px-3 py-2 text-left text-sm transition-colors",
                activeId === conv.id
                  ? "bg-zinc-900 text-white dark:bg-zinc-50 dark:text-zinc-900 font-medium"
                  : "text-zinc-700 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-800"
              )}
            >
              <span className="block truncate">
                {conv.title ?? "New conversation"}
              </span>
            </button>
          ))
        )}
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden md:flex w-64 shrink-0 flex-col border-r border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
        {sidebarContent}
      </aside>

      {/* Mobile drawer */}
      {isOpen && (
        <div
          ref={overlayRef}
          className="fixed inset-0 z-50 flex md:hidden"
          style={{ backgroundColor: "rgba(0,0,0,0.4)" }}
        >
          <aside className="w-72 flex flex-col bg-white dark:bg-zinc-900 h-full shadow-xl">
            {sidebarContent}
          </aside>
        </div>
      )}
    </>
  );
}
