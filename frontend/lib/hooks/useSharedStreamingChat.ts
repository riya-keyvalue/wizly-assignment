"use client";

import { useState, useCallback, useRef } from "react";
import { publicShareApi } from "@/lib/api";
import type { ChatMessage, Source } from "@/lib/hooks/useStreamingChat";

export type { ChatMessage, Source };

export function useSharedStreamingChat(token: string, conversationId: string | null) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const loadHistory = useCallback(async (convId: string) => {
    try {
      const res = await publicShareApi.getMessages(token, convId);
      const loaded: ChatMessage[] = res.data.data.map(
        (m: { id: string; role: string; content: string; sources?: Source[] }) => ({
          id: m.id,
          role: m.role as "user" | "assistant",
          content: m.content,
          sources: m.sources ?? undefined,
        })
      );
      setMessages(loaded);
    } catch {
      setError("Failed to load conversation history.");
    }
  }, [token]);

  const sendMessage = useCallback(
    async (query: string) => {
      if (!conversationId || isStreaming || !query.trim()) return;

      setError(null);

      const userMsg: ChatMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content: query.trim(),
      };
      const assistantMsgId = `assistant-${Date.now()}`;
      const assistantMsg: ChatMessage = {
        id: assistantMsgId,
        role: "assistant",
        content: "",
        streaming: true,
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsStreaming(true);

      abortRef.current = new AbortController();
      const url = publicShareApi.streamUrl(token, conversationId, query.trim());

      try {
        const response = await fetch(url, {
          method: "GET",
          signal: abortRef.current.signal,
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const reader = response.body?.getReader();
        if (!reader) throw new Error("No response body");

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const jsonStr = line.slice(6).trim();
            if (!jsonStr) continue;

            try {
              const event = JSON.parse(jsonStr) as {
                type: string;
                content?: string;
                sources?: Source[];
              };

              if (event.type === "token" && event.content) {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMsgId
                      ? { ...m, content: m.content + event.content }
                      : m
                  )
                );
              } else if (event.type === "sources" && event.sources) {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMsgId
                      ? { ...m, sources: event.sources }
                      : m
                  )
                );
              } else if (event.type === "done") {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMsgId ? { ...m, streaming: false } : m
                  )
                );
              } else if (event.type === "error") {
                setError(event.content ?? "Unknown streaming error");
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMsgId ? { ...m, streaming: false } : m
                  )
                );
              }
            } catch {
              // malformed JSON line — skip
            }
          }
        }
      } catch (err: unknown) {
        if ((err as Error).name === "AbortError") return;
        setError("Connection lost. Please try again.");
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId ? { ...m, streaming: false } : m
          )
        );
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [token, conversationId, isStreaming]
  );

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return {
    messages,
    isStreaming,
    error,
    sendMessage,
    loadHistory,
    stopStreaming,
    setError,
  };
}
