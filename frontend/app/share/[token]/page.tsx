"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { AlertCircle, Bot } from "lucide-react";
import { publicShareApi } from "@/lib/api";
import { useSharedStreamingChat } from "@/lib/hooks/useSharedStreamingChat";
import ChatThread from "@/components/ChatThread";
import ChatInput from "@/components/ChatInput";

interface LinkInfo {
  owner_email: string;
  label: string | null;
}

export default function SharedChatPage() {
  const params = useParams();
  const token = params?.token as string;

  const [linkInfo, setLinkInfo] = useState<LinkInfo | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [initialising, setInitialising] = useState(true);

  const { messages, isStreaming, error, sendMessage, setError } =
    useSharedStreamingChat(token, conversationId);

  useEffect(() => {
    if (!token) return;

    const init = async () => {
      try {
        const infoRes = await publicShareApi.getLink(token);
        const info: LinkInfo = infoRes.data.data;
        setLinkInfo(info);

        const convRes = await publicShareApi.createConversation(token);
        setConversationId(convRes.data.data.id as string);
      } catch {
        setNotFound(true);
      } finally {
        setInitialising(false);
      }
    };

    init();
  }, [token]);

  if (initialising) {
    return (
      <div className="flex h-screen items-center justify-center bg-zinc-50 dark:bg-zinc-950">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-300 border-t-zinc-700 dark:border-zinc-700 dark:border-t-zinc-300" />
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-4 px-4 text-center bg-zinc-50 dark:bg-zinc-950">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/30">
          <AlertCircle className="h-7 w-7 text-red-500" />
        </div>
        <div>
          <h1 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
            Link not found or expired
          </h1>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
            This share link may have been revoked or does not exist.
          </p>
        </div>
        <Link
          href="/register"
          className="mt-2 rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-700 transition-colors dark:bg-zinc-50 dark:text-zinc-900 dark:hover:bg-zinc-200"
        >
          Create your own AI Twin
        </Link>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col bg-zinc-50 dark:bg-zinc-950">
      {/* Guest header */}
      <header className="shrink-0 border-b border-zinc-200 bg-white px-4 dark:border-zinc-800 dark:bg-zinc-900">
        <div className="mx-auto flex h-14 max-w-3xl items-center gap-3">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-zinc-100 dark:bg-zinc-800">
            <Bot className="h-4 w-4 text-zinc-600 dark:text-zinc-400" />
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-zinc-900 dark:text-zinc-50">
              {linkInfo?.label
                ? linkInfo.label
                : `${linkInfo?.owner_email ?? ""}'s knowledge base`}
            </p>
            {linkInfo?.label && (
              <p className="truncate text-xs text-zinc-400 dark:text-zinc-500">
                Shared by {linkInfo.owner_email}
              </p>
            )}
          </div>
        </div>
      </header>

      {/* Chat area */}
      <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col overflow-hidden">
        <div className="flex flex-1 flex-col overflow-hidden">
          <ChatThread messages={messages} isStreaming={isStreaming} />
        </div>

        {error && (
          <div className="mx-4 mb-2 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600 dark:border-red-800 dark:bg-red-950/30 dark:text-red-400">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" />
            <span className="flex-1">{error}</span>
            <button
              onClick={() => setError(null)}
              className="ml-auto text-xs underline hover:no-underline"
            >
              Dismiss
            </button>
          </div>
        )}

        <ChatInput onSend={sendMessage} disabled={isStreaming} />
      </div>

      {/* Footer */}
      <footer className="shrink-0 border-t border-zinc-200 bg-white py-2 text-center dark:border-zinc-800 dark:bg-zinc-900">
        <p className="text-xs text-zinc-400 dark:text-zinc-500">
          Powered by AI Twin &middot;{" "}
          <Link
            href="/register"
            className="underline hover:no-underline hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors"
          >
            Create your own
          </Link>
        </p>
      </footer>
    </div>
  );
}
