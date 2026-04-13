"use client";

import { usePathname, useRouter } from "next/navigation";
import { useUser } from "../lib/user";
import { useTheme } from "../lib/theme";
import { useBackend } from "../lib/backend";
import { useState, useEffect } from "react";
import { getStats, getStreak, type Stats, type StreakData } from "../lib/api";

const navItems = [
  {
    label: "Chat",
    href: "/",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    ),
  },
  {
    label: "Voice",
    href: "/voice",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <rect x="9" y="1" width="6" height="11" rx="3" />
        <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
        <line x1="12" y1="19" x2="12" y2="23" />
      </svg>
    ),
  },
  {
    label: "Dashboard",
    href: "/dashboard",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <circle cx="12" cy="12" r="3" />
        <path d="M12 2a10 10 0 0 1 10 10" />
      </svg>
    ),
  },
  {
    label: "Progress",
    href: "/progress",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
      </svg>
    ),
  },
];

const quickActions = [
  {
    label: "Ingest URL",
    prefill: "/ingest-url ",
    icon: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
      </svg>
    ),
  },
  {
    label: "Set Goal",
    prefill: "/goal ",
    icon: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <circle cx="12" cy="12" r="6" />
        <circle cx="12" cy="12" r="2" />
      </svg>
    ),
  },
  {
    label: "Study",
    prefill: "/study ",
    icon: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
        <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
      </svg>
    ),
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { userId, logout } = useUser();
  const { theme, toggle: toggleTheme } = useTheme();
  const { backend, toggle: toggleBackend } = useBackend();
  const [collapsed, setCollapsed] = useState(false);
  const [stats, setStats] = useState<Stats | null>(null);
  const [streak, setStreak] = useState<StreakData | null>(null);

  useEffect(() => {
    if (!userId) return;
    getStats(userId).then(setStats).catch(() => {});
    getStreak(userId).then(setStreak).catch(() => {});
  }, [userId, backend]);

  if (!userId || pathname === "/login") return null;

  return (
    <aside
      className={`flex flex-col border-r border-surface-2/30 bg-surface-0 transition-all duration-300 ease-out ${
        collapsed ? "w-14" : "w-48"
      }`}
    >
      {/* Logo + collapse */}
      <div className="flex h-12 items-center justify-between px-3">
        {!collapsed && (
          <span className="text-[11px] font-medium uppercase tracking-[0.2em] text-text-tertiary">
            {backend === "kuro" ? "Kuro" : "Nexus"}
          </span>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex h-6 w-6 items-center justify-center rounded-md text-text-tertiary transition-colors duration-200 hover:text-text-secondary"
          title={collapsed ? "Expand" : "Collapse"}
        >
          <svg
            width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
            className={`transition-transform duration-300 ${collapsed ? "rotate-180" : ""}`}
          >
            <path d="M10 4L6 8L10 12" />
          </svg>
        </button>
      </div>

      {/* Nav items */}
      <nav className="space-y-0.5 px-2 pt-2">
        {navItems.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);

          return (
            <button
              key={item.href}
              onClick={() => router.push(item.href)}
              className={`group flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] transition-all duration-200 ${
                isActive
                  ? "bg-accent/8 text-accent"
                  : "text-text-tertiary hover:bg-surface-1/50 hover:text-text-secondary"
              } ${collapsed ? "justify-center" : ""}`}
              title={item.label}
            >
              <span className="shrink-0">{item.icon}</span>
              {!collapsed && <span className="font-light">{item.label}</span>}
            </button>
          );
        })}
      </nav>

      {/* Quick actions — expanded only */}
      {!collapsed && (
        <div className="mt-5 border-t border-surface-2/20 px-2 pt-4">
          <p className="mb-2 px-2.5 text-[9px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">
            Quick Actions
          </p>
          <div className="space-y-0.5">
            {quickActions.map((action) => (
              <button
                key={action.label}
                onClick={() => {
                  if (pathname === "/") {
                    window.dispatchEvent(new CustomEvent("kuro:prefill", { detail: action.prefill }));
                  } else {
                    sessionStorage.setItem("kuro_prefill", action.prefill);
                    router.push("/");
                  }
                }}
                className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-[11px] text-text-tertiary transition-all duration-200 hover:bg-surface-1/50 hover:text-text-secondary"
              >
                <span className="shrink-0 text-text-tertiary">{action.icon}</span>
                {action.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Stats — expanded only */}
      {!collapsed && stats && (
        <div className="mt-4 border-t border-surface-2/20 px-2 pt-4">
          <p className="mb-2 px-2.5 text-[9px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">
            Knowledge Base
          </p>
          <div className="grid grid-cols-2 gap-1.5 px-1">
            {[
              { label: "Concepts", value: stats.concept_count },
              { label: "Links", value: stats.backlink_count },
              { label: "Articles", value: stats.article_count },
              { label: "Streak", value: streak?.current ?? 0, suffix: "d" },
            ].map((item) => (
              <div key={item.label} className="rounded-lg bg-surface-05 px-2.5 py-2">
                <p className="text-[15px] font-extralight leading-none text-text-primary">
                  {item.value}{item.suffix || ""}
                </p>
                <p className="mt-0.5 text-[8px] uppercase tracking-wider text-text-tertiary">
                  {item.label}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Spacer */}
      <div className="flex-1" />

      {/* Backend toggle */}
      <div className="px-2 pb-1">
        <button
          onClick={toggleBackend}
          className={`group flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] text-text-tertiary transition-all duration-200 hover:bg-surface-1/50 hover:text-text-secondary ${collapsed ? "justify-center" : ""}`}
          title={`Switch to ${backend === "kuro" ? "Nexus" : "Kuro"}`}
        >
          <span className="shrink-0">
            {backend === "kuro" ? (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                <ellipse cx="12" cy="5" rx="9" ry="3" />
                <path d="M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5" />
                <path d="M3 12c0 1.66 4.03 3 9 3s9-1.34 9-3" />
              </svg>
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="3" />
                <circle cx="19" cy="5" r="2" />
                <circle cx="5" cy="5" r="2" />
                <circle cx="19" cy="19" r="2" />
                <circle cx="5" cy="19" r="2" />
                <line x1="14.5" y1="10" x2="17.5" y2="6.5" />
                <line x1="9.5" y1="10" x2="6.5" y2="6.5" />
                <line x1="14.5" y1="14" x2="17.5" y2="17.5" />
                <line x1="9.5" y1="14" x2="6.5" y2="17.5" />
              </svg>
            )}
          </span>
          {!collapsed && <span className="font-light">{backend === "kuro" ? "Kuro" : "Nexus"}</span>}
        </button>
      </div>

      {/* Theme toggle */}
      <div className="px-2 pb-1">
        <button
          onClick={toggleTheme}
          className={`group flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] text-text-tertiary transition-all duration-200 hover:bg-surface-1/50 hover:text-text-secondary ${collapsed ? "justify-center" : ""}`}
          title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        >
          <span className="shrink-0">
            {theme === "dark" ? (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="5" />
                <line x1="12" y1="1" x2="12" y2="3" />
                <line x1="12" y1="21" x2="12" y2="23" />
                <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
                <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                <line x1="1" y1="12" x2="3" y2="12" />
                <line x1="21" y1="12" x2="23" y2="12" />
                <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
                <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
              </svg>
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
              </svg>
            )}
          </span>
          {!collapsed && <span className="font-light">{theme === "dark" ? "Light Mode" : "Dark Mode"}</span>}
        </button>
      </div>

      {/* User section */}
      <div className="px-2 pb-3 pt-2">
        <div
          className={`flex items-center gap-2.5 rounded-lg px-2.5 py-2 ${
            collapsed ? "justify-center" : ""
          }`}
        >
          <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-surface-2/50 text-[10px] font-medium text-text-tertiary">
            {userId[0].toUpperCase()}
          </div>
          {!collapsed && (
            <div className="flex min-w-0 flex-1 items-center justify-between">
              <span className="truncate text-[11px] text-text-tertiary">
                {userId}
              </span>
              <button
                onClick={async () => { await logout(); router.push("/login"); }}
                className="text-text-tertiary transition-colors duration-200 hover:text-text-secondary"
                title="Logout"
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                  <polyline points="16 17 21 12 16 7" />
                  <line x1="21" y1="12" x2="9" y2="12" />
                </svg>
              </button>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
