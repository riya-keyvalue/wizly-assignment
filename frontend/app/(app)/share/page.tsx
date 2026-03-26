"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Plus, X } from "lucide-react";
import { shareApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/components/ui/toast";
import ShareLinkManager from "@/components/ShareLinkManager";

export default function SharePage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const [showForm, setShowForm] = useState(false);
  const [label, setLabel] = useState("");
  const [expiresAt, setExpiresAt] = useState("");
  const [creating, setCreating] = useState(false);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      await shareApi.createLink({
        label: label.trim() || undefined,
        expires_at: expiresAt || undefined,
      });
      queryClient.invalidateQueries({ queryKey: ["share-links"] });
      toast("Share link generated.", "success");
      setLabel("");
      setExpiresAt("");
      setShowForm(false);
    } catch {
      toast("Failed to generate link. Please try again.", "error");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
          Share your knowledge base
        </h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Generate secure links so external users can chat with your publicly
          published documents — without needing an account.
        </p>
      </div>

      {/* Generate link CTA / form */}
      <div className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        {!showForm ? (
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">
                Generate a shareable link
              </h2>
              <p className="mt-0.5 text-xs text-zinc-400 dark:text-zinc-500">
                Anyone with the link can query your globally published documents.
              </p>
            </div>
            <Button
              onClick={() => setShowForm(true)}
              className="shrink-0 gap-1.5"
            >
              <Plus className="h-4 w-4" />
              New link
            </Button>
          </div>
        ) : (
          <form onSubmit={handleGenerate} className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">
                New shareable link
              </h2>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="rounded-md p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-800 dark:hover:text-zinc-300 transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="link-label" className="text-xs font-medium">
                  Label{" "}
                  <span className="text-zinc-400">(optional)</span>
                </Label>
                <Input
                  id="link-label"
                  placeholder="e.g. Marketing team"
                  value={label}
                  onChange={(e) => setLabel(e.target.value)}
                  maxLength={128}
                  className="text-sm"
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="link-expiry" className="text-xs font-medium">
                  Expires at{" "}
                  <span className="text-zinc-400">(optional)</span>
                </Label>
                <Input
                  id="link-expiry"
                  type="datetime-local"
                  value={expiresAt}
                  onChange={(e) => setExpiresAt(e.target.value)}
                  className="text-sm"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowForm(false)}
                className="text-sm"
              >
                Cancel
              </Button>
              <Button type="submit" disabled={creating} className="gap-1.5 text-sm">
                <Plus className="h-4 w-4" />
                {creating ? "Generating…" : "Generate link"}
              </Button>
            </div>
          </form>
        )}
      </div>

      {/* Active links */}
      <div>
        <h2 className="mb-3 text-sm font-semibold text-zinc-700 dark:text-zinc-300">
          Your links
        </h2>
        <ShareLinkManager />
      </div>
    </div>
  );
}
