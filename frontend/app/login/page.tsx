"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { useUser } from "../../lib/user";

export default function LoginPage() {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [username, setUsername] = useState("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { login, signup } = useUser();
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setInfo("");

    if (!email.trim() || !password) {
      setError("Enter email and password");
      return;
    }

    if (mode === "signup" && !username.trim()) {
      setError("Choose a username");
      return;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters");
      return;
    }

    setSubmitting(true);

    try {
      if (mode === "login") {
        await login(email.trim(), password);
        router.push("/");
      } else {
        const { needsConfirmation } = await signup(email.trim(), password, username.trim());
        if (needsConfirmation) {
          setInfo("Check your email to confirm your account, then sign in.");
          setMode("login");
        } else {
          router.push("/");
        }
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Something went wrong";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="gradient-page flex min-h-screen items-center justify-center bg-surface-0">
      <div className="w-full max-w-sm px-6">
        <div className="mb-10 flex flex-col items-center">
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: "spring", damping: 20, stiffness: 200 }}
            className="mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-accent/10"
          >
            <span className="text-xl font-light text-accent">K</span>
          </motion.div>
          <motion.h1
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: 0.08, ease: "easeOut" }}
            className="text-xl font-extralight tracking-tight text-text-primary"
          >
            {mode === "login" ? "Welcome back" : "Create account"}
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: 0.14, ease: "easeOut" }}
            className="mt-1.5 text-[13px] text-text-tertiary"
          >
            {mode === "login"
              ? "Sign in to your Kuro knowledge wiki"
              : "Start building your personal knowledge base"}
          </motion.p>
        </div>

        <motion.form
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.2, ease: "easeOut" }}
          onSubmit={handleSubmit}
          className="space-y-3"
        >
          {mode === "signup" && (
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Username (your user ID)"
              autoFocus
              className="w-full rounded-xl border border-surface-2/30 bg-surface-05 px-4 py-3 text-[14px] text-text-primary placeholder-text-tertiary outline-none transition-all duration-200 focus:border-accent/30 focus:bg-surface-1"
            />
          )}
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            autoFocus={mode === "login"}
            className="w-full rounded-xl border border-surface-2/30 bg-surface-05 px-4 py-3 text-[14px] text-text-primary placeholder-text-tertiary outline-none transition-all duration-200 focus:border-accent/30 focus:bg-surface-1"
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            className="w-full rounded-xl border border-surface-2/30 bg-surface-05 px-4 py-3 text-[14px] text-text-primary placeholder-text-tertiary outline-none transition-all duration-200 focus:border-accent/30 focus:bg-surface-1"
          />

          {error && (
            <p className="text-center text-[12px] text-red-400">{error}</p>
          )}
          {info && (
            <p className="text-center text-[12px] text-emerald-400">{info}</p>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-xl bg-accent/90 py-3 text-[13px] font-medium text-white transition-all duration-200 hover:bg-accent disabled:opacity-40"
          >
            {submitting
              ? mode === "login" ? "Signing in..." : "Creating account..."
              : mode === "login" ? "Sign In" : "Create Account"}
          </button>

          <button
            type="button"
            onClick={() => {
              setMode(mode === "login" ? "signup" : "login");
              setError("");
              setInfo("");
            }}
            className="w-full py-2 text-[12px] text-accent/70 transition-colors hover:text-accent"
          >
            {mode === "login" ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
          </button>
        </motion.form>
      </div>
    </div>
  );
}
