/**
 * 发送聊天请求并消费后端数据流
 * - 参数 `kbId` 为单个知识库ID（字符串，如 'kb-1' 或 '1'）
 * - 返回异步迭代器用于增量读取文本与工具数据
 */
export type StreamChatOptions = {
  apiUrl?: string
  llmApiKey?: string
  llmBaseUrl?: string
  llmModel?: string
  sessionId?: string
  signal?: AbortSignal
  skipSaveUser?: boolean
}

function resolveChatUrl(raw?: string): string {
  const fallback = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000/api/chat'
  const url = (raw || fallback).trim()
  if (!url) return 'http://localhost:8000/api/chat'
  if (url.endsWith('/api/chat')) return url
  return url.replace(/\/+$/, '') + '/api/chat'
}

export async function streamChat(
  messages: Array<{ role: string; content: string }>,
  kbId?: string,
  options?: StreamChatOptions
) {
  const url = resolveChatUrl(options?.apiUrl)
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const apiKey = (options?.llmApiKey || '').trim()
  const baseUrl = (options?.llmBaseUrl || '').trim()
  const model = (options?.llmModel || '').trim()
  if (apiKey) headers['X-LLM-API-KEY'] = apiKey
  if (baseUrl) headers['X-LLM-BASE-URL'] = baseUrl
  if (model) headers['X-LLM-MODEL'] = model

  const res = await fetch(url, {
    method: 'POST',
    headers,
    body: JSON.stringify({ messages, kbId, sessionId: options?.sessionId, skipSaveUser: options?.skipSaveUser }),
    signal: options?.signal,
  })
  if (!res.body || !res.ok) {
    throw new Error(await res.text());
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();

  return {
    async *[Symbol.asyncIterator]() {
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;
          try {
            const parsed = JSON.parse(trimmed);
            yield parsed;
          } catch (e) {
            // 忽略无法解析的行（可能是空行或无效 JSON）
            console.debug('Failed to parse stream line:', trimmed, e);
          }
        }
      }
    },
  };
}
