"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Trash2, FileText } from "lucide-react";
import { documentsApi } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";

interface Document {
  id: string;
  filename: string;
  visibility: "global" | "private";
  chunk_count: number;
  created_at: string;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function DocumentList() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const { data, isLoading, error } = useQuery<Document[]>({
    queryKey: ["documents"],
    queryFn: async () => {
      const res = await documentsApi.list();
      return res.data.data;
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => documentsApi.delete(id),
    onMutate: async (deletedId) => {
      await queryClient.cancelQueries({ queryKey: ["documents"] });
      const previous = queryClient.getQueryData<Document[]>(["documents"]);
      queryClient.setQueryData<Document[]>(["documents"], (old) =>
        old?.filter((d) => d.id !== deletedId) ?? []
      );
      return { previous };
    },
    onSuccess: (_data, _id, context) => {
      const removed = (context as { previous?: Document[] })?.previous?.find(
        (d) => d.id === _id
      );
      toast(
        removed ? `"${removed.filename}" deleted.` : "Document deleted.",
        "success"
      );
    },
    onError: (_err, _id, context) => {
      if (context?.previous) {
        queryClient.setQueryData(["documents"], context.previous);
      }
      toast("Failed to delete document. Please try again.", "error");
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });

  const handleDelete = (doc: Document) => {
    if (!window.confirm(`Delete "${doc.filename}"? This cannot be undone.`)) return;
    deleteMutation.mutate(doc.id);
  };

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-16 w-full rounded-lg" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400">
        Failed to load documents. Please refresh.
      </div>
    );
  }

  if (!data?.length) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-zinc-300 py-14 text-center dark:border-zinc-700">
        <FileText className="mb-3 h-8 w-8 text-zinc-300 dark:text-zinc-600" />
        <p className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
          No documents yet
        </p>
        <p className="mt-1 text-xs text-zinc-400 dark:text-zinc-500">
          Upload a PDF above to get started
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {data.map((doc) => (
        <div
          key={doc.id}
          className="flex items-center justify-between rounded-lg border border-zinc-200 bg-white px-4 py-3 dark:border-zinc-800 dark:bg-zinc-900"
        >
          <div className="flex items-center gap-3 min-w-0">
            <FileText className="h-5 w-5 shrink-0 text-zinc-400" />
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-zinc-900 dark:text-zinc-50">
                {doc.filename}
              </p>
              <p className="text-xs text-zinc-500 dark:text-zinc-400">
                {doc.chunk_count} chunks · {formatDate(doc.created_at)}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 ml-4 shrink-0">
            <Badge variant={doc.visibility === "global" ? "success" : "secondary"}>
              {doc.visibility}
            </Badge>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-zinc-400 hover:text-red-500"
              onClick={() => handleDelete(doc)}
              disabled={deleteMutation.isPending}
              title="Delete document"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      ))}
    </div>
  );
}
