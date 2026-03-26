import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-zinc-50 dark:bg-zinc-950 px-4 text-center">
      <p className="text-sm font-semibold uppercase tracking-widest text-zinc-400 dark:text-zinc-500">
        404
      </p>
      <h1 className="mt-3 text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
        Page not found
      </h1>
      <p className="mt-3 text-sm text-zinc-500 dark:text-zinc-400 max-w-sm">
        The page you&apos;re looking for doesn&apos;t exist or has been moved.
      </p>
      <Link
        href="/"
        className="mt-8 rounded-lg bg-zinc-900 px-5 py-2.5 text-sm font-medium text-white hover:bg-zinc-700 transition-colors dark:bg-zinc-50 dark:text-zinc-900 dark:hover:bg-zinc-200"
      >
        Go home
      </Link>
    </div>
  );
}
