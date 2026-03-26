"use client";

import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-zinc-50 dark:bg-zinc-950 px-4 text-center">
      <p className="text-sm font-semibold uppercase tracking-widest text-red-400 dark:text-red-500">
        500
      </p>
      <h1 className="mt-3 text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
        Something went wrong
      </h1>
      <p className="mt-3 text-sm text-zinc-500 dark:text-zinc-400 max-w-sm">
        An unexpected error occurred. Please try again or contact support if the
        problem persists.
      </p>
      <div className="mt-8 flex gap-3">
        <button
          onClick={reset}
          className="rounded-lg bg-zinc-900 px-5 py-2.5 text-sm font-medium text-white hover:bg-zinc-700 transition-colors dark:bg-zinc-50 dark:text-zinc-900 dark:hover:bg-zinc-200"
        >
          Try again
        </button>
        <a
          href="/"
          className="rounded-lg border border-zinc-200 px-5 py-2.5 text-sm font-medium text-zinc-700 hover:bg-zinc-100 transition-colors dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
        >
          Go home
        </a>
      </div>
    </div>
  );
}
