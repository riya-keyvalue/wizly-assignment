export type ChatMode = "playground" | "ai_twin";

export function parseChatMode(value: string | undefined): ChatMode {
  return value === "ai_twin" ? "ai_twin" : "playground";
}
