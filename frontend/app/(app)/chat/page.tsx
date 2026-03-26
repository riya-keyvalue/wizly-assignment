"use client";

import { useEffect, useState, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Menu, AlertCircle, X } from "lucide-react";
import Sidebar from "@/components/Sidebar";
import ChatThread from "@/components/ChatThread";
import ChatInput from "@/components/ChatInput";
import { useStreamingChat, type ChatMessage } from "@/lib/hooks/useStreamingChat";
import { conversationsApi } from "@/lib/api";

export default function ChatPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const conversationId = searchParams.get("id");

  const [sidebarOpen, setSidebarOpen] = useState(false);

  const {
    messages,
    isStreaming,
    error,
    sendMessage,
    loadHistory,
    clearMessages,
    setError,
  } = useStreamingChat(conversationId);

  // Load history when conversation changes
  useEffect(() => {
    if (conversationId) {
      clearMessages();
      loadHistory(conversationId);
    } else {
      clearMessages();
    }
  }, [conversationId]);

  const handleSend = useCallback(
    async (text: string) => {
      if (!conversationId) {
        // No conversation selected — create one first
        try {
          const res = await conversationsApi.create();
          const id = res.data.data.id as string;
          router.push(`/chat?id=${id}`);
          // sendMessage will be re-triggered after navigation + useEffect
        } catch {
          setError("Failed to create conversation.");
        }
        return;
      }
      sendMessage(text);
    },
    [conversationId, router, sendMessage, setError]
  );

  return (
    <div className="flex h-full overflow-hidden">
      {/* Conversation list sidebar */}
      <Sidebar
        activeId={conversationId ?? undefined}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Main chat area */}
      <div className="flex flex-1 flex-col overflow-hidden min-w-0">
        {/* Mobile top bar */}
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

        {/* Error banner */}
        {error && (
          <div className="flex items-center gap-2 border-b border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span className="flex-1">{error}</span>
            <button onClick={() => setError(null)}>
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Messages */}
        <ChatThread messages={messages} isStreaming={isStreaming} />

        {/* Input */}
        <ChatInput onSend={handleSend} disabled={isStreaming} />
      </div>
    </div>
  );
}
