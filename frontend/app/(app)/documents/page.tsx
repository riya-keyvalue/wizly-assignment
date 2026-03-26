"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { useQueryClient } from "@tanstack/react-query";
import { UploadCloud, AlertCircle, CheckCircle2 } from "lucide-react";
import { documentsApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/utils";
import DocumentList from "@/components/DocumentList";

const MAX_SIZE_BYTES = 20 * 1024 * 1024; // 20 MB

type UploadState =
  | { status: "idle" }
  | { status: "uploading"; progress: number; filename: string }
  | { status: "success"; filename: string }
  | { status: "error"; message: string };

export default function DocumentsPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [uploadState, setUploadState] = useState<UploadState>({ status: "idle" });
  const [visibility, setVisibility] = useState<"global" | "private">("global");

  const handleUpload = async (file: File) => {
    setUploadState({ status: "uploading", progress: 0, filename: file.name });
    try {
      await documentsApi.upload(file, visibility, (pct) =>
        setUploadState({ status: "uploading", progress: pct, filename: file.name })
      );
      setUploadState({ status: "success", filename: file.name });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      toast(`"${file.name}" uploaded successfully.`, "success");
      setTimeout(() => setUploadState({ status: "idle" }), 3000);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Upload failed. Please try again.";
      setUploadState({ status: "error", message: msg });
      toast(msg, "error");
    }
  };

  const onDrop = useCallback(
    (accepted: File[], rejected: import("react-dropzone").FileRejection[]) => {
      if (rejected.length > 0) {
        const reason = rejected[0].errors[0]?.message ?? "Invalid file";
        setUploadState({ status: "error", message: reason });
        return;
      }
      if (accepted[0]) handleUpload(accepted[0]);
    },
    [visibility]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    maxSize: MAX_SIZE_BYTES,
    maxFiles: 1,
    disabled: uploadState.status === "uploading",
  });

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
          Documents
        </h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Upload PDFs to build your AI Twin&apos;s knowledge base.
        </p>
      </div>

      {/* Upload card */}
      <div className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <h2 className="mb-4 text-sm font-semibold text-zinc-700 dark:text-zinc-300">
          Upload a document
        </h2>

        {/* Visibility toggle */}
        <div className="mb-4 flex items-center gap-3">
          <span className="text-sm text-zinc-500 dark:text-zinc-400">Visibility:</span>
          <div className="flex rounded-lg border border-zinc-200 overflow-hidden dark:border-zinc-700 text-sm">
            {(["global", "private"] as const).map((v) => (
              <button
                key={v}
                onClick={() => setVisibility(v)}
                className={cn(
                  "px-3 py-1.5 capitalize font-medium transition-colors",
                  visibility === v
                    ? "bg-zinc-900 text-white dark:bg-zinc-50 dark:text-zinc-900"
                    : "bg-white text-zinc-600 hover:bg-zinc-50 dark:bg-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800"
                )}
              >
                {v}
              </button>
            ))}
          </div>
          <span className="text-xs text-zinc-400 dark:text-zinc-500">
            {visibility === "global"
              ? "Available to AI Twin for answering questions"
              : "Stored but not used by AI Twin"}
          </span>
        </div>

        {/* Dropzone */}
        <div
          {...getRootProps()}
          className={cn(
            "flex flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors cursor-pointer",
            isDragActive
              ? "border-zinc-900 bg-zinc-50 dark:border-zinc-300 dark:bg-zinc-800"
              : "border-zinc-200 hover:border-zinc-300 hover:bg-zinc-50 dark:border-zinc-700 dark:hover:border-zinc-600 dark:hover:bg-zinc-800/50",
            uploadState.status === "uploading" && "cursor-not-allowed opacity-60"
          )}
        >
          <input {...getInputProps()} />
          <UploadCloud
            className={cn(
              "mb-3 h-8 w-8",
              isDragActive ? "text-zinc-900 dark:text-zinc-100" : "text-zinc-400"
            )}
          />
          <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
            {isDragActive ? "Drop PDF here" : "Drag & drop a PDF, or click to browse"}
          </p>
          <p className="mt-1 text-xs text-zinc-400 dark:text-zinc-500">
            PDF only · max 20 MB
          </p>
        </div>

        {/* Upload progress / status */}
        {uploadState.status === "uploading" && (
          <div className="mt-4 space-y-2">
            <div className="flex items-center justify-between text-xs text-zinc-500">
              <span className="truncate max-w-xs">{uploadState.filename}</span>
              <span>{uploadState.progress}%</span>
            </div>
            <Progress value={uploadState.progress} />
          </div>
        )}

        {uploadState.status === "success" && (
          <div className="mt-4 flex items-center gap-2 rounded-lg bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-700 dark:bg-emerald-950 dark:border-emerald-800 dark:text-emerald-400">
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            <span>
              <strong>{uploadState.filename}</strong> uploaded successfully.
            </span>
          </div>
        )}

        {uploadState.status === "error" && (
          <div className="mt-4 flex items-center gap-2 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700 dark:bg-red-950 dark:border-red-800 dark:text-red-400">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{uploadState.message}</span>
            <button
              className="ml-auto text-xs underline hover:no-underline"
              onClick={() => setUploadState({ status: "idle" })}
            >
              Dismiss
            </button>
          </div>
        )}
      </div>

      {/* Document list */}
      <div>
        <h2 className="mb-3 text-sm font-semibold text-zinc-700 dark:text-zinc-300">
          Your documents
        </h2>
        <DocumentList />
      </div>
    </div>
  );
}
