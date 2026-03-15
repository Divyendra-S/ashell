"use client";

import { createContext, useContext, useState, useEffect, type ReactNode } from "react";

interface UserContextType {
  userId: string | null;
  login: (userId: string) => void;
  logout: () => void;
}

const UserContext = createContext<UserContextType>({
  userId: null,
  login: () => {},
  logout: () => {},
});

export function UserProvider({ children }: { children: ReactNode }) {
  const [userId, setUserId] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("kuro_user_id");
    if (stored) setUserId(stored);
    setLoaded(true);
  }, []);

  function login(id: string) {
    localStorage.setItem("kuro_user_id", id);
    setUserId(id);
  }

  function logout() {
    localStorage.removeItem("kuro_user_id");
    setUserId(null);
  }

  if (!loaded) return null;

  return (
    <UserContext.Provider value={{ userId, login, logout }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  return useContext(UserContext);
}
