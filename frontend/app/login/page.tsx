"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useUser } from "../../lib/user";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const { login } = useUser();
  const router = useRouter();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const id = username.trim();
    if (!id) return;
    login(id);
    router.push("/");
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface-0">
      <div className="w-full max-w-sm animate-fade-in px-6">
        <div className="mb-8 flex flex-col items-center">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-accent/15 text-accent">
            <span className="text-2xl font-semibold">K</span>
          </div>
          <h1 className="text-xl font-medium text-text-primary">Welcome to Kuro</h1>
          <p className="mt-1 text-sm text-text-tertiary">
            Enter your username to continue
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Username"
            autoFocus
            className="w-full rounded-xl border border-surface-2 bg-surface-1 px-4 py-3 text-[15px] text-text-primary placeholder-text-tertiary outline-none transition-colors focus:border-accent/40"
          />
          <button
            type="submit"
            disabled={!username.trim()}
            className="w-full rounded-xl bg-accent py-3 text-sm font-medium text-surface-0 transition-opacity disabled:opacity-30"
          >
            Continue
          </button>
        </form>
      </div>
    </div>
  );
}
