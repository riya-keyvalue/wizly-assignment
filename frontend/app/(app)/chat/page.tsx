"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Menu, AlertCircle, X } from "lucide-react";
import Sidebar from "@/components/Sidebar";
import ChatThread from "@/components/ChatThread";
import ChatInput from "@/components/ChatInput";
import { useStreamingChat } from "@/lib/hooks/useStreamingChat";
import { conversationsApi } from "@/lib/api";
import type { ChatMode } from "@/lib/chatMode";
import { parseChatMode } from "@/lib/chatMode";
import { cn } from "@/lib/utils";

interface ConversationRow {
  id: string;
  title: string | null;
  session_id: string;
  created_at: string;
  chat_mode?: string;
}

interface ConversationDetail extends ConversationRow {
  chat_mode: string;
}

export default function ChatPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const conversationId = searchParams.get("id");

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [draftMode, setDraftMode] = useState<ChatMode>("playground");

  const { data: activeConversation } = useQuery({
    queryKey: ["conversation", conversationId],
    queryFn: async () => {
      const res = await conversationsApi.get(conversationId!);
      return res.data.data as ConversationDetail;
    },
    enabled: Boolean(conversationId),
    placeholderData: (): ConversationDetail | undefined => {
      const list = queryClient.getQueryData<ConversationRow[]>([
        "conversations",
      ]);
      const row = list?.find((c) => c.id === conversationId);
      if (!row || row.chat_mode == null) return undefined;
      return {
        id: row.id,
        title: row.title,
        session_id: row.session_id,
        created_at: row.created_at,
        chat_mode: row.chat_mode,
      };
    },
  });

  /** Mode used for this thread (API / streaming). When there is no open thread, follows the toggle. */
  const activeMode: ChatMode = useMemo(() => {
    if (!conversationId) return draftMode;
    const raw = activeConversation?.chat_mode;
    if (raw != null) return parseChatMode(raw);
    const fromList = queryClient
      .getQueryData<ConversationRow[]>(["conversations"])
      ?.find((c) => c.id === conversationId)?.chat_mode;
    if (fromList != null) return parseChatMode(fromList);
    return draftMode;
  }, [conversationId, draftMode, activeConversation?.chat_mode, queryClient]);

  const globalDocsOnly = activeMode === "ai_twin";

  const {
    messages,
    isStreaming,
    error,
    sendMessage,
    loadHistory,
    clearMessages,
    setError,
  } = useStreamingChat(conversationId, globalDocsOnly);

  useEffect(() => {
    if (conversationId) {
      clearMessages();
      loadHistory(conversationId);
    } else {
      clearMessages();
    }
  }, [conversationId]);

  useEffect(() => {
    if (!conversationId) return;
    const raw = activeConversation?.chat_mode;
    if (raw == null) return;
    setDraftMode(parseChatMode(raw));
  }, [conversationId, activeConversation?.chat_mode]);

  const handleModeChange = useCallback((next: ChatMode) => {
    setDraftMode(next);
  }, []);

  const handleSend = useCallback(
    async (text: string) => {
      if (!conversationId) {
        try {
          const res = await conversationsApi.create({
            chat_mode: draftMode,
          });
          const id = res.data.data.id as string;
          queryClient.invalidateQueries({ queryKey: ["conversations"] });
          queryClient.setQueryData(["conversation", id], res.data.data);
          router.push(`/chat?id=${id}`);
        } catch {
          setError("Failed to create conversation.");
        }
        return;
      }
      sendMessage(text);
    },
    [
      conversationId,
      router,
      sendMessage,
      setError,
      draftMode,
      queryClient,
    ]
  );

  return (
    <div className="flex flex-1 overflow-hidden">
      <Sidebar
        activeId={conversationId ?? undefined}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        chatModeForNew={draftMode}
      />

      <div className="flex flex-1 flex-col overflow-hidden min-w-0">
        <div className="flex items-center gap-3 border-b border-zinc-200 px-4 py-3 md:hidden dark:border-zinc-800 bg-white dark:bg-zinc-900">
          <button
            onClick={() => setSidebarOpen(true)}
            className="rounded-lg p-1.5 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
          >
            <Menu className="h-5 w-5 text-zinc-600 dark:text-zinc-400" />
          </button>
          <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300 truncate">
            {conversationId ? "Conversation" : "New Chat"}
          </span>
        </div>

        {error && (
          <div className="flex items-center gap-2 border-b border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span className="flex-1">{error}</span>
            <button onClick={() => setError(null)}>
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        <div
          className={cn(
            "flex flex-1 flex-col min-h-0 overflow-hidden w-full mx-auto border-l-[3px] transition-[border-color] duration-200",
            activeMode === "playground" &&
              "border-l-violet-500 dark:border-l-violet-400",
            activeMode === "ai_twin" &&
              "border-l-emerald-500 dark:border-l-emerald-400"
          )}
        >
          <div
            className={cn(
              "shrink-0 flex flex-col items-center gap-1 border-b px-4 py-2.5 transition-colors duration-200",
              activeMode === "playground" &&
                "border-violet-200 bg-gradient-to-b from-violet-50 to-violet-50/30 dark:border-violet-800/70 dark:from-violet-950/50 dark:to-violet-950/20",
              activeMode === "ai_twin" &&
                "border-emerald-200 bg-gradient-to-b from-emerald-50 to-emerald-50/30 dark:border-emerald-800/70 dark:from-emerald-950/50 dark:to-emerald-950/20"
            )}
          >
            <div
              className={cn(
                "inline-flex rounded-lg border p-0.5 shadow-sm",
                draftMode === "playground" &&
                  "border-violet-200/90 bg-violet-100/80 dark:border-violet-700 dark:bg-violet-900/50",
                draftMode === "ai_twin" &&
                  "border-emerald-200/90 bg-emerald-100/80 dark:border-emerald-700 dark:bg-emerald-900/50"
              )}
              role="group"
              aria-label="Chat mode"
            >
              <button
                type="button"
                onClick={() => handleModeChange("playground")}
                className={cn(
                  "rounded-md px-3 py-1.5 text-xs font-semibold transition-all duration-200",
                  draftMode === "playground"
                    ? "bg-violet-600 text-white shadow-md shadow-violet-600/25 dark:bg-violet-500 dark:shadow-violet-500/20"
                    : "text-violet-800/70 hover:bg-violet-200/50 hover:text-violet-900 dark:text-violet-300/80 dark:hover:bg-violet-800/40 dark:hover:text-violet-100"
                )}
              >
                Playground
              </button>
              <button
                type="button"
                onClick={() => handleModeChange("ai_twin")}
                className={cn(
                  "rounded-md px-3 py-1.5 text-xs font-semibold transition-all duration-200",
                  draftMode === "ai_twin"
                    ? "bg-emerald-600 text-white shadow-md shadow-emerald-600/25 dark:bg-emerald-500 dark:shadow-emerald-500/20"
                    : "text-emerald-800/70 hover:bg-emerald-200/50 hover:text-emerald-900 dark:text-emerald-300/80 dark:hover:bg-emerald-800/40 dark:hover:text-emerald-100"
                )}
              >
                AI Twin
              </button>
            </div>
            <p
              className={cn(
                "text-[10px] font-medium uppercase tracking-wide",
                activeMode === "playground" &&
                  "text-violet-600/90 dark:text-violet-400",
                activeMode === "ai_twin" &&
                  "text-emerald-700/90 dark:text-emerald-400"
              )}
            >
              {activeMode === "playground"
                ? "Private & global documents"
                : "Global published only"}
            </p>
            {conversationId && draftMode !== activeMode && (
              <p className="text-[10px] text-zinc-500 dark:text-zinc-400 text-center max-w-xs">
                This chat uses {activeMode === "ai_twin" ? "AI Twin" : "Playground"}.
                New chats from the sidebar will use{" "}
                {draftMode === "ai_twin" ? "AI Twin" : "Playground"}.
              </p>
            )}
          </div>

          <div
            className={cn(
              "flex min-h-0 flex-1 flex-col transition-colors duration-200",
              activeMode === "playground" &&
                "bg-violet-50/25 dark:bg-violet-950/10",
              activeMode === "ai_twin" &&
                "bg-emerald-50/25 dark:bg-emerald-950/10"
            )}
          >
            <ChatThread
              messages={messages}
              isStreaming={isStreaming}
              emptyDescription={
                activeMode === "ai_twin"
                  ? "Questions use only your globally published documents — the same scope as share links."
                  : "Start a conversation about the documents you've uploaded."
              }
            />
          </div>

          <ChatInput
            onSend={handleSend}
            disabled={isStreaming}
            accent={activeMode === "playground" ? "playground" : "ai_twin"}
            footnote={
              activeMode === "ai_twin"
                ? "Answers grounded in your globally published documents only."
                : "Answers grounded in your uploaded documents."
            }
          />
        </div>
      </div>
    </div>
  );
}
