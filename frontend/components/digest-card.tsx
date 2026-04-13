"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { getDigest, completeGoal, type DigestData } from "../lib/api";
import { useBackend } from "../lib/backend";

export function DigestCard({ userId }: { userId: string }) {
  const { backend } = useBackend();
  const [digest, setDigest] = useState<DigestData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDigest(userId).then(setDigest).catch(console.error).finally(() => setLoading(false));
  }, [userId, backend]);

  if (loading || !digest) return null;

  const hasContent =
    digest.recent_concepts.length > 0 ||
    digest.recent_articles.length > 0 ||
    digest.study_suggestion;

  if (!hasContent && digest.streak.current === 0) return null;

  // Show a compact one-liner digest
  const recentCount = digest.recent_concepts.length + digest.recent_articles.length;
  const parts: string[] = [];
  if (digest.streak.current > 0) parts.push(`${digest.streak.current}-day streak`);
  if (recentCount > 0) parts.push(`${recentCount} new item${recentCount > 1 ? "s" : ""} added`);
  if (digest.study_suggestion) parts.push(`review ${digest.study_suggestion}`);

  return (
    <motion.p
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.15, ease: "easeOut" }}
      className="text-[12px] text-text-tertiary"
    >
      {parts.join(" · ")}
    </motion.p>
  );
}
