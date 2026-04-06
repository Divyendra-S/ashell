"use client";

import { createContext, useContext, useState, useEffect, type ReactNode } from "react";
import { supabase } from "./supabase";

interface UserContextType {
  userId: string | null;
  email: string | null;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, username: string) => Promise<{ needsConfirmation: boolean }>;
  logout: () => Promise<void>;
  loading: boolean;
}

const UserContext = createContext<UserContextType>({
  userId: null,
  email: null,
  login: async () => {},
  signup: async () => ({ needsConfirmation: false }),
  logout: async () => {},
  loading: true,
});

export function UserProvider({ children }: { children: ReactNode }) {
  const [userId, setUserId] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for existing Supabase session
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session?.user) {
        const username = session.user.user_metadata?.username || session.user.email?.split("@")[0] || null;
        setUserId(username);
        setEmail(session.user.email || null);
      }
      setLoading(false);
    });

    // Listen for auth state changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session?.user) {
        const username = session.user.user_metadata?.username || session.user.email?.split("@")[0] || null;
        setUserId(username);
        setEmail(session.user.email || null);
      } else {
        setUserId(null);
        setEmail(null);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  async function login(email: string, password: string) {
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw error;
  }

  async function signup(email: string, password: string, username: string) {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: { data: { username } },
    });
    if (error) throw error;
    // If session exists, user is auto-confirmed
    return { needsConfirmation: !data.session };
  }

  async function logout() {
    await supabase.auth.signOut();
    setUserId(null);
    setEmail(null);
  }

  if (loading) return null;

  return (
    <UserContext.Provider value={{ userId, email, login, signup, logout, loading }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  return useContext(UserContext);
}
