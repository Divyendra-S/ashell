export interface ChatResponse {
  response: string;
  skill?: string | null;
}

export interface SkillInfo {
  name: string;
  description: string;
  triggers: string[];
}

export interface GraphEntity {
  id: string;
  name: string;
  entity_type: string;
  summary: string | null;
  fact_count: number;
}

export interface GraphRelation {
  id: string;
  source_id: string;
  target_id: string;
  relation_type: string;
  context: string | null;
  source_name: string;
  target_name: string;
}

export interface GraphData {
  entities: GraphEntity[];
  relations: GraphRelation[];
}

export interface Stats {
  concept_count: number;
  backlink_count: number;
  article_count: number;
  new_concepts_7d: number;
  new_articles_7d: number;
  health_score: number;
}

export interface GrowthDay {
  date: string;
  concepts: number;
  articles: number;
}

export interface ConceptDetail {
  slug: string;
  name: string;
  summary: string | null;
  content: string;
  backlinks: { name: string; slug: string }[];
  incoming_backlinks: { name: string; slug: string }[];
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface Article {
  id: number;
  title: string;
  url: string | null;
  file_path: string;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
}

export interface TimelineEntry {
  type: "checkin" | "article" | "concept" | "goal_set";
  date: string;
  data: Record<string, unknown>;
}

export interface StreakData {
  current: number;
  longest: number;
  total_active_days: number;
}

export interface DigestData {
  streak: StreakData;
  recent_concepts: { name: string }[];
  recent_articles: { title: string; url: string | null }[];
  pending_goals: { id: number; content: string; created_at: string }[];
  study_suggestion: string | null;
  kb_suggestions: string[];
}

let _apiBase = "http://localhost:8000/api";

export function setApiBase(base: string) {
  _apiBase = base;
}

async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const maxRetries = init?.method === "POST" ? 0 : 2;
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const res = await fetch(`${_apiBase}${path}`, init);
      if (res.ok) return res.json();
      if (res.status < 500 || attempt === maxRetries) {
        throw new Error(`API error: ${res.status}`);
      }
    } catch (err) {
      if (attempt === maxRetries) throw err;
    }
    await new Promise((r) => setTimeout(r, 500 * (attempt + 1)));
  }
  throw new Error("API request failed");
}

export async function sendMessage(text: string, userId: string, skill?: string): Promise<ChatResponse> {
  const body: Record<string, string> = { message: text, user_id: userId };
  if (skill) body.skill = skill;
  return fetchJSON<ChatResponse>("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export interface ToolStep {
  tool: string;
  args: Record<string, unknown>;
  status: "running" | "done";
}

export function streamMessage(
  text: string,
  userId: string,
  skill: string | undefined,
  callbacks: {
    onStep: (step: ToolStep) => void;
    onDelta: (text: string) => void;
    onDone: (meta: { mode: string; skill?: string }) => void;
    onError: (message: string) => void;
  },
  history?: { role: string; text: string }[],
): AbortController {
  const controller = new AbortController();
  const body: Record<string, unknown> = { message: text, user_id: userId };
  if (skill) body.skill = skill;
  if (history?.length) body.history = history;

  const streamUrl = `${_apiBase}/chat/stream`;

  fetch(streamUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok) {
        callbacks.onError(`API error: ${res.status}`);
        return;
      }
      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      let eventType = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // Parse SSE events from buffer
        const lines = buffer.split("\n");
        buffer = lines.pop()!; // keep incomplete line
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith("data: ") && eventType) {
            try {
              const data = JSON.parse(line.slice(6));
              if (eventType === "step") callbacks.onStep(data as ToolStep);
              else if (eventType === "delta") callbacks.onDelta(data.text);
              else if (eventType === "done") callbacks.onDone(data);
              else if (eventType === "error") callbacks.onError(data.message);
            } catch {
              // skip malformed JSON
            }
            eventType = "";
          } else if (line === "") {
            eventType = "";
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        callbacks.onError(String(err));
      }
    });

  return controller;
}

export async function getSkills(): Promise<SkillInfo[]> {
  const data = await fetchJSON<{ skills: SkillInfo[] }>("/skills");
  return data.skills;
}

export async function getGraph(userId: string): Promise<GraphData> {
  return fetchJSON<GraphData>(`/graph?user_id=${userId}`);
}

export async function getStats(userId: string): Promise<Stats> {
  return fetchJSON<Stats>(`/stats?user_id=${userId}`);
}

export async function getGrowth(userId: string, days = 30): Promise<GrowthDay[]> {
  const data = await fetchJSON<{ data: GrowthDay[] }>(`/stats/growth?user_id=${userId}&days=${days}`);
  return data.data;
}

export async function getConceptDetail(slug: string, userId: string): Promise<ConceptDetail> {
  return fetchJSON<ConceptDetail>(`/concept/${slug}?user_id=${userId}`);
}

export async function getArticles(userId: string): Promise<Article[]> {
  const data = await fetchJSON<{ articles: Article[] }>(`/articles?user_id=${userId}`);
  return data.articles;
}

export async function getTimeline(userId: string, days = 30): Promise<TimelineEntry[]> {
  const data = await fetchJSON<{ timeline: TimelineEntry[] }>(`/progress/timeline?user_id=${userId}&days=${days}`);
  return data.timeline;
}

export async function getStreak(userId: string): Promise<StreakData> {
  return fetchJSON<StreakData>(`/progress/streak?user_id=${userId}`);
}

export async function completeGoal(entryId: number, userId: string): Promise<void> {
  await fetchJSON(`/goals/${entryId}/complete?user_id=${userId}`, { method: "PATCH" });
}

export async function getDigest(userId: string): Promise<DigestData> {
  return fetchJSON<DigestData>(`/digest?user_id=${userId}`);
}

export async function createNote(userId: string, content: string, conceptSlug: string): Promise<{ status: string; concept_slug: string }> {
  return fetchJSON("/notes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: userId,
      content,
      concept_slug: conceptSlug,
    }),
  });
}
