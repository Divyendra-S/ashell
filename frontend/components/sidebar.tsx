"use client";

import { usePathname, useRouter } from "next/navigation";
import { useUser } from "../lib/user";
import { useState } from "react";

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

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { userId, logout } = useUser();
  const [collapsed, setCollapsed] = useState(false);

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
            Kuro
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
      <nav className="flex-1 space-y-0.5 px-2 pt-2">
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
                onClick={() => { logout(); router.push("/login"); }}
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
