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
    <div className="gradient-page flex min-h-screen items-center justify-center bg-surface-0">
      <div className="w-full max-w-sm animate-fade-in px-6">
        <div className="mb-10 flex flex-col items-center">
          <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-accent/10">
            <span className="text-xl font-light text-accent">K</span>
          </div>
          <h1 className="text-xl font-extralight tracking-tight text-text-primary">
            Welcome to Kuro
          </h1>
          <p className="mt-1.5 text-[13px] text-text-tertiary">
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
            className="w-full rounded-xl border border-surface-2/30 bg-surface-1/50 px-4 py-3 text-[14px] text-text-primary placeholder-text-tertiary outline-none transition-all duration-200 focus:border-accent/30 focus:bg-surface-1/50"
          />
          <button
            type="submit"
            disabled={!username.trim()}
            className="w-full rounded-xl bg-accent/90 py-3 text-[13px] font-medium text-white transition-all duration-200 hover:bg-accent disabled:opacity-20"
          >
            Continue
          </button>
        </form>
      </div>
    </div>
  );
}
