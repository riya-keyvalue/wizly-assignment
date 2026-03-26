"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import AuthForm from "@/components/AuthForm";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

export default function LoginPage() {
  const router = useRouter();
  const setTokens = useAuthStore((s) => s.setTokens);

  const handleLogin = async (values: Record<string, string>) => {
    const res = await authApi.login(values.email, values.password);
    const { access_token, refresh_token } = res.data.data;
    setTokens(access_token, refresh_token);
    router.replace("/chat");
  };

  return (
    <AuthForm
      title="Welcome back"
      description="Sign in to your Wizly account"
      fields={[
        {
          id: "email",
          label: "Email",
          type: "email",
          placeholder: "you@example.com",
          autoComplete: "email",
        },
        {
          id: "password",
          label: "Password",
          type: "password",
          placeholder: "••••••••",
          autoComplete: "current-password",
        },
      ]}
      submitLabel="Sign in"
      onSubmit={handleLogin}
      footer={
        <>
          Don&apos;t have an account?{" "}
          <Link
            href="/register"
            className="font-medium text-zinc-900 underline-offset-4 hover:underline dark:text-zinc-50"
          >
            Register
          </Link>
        </>
      }
    />
  );
}
