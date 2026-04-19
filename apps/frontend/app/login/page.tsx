"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { login } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await login(password);
      await queryClient.invalidateQueries();
      router.push("/load-data");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="py-16 max-w-sm mx-auto">
      <h1 className="text-2xl font-headline font-bold tracking-tight mb-2">
        Owner login
      </h1>
      <p className="text-sm text-on-surface-variant mb-8">
        Enter the owner password to switch from the public demo portfolio to
        your real data.
      </p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
          autoFocus
          className="w-full px-3 py-2 rounded-lg bg-surface-container border border-outline-variant/30 focus:border-primary focus:outline-none text-on-surface"
        />

        {error && (
          <div className="text-sm text-error bg-error/5 rounded-lg px-3 py-2">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={submitting || password.length === 0}
          className="w-full px-4 py-2 rounded-lg bg-primary text-on-primary font-label disabled:opacity-50"
        >
          {submitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
