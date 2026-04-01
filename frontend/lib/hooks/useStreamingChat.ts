"use client";

import { useState, useCallback, useRef } from "react";
import { conversationsApi } from "@/lib/api";

export interface Source {
  doc_id: string;
  filename: string;
  page: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  streaming?: boolean;
}

export function useStreamingChat(
  conversationId: string | null,
  globalDocsOnly: boolean = false
) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const loadHistory = useCallback(
    async (id: string, initialMessages?: ChatMessage[]) => {
      if (initialMessages) {
        setMessages(initialMessages);
        return;
      }
      try {
        const res = await conversationsApi.messages(id);
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
    },
    []
  );

  const sendMessage = useCallback(
    async (query: string) => {
      if (!conversationId || isStreaming || !query.trim()) return;

      setError(null);

      // Optimistically append user message
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
      const { url, headers } = conversationsApi.streamFetch(
        conversationId,
        query.trim(),
        { globalDocsOnly }
      );

      try {
        const response = await fetch(url, {
          method: "GET",
          headers,
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
    [conversationId, isStreaming, globalDocsOnly]
  );

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return {
    messages,
    isStreaming,
    error,
    sendMessage,
    loadHistory,
    stopStreaming,
    clearMessages,
    setError,
  };
}
