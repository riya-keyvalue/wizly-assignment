"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

interface Field {
  id: string;
  label: string;
  type: string;
  placeholder: string;
  autoComplete?: string;
}

interface AuthFormProps {
  title: string;
  description: string;
  fields: Field[];
  submitLabel: string;
  onSubmit: (values: Record<string, string>) => Promise<void>;
  footer?: React.ReactNode;
}

export default function AuthForm({
  title,
  description,
  fields,
  submitLabel,
  onSubmit,
  footer,
}: AuthFormProps) {
  const [values, setValues] = useState<Record<string, string>>(
    Object.fromEntries(fields.map((f) => [f.id, ""]))
  );
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await onSubmit(values);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Something went wrong. Please try again.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md mx-auto">
      <div className="mb-8 text-center">
        <h1 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
          {title}
        </h1>
        <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400">
          {description}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {fields.map((field) => (
          <div key={field.id} className="space-y-1.5">
            <Label htmlFor={field.id}>{field.label}</Label>
            <Input
              id={field.id}
              type={field.type}
              placeholder={field.placeholder}
              autoComplete={field.autoComplete}
              value={values[field.id]}
              onChange={(e) =>
                setValues((v) => ({ ...v, [field.id]: e.target.value }))
              }
              required
            />
          </div>
        ))}

        {error && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700 dark:bg-red-950 dark:border-red-800 dark:text-red-400">
            {error}
          </div>
        )}

        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? (
            <span className="flex items-center gap-2">
              <svg
                className="h-4 w-4 animate-spin"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
              {submitLabel}…
            </span>
          ) : (
            submitLabel
          )}
        </Button>
      </form>

      {footer && (
        <div className="mt-6 text-center text-sm text-zinc-500 dark:text-zinc-400">
          {footer}
        </div>
      )}
    </div>
  );
}
