import { createClient } from "@supabase/supabase-js";

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || "https://hlfswvzrtfeaucnpzfdp.supabase.co";
const SUPABASE_KEY = process.env.NEXT_PUBLIC_SUPABASE_KEY || "sb_publishable_mk8rNo3p6OVA5HgXMTrj-g_Q1dIY8rD";

export const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);
