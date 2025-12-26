/**
 * 发送聊天请求并消费后端数据流
 * - 参数 `kbId` 为单个知识库ID（字符串，如 'kb-1' 或 '1'）
 * - 返回异步迭代器用于增量读取文本与工具数据
 */
export async function streamChat(
  messages: Array<{ role: string; content: string }>,
  kbId?: string,
  apiUrl?: string
) {
  const url = apiUrl || (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000/api/chat';
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages, kbId }),
  });
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
          try {
            const parsed = JSON.parse(line);
            yield parsed;
          } catch {
            // ignore
          }
        }
      }
    },
  };
}
