import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => (
    <input
      type={type}
      className={cn(
        "flex h-10 w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm",
        "placeholder:text-zinc-400",
        "focus:outline-none focus:ring-2 focus:ring-zinc-900 focus:border-transparent",
        "disabled:cursor-not-allowed disabled:opacity-50",
        "dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50 dark:placeholder:text-zinc-500",
        "dark:focus:ring-zinc-300",
        className
      )}
      ref={ref}
      {...props}
    />
  )
);
Input.displayName = "Input";

export { Input };
