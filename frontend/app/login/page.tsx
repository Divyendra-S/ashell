"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
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
            Welcome to Kuro
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: 0.14, ease: "easeOut" }}
            className="mt-1.5 text-[13px] text-text-tertiary"
          >
            Your personal knowledge companion
          </motion.p>
        </div>

        <motion.form
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.2, ease: "easeOut" }}
          onSubmit={handleSubmit}
          className="space-y-4"
        >
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Enter your username"
            autoFocus
            className="w-full rounded-xl border border-surface-2/30 bg-surface-05 px-4 py-3 text-[14px] text-text-primary placeholder-text-tertiary outline-none transition-all duration-200 focus:border-accent/30 focus:bg-surface-1"
          />
          <button
            type="submit"
            disabled={!username.trim()}
            className="w-full rounded-xl bg-accent/90 py-3 text-[13px] font-medium text-white transition-all duration-200 hover:bg-accent disabled:opacity-20"
          >
            Continue
          </button>
        </motion.form>
      </div>
    </div>
  );
}
