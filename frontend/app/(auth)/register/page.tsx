"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import AuthForm from "@/components/AuthForm";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

export default function RegisterPage() {
  const router = useRouter();
  const setTokens = useAuthStore((s) => s.setTokens);

  const handleRegister = async (values: Record<string, string>) => {
    if (values.password !== values.confirm) {
      throw { response: { data: { detail: "Passwords do not match" } } };
    }
    // Register then auto-login
    await authApi.register(values.email, values.password);
    const res = await authApi.login(values.email, values.password);
    const { access_token, refresh_token } = res.data.data;
    setTokens(access_token, refresh_token);
    router.replace("/documents");
  };

  return (
    <AuthForm
      title="Create an account"
      description="Start using Wizly today"
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
          placeholder: "Min. 8 characters",
          autoComplete: "new-password",
        },
        {
          id: "confirm",
          label: "Confirm password",
          type: "password",
          placeholder: "••••••••",
          autoComplete: "new-password",
        },
      ]}
      submitLabel="Create account"
      onSubmit={handleRegister}
      footer={
        <>
          Already have an account?{" "}
          <Link
            href="/login"
            className="font-medium text-zinc-900 underline-offset-4 hover:underline dark:text-zinc-50"
          >
            Sign in
          </Link>
        </>
      }
    />
  );
}
