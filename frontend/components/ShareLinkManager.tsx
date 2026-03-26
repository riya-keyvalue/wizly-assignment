"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Copy, Link2, Trash2, ToggleLeft, ToggleRight, AlertCircle } from "lucide-react";
import { shareApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/utils";

interface ShareLink {
  id: string;
  token: string;
  label: string | null;
  is_active: boolean;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

const FRONTEND_URL =
  typeof window !== "undefined"
    ? window.location.origin
    : process.env.NEXT_PUBLIC_FRONTEND_URL || "http://localhost:3000";

function buildShareUrl(token: string) {
  return `${FRONTEND_URL}/share/${token}`;
}

function CopyButton({ token }: { token: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(buildShareUrl(token));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback: select the input manually
    }
  };

  return (
    <button
      onClick={handleCopy}
      className="shrink-0 rounded-md p-1.5 text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900 dark:hover:bg-zinc-700 dark:hover:text-zinc-100 transition-colors"
      title="Copy link"
    >
      {copied ? (
        <Check className="h-4 w-4 text-emerald-500" />
      ) : (
        <Copy className="h-4 w-4" />
      )}
    </button>
  );
}

interface LinkRowProps {
  link: ShareLink;
  onToggle: (token: string, is_active: boolean) => Promise<void>;
  onDelete: (token: string) => Promise<void>;
}

function LinkRow({ link, onToggle, onDelete }: LinkRowProps) {
  const [toggling, setToggling] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const handleToggle = async () => {
    setToggling(true);
    try {
      await onToggle(link.token, !link.is_active);
    } finally {
      setToggling(false);
    }
  };

  const handleDelete = async () => {
    if (!confirmDelete) {
      setConfirmDelete(true);
      setTimeout(() => setConfirmDelete(false), 3000);
      return;
    }
    setDeleting(true);
    try {
      await onDelete(link.token);
    } finally {
      setDeleting(false);
    }
  };

  const shareUrl = buildShareUrl(link.token);
  const createdDate = new Date(link.created_at).toLocaleDateString();
  const expiryDate = link.expires_at
    ? new Date(link.expires_at).toLocaleDateString()
    : null;

  return (
    <div
      className={cn(
        "rounded-xl border p-4 transition-colors",
        link.is_active
          ? "border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900"
          : "border-zinc-200 bg-zinc-50 opacity-60 dark:border-zinc-800 dark:bg-zinc-900/50"
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-sm text-zinc-900 dark:text-zinc-50 truncate">
              {link.label || "Unnamed link"}
            </span>
            <Badge
              variant={link.is_active ? "default" : "secondary"}
              className="shrink-0 text-xs"
            >
              {link.is_active ? "Active" : "Revoked"}
            </Badge>
            {expiryDate && (
              <span className="text-xs text-zinc-400 dark:text-zinc-500">
                Expires {expiryDate}
              </span>
            )}
          </div>
          <p className="mt-0.5 text-xs text-zinc-400 dark:text-zinc-500">
            Created {createdDate}
          </p>

          {/* Share URL row */}
          <div className="mt-2 flex items-center gap-1 rounded-md border border-zinc-200 bg-zinc-50 px-2 py-1 dark:border-zinc-700 dark:bg-zinc-800">
            <Link2 className="h-3.5 w-3.5 shrink-0 text-zinc-400" />
            <span className="flex-1 truncate text-xs text-zinc-500 dark:text-zinc-400 font-mono">
              {shareUrl}
            </span>
            <CopyButton token={link.token} />
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={handleToggle}
            disabled={toggling}
            className="rounded-md p-1.5 text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900 dark:hover:bg-zinc-700 dark:hover:text-zinc-100 transition-colors disabled:opacity-50"
            title={link.is_active ? "Revoke link" : "Reactivate link"}
          >
            {link.is_active ? (
              <ToggleRight className="h-4 w-4 text-emerald-500" />
            ) : (
              <ToggleLeft className="h-4 w-4" />
            )}
          </button>

          <button
            onClick={handleDelete}
            disabled={deleting}
            className={cn(
              "rounded-md p-1.5 transition-colors disabled:opacity-50",
              confirmDelete
                ? "bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400"
                : "text-zinc-400 hover:bg-zinc-100 hover:text-red-500 dark:hover:bg-zinc-700"
            )}
            title={confirmDelete ? "Click again to confirm deletion" : "Delete link"}
          >
            {confirmDelete ? (
              <AlertCircle className="h-4 w-4" />
            ) : (
              <Trash2 className="h-4 w-4" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function ShareLinkManager() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["share-links"],
    queryFn: async () => {
      const res = await shareApi.listLinks();
      return (res.data.data || []) as ShareLink[];
    },
  });

  const handleToggle = async (token: string, is_active: boolean) => {
    try {
      await shareApi.updateLink(token, { is_active });
      queryClient.invalidateQueries({ queryKey: ["share-links"] });
      toast(is_active ? "Link reactivated." : "Link revoked.", "success");
    } catch {
      toast("Failed to update link.", "error");
    }
  };

  const handleDelete = async (token: string) => {
    try {
      await shareApi.deleteLink(token);
      queryClient.invalidateQueries({ queryKey: ["share-links"] });
      toast("Link deleted.", "success");
    } catch {
      toast("Failed to delete link.", "error");
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[...Array(2)].map((_, i) => (
          <div
            key={i}
            className="h-24 animate-pulse rounded-xl border border-zinc-200 bg-zinc-100 dark:border-zinc-800 dark:bg-zinc-800"
          />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <p className="text-sm text-red-500">Failed to load share links.</p>
    );
  }

  if (!data || data.length === 0) {
    return (
      <p className="text-sm text-zinc-400 dark:text-zinc-500">
        No links yet. Generate one above to share your knowledge base.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {data.map((link) => (
        <LinkRow
          key={link.id}
          link={link}
          onToggle={handleToggle}
          onDelete={handleDelete}
        />
      ))}
    </div>
  );
}
