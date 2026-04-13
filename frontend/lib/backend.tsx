"use client";

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { setApiBase } from "./api";

type Backend = "kuro" | "nexus";

interface BackendContextType {
  backend: Backend;
  toggle: () => void;
}

const PORTS: Record<Backend, number> = {
  kuro: 8000,
  nexus: 8001,
};

function resolveApiBase(backend: Backend): string {
  return `http://localhost:${PORTS[backend]}/api`;
}

const BackendContext = createContext<BackendContextType>({
  backend: "kuro",
  toggle: () => {},
});

export function BackendProvider({ children }: { children: ReactNode }) {
  const [backend, setBackend] = useState<Backend>("kuro");
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("kuro_backend") as Backend | null;
    if (stored === "kuro" || stored === "nexus") {
      setBackend(stored);
    }
    setLoaded(true);
  }, []);

  useEffect(() => {
    if (!loaded) return;
    localStorage.setItem("kuro_backend", backend);
    setApiBase(resolveApiBase(backend));
  }, [backend, loaded]);

  const toggle = useCallback(() => {
    setBackend((prev) => (prev === "kuro" ? "nexus" : "kuro"));
  }, []);

  if (!loaded) return null;

  return (
    <BackendContext.Provider value={{ backend, toggle }}>
      {children}
    </BackendContext.Provider>
  );
}

export function useBackend() {
  return useContext(BackendContext);
}
