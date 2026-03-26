"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { FileText, LogOut, MessageSquare, Share2 } from "lucide-react";
import { useAuthStore } from "@/lib/store";
import { authApi } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { accessToken, clearAuth } = useAuthStore();

  useEffect(() => {
    if (!accessToken) {
      router.replace("/login");
    }
  }, [accessToken, router]);

  if (!accessToken) return null;

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch {
      // ignore — token may already be expired
    } finally {
      clearAuth();
      router.replace("/login");
    }
  };

  const isChat = pathname?.startsWith("/chat");
  const isShare = pathname?.startsWith("/share");

  return (
    <div className={cn("flex flex-col", isChat ? "h-screen" : "min-h-screen")}>
      {/* Top nav */}
      <header className="shrink-0 sticky top-0 z-40 border-b border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
        <div className="mx-auto flex h-14 max-w-none items-center justify-between px-4">
          <Link
            href="/chat"
            className="text-lg font-bold tracking-tight text-zinc-900 dark:text-zinc-50"
          >
            AI Twin
          </Link>
          <nav className="flex items-center gap-1">
            <Link
              href="/chat"
              className={cn(
                "inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
                pathname?.startsWith("/chat")
                  ? "bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-50"
                  : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
              )}
            >
              <MessageSquare className="h-4 w-4" />
              Chat
            </Link>
            <Link
              href="/documents"
              className={cn(
                "inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
                pathname?.startsWith("/documents")
                  ? "bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-50"
                  : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
              )}
            >
              <FileText className="h-4 w-4" />
              Documents
            </Link>
            <Link
              href="/share"
              className={cn(
                "inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
                isShare
                  ? "bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-50"
                  : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
              )}
            >
              <Share2 className="h-4 w-4" />
              Share
            </Link>
            <button
              onClick={handleLogout}
              className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
            >
              <LogOut className="h-4 w-4" />
              Sign out
            </button>
          </nav>
        </div>
      </header>

      {/* Page content */}
      {isChat ? (
        <div className="flex flex-1 overflow-hidden">{children}</div>
      ) : (
        <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">
          {children}
        </main>
      )}
    </div>
  );
}
