export async function streamChat(
  messages: Array<{ role: string; content: string }>,
  apiUrl?: string
) {
  const url = apiUrl || (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000/api/chat';
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages }),
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
          const idx = line.indexOf(':');
          if (idx === -1) continue;
          const type = line.slice(0, idx);
          const content = line.slice(idx + 1);
          try {
            const parsed = JSON.parse(content);
            if (type === '0') yield { type: 'text', data: parsed };
            else if (type === '8') yield { type: 'data', data: parsed };
            else if (type === '3') yield { type: 'error', data: parsed };
          } catch {
            // ignore
          }
        }
      }
    },
  };
}
