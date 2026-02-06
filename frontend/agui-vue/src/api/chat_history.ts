const getApiBase = () => {
  const raw = (import.meta as any).env?.VITE_API_URL || "http://localhost:8000";
  return String(raw).replace(/\/$/, "");
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
}

export interface MessageCitation {
  file_id: number;
  chunk_index: number;
  filename: string;
  content: string;
  metadata?: Record<string, any>;
}

export interface ChatMessage {
  id: number;
  role: string;
  content: string;
  createdAt: number;
  citations?: MessageCitation[];
}

export async function fetchSessions(): Promise<ChatSession[]> {
  const res = await fetch(`${getApiBase()}/api/chat/sessions`);
  const json = await res.json();
  if (json.ok) return json.data;
  return [];
}

export async function createSession(title: string = "New Chat"): Promise<ChatSession> {
  const res = await fetch(`${getApiBase()}/api/chat/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  const json = await res.json();
  if (json.ok) return json.data;
  throw new Error("Failed to create session");
}

export async function deleteSession(sessionId: string): Promise<void> {
  await fetch(`${getApiBase()}/api/chat/sessions/${sessionId}`, {
    method: "DELETE"
  });
}

export async function fetchMessages(sessionId: string): Promise<ChatMessage[]> {
  const res = await fetch(`${getApiBase()}/api/chat/sessions/${sessionId}/messages`);
  const json = await res.json();
  if (json.ok) return json.data;
  return [];
}

export async function editMessage(sessionId: string, messageId: number, content: string): Promise<void> {
  const res = await fetch(`${getApiBase()}/api/chat/sessions/${sessionId}/messages/${messageId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  const json = await res.json();
  if (!json.ok) {
    throw new Error(json.error?.message || "Failed to edit message");
  }
}

export async function updateSessionTitle(sessionId: string, title: string): Promise<void> {
  const res = await fetch(`${getApiBase()}/api/chat/sessions/${sessionId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  const json = await res.json();
  if (!json.ok) {
    throw new Error(json.error?.message || "Failed to update session title");
  }
}
