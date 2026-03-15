export interface ChatResponse {
  response: string;
  mode: "ingest" | "query";
  skill?: string | null;
}

export interface SkillInfo {
  name: string;
  description: string;
  triggers: string[];
}

export async function sendMessage(text: string, userId: string, skill?: string): Promise<ChatResponse> {
  const body: Record<string, string> = { message: text, user_id: userId };
  if (skill) body.skill = skill;

  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }
  return res.json();
}

export async function getSkills(): Promise<SkillInfo[]> {
  const res = await fetch("/api/skills");
  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }
  const data = await res.json();
  return data.skills;
}
