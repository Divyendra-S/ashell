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

export interface GraphEntity {
  id: number;
  name: string;
  entity_type: string;
  summary: string | null;
  fact_count: number;
  community_id: number | null;
}

export interface GraphRelation {
  id: number;
  source_id: number;
  target_id: number;
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
  entity_count: number;
  fact_count: number;
  article_count: number;
  relation_count: number;
  new_entities_7d: number;
  new_facts_7d: number;
  new_articles_7d: number;
  health_score: number;
}

export interface GrowthDay {
  date: string;
  entities: number;
  facts: number;
  articles: number;
}

export interface EntityDetail {
  id: number;
  name: string;
  entity_type: string;
  summary: string | null;
  created_at: string;
  facts: { id: number; content: string; source: string; created_at: string }[];
  relations: GraphRelation[];
}

export interface Article {
  id: number;
  title: string;
  url: string | null;
  file_path: string;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
  chunk_count: number;
}

export interface TimelineEntry {
  type: "checkin" | "article" | "entity" | "goal_set";
  date: string;
  data: Record<string, unknown>;
}

export interface StreakData {
  current: number;
  longest: number;
  total_active_days: number;
}

export interface Note {
  id: number;
  content: string;
  entity_id: number | null;
  article_id: number | null;
  created_at: string;
}

export interface Passage {
  id: number;
  entity_id: number;
  article_id: number;
  content: string;
  created_at: string;
  articles: { id: number; title: string; url: string | null } | null;
}

export interface ConceptDetail extends EntityDetail {
  notes: Note[];
  learning_entries: { id: number; content: string; created_at: string }[];
  related_articles: { id: number; title: string; url: string | null }[];
  passages: Passage[];
}

export interface DigestData {
  streak: StreakData;
  recent_entities: { name: string; entity_type: string }[];
  recent_articles: { title: string; url: string | null }[];
  pending_goals: { id: number; content: string; created_at: string }[];
  study_suggestion: string | null;
  kb_suggestions: string[];
}

const API = "/api";

async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const maxRetries = init?.method === "POST" ? 0 : 2;
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const res = await fetch(`${API}${path}`, init);
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

export async function getEntityDetail(id: number, userId: string): Promise<EntityDetail> {
  return fetchJSON<EntityDetail>(`/entity/${id}?user_id=${userId}`);
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

export async function getConceptDetail(entityId: number, userId: string): Promise<ConceptDetail> {
  return fetchJSON<ConceptDetail>(`/concept/${entityId}?user_id=${userId}`);
}

export async function createNote(userId: string, content: string, entityId?: number, articleId?: number): Promise<Note> {
  return fetchJSON<Note>("/notes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: userId,
      content,
      entity_id: entityId ?? null,
      article_id: articleId ?? null,
    }),
  });
}

export async function deleteNote(noteId: number, userId: string): Promise<void> {
  await fetchJSON(`/notes/${noteId}?user_id=${userId}`, { method: "DELETE" });
}
