import { ref } from 'vue';

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'data';
  content: string;
  [key: string]: any;
}

export function useChat(options: { api?: string } = {}) {
  const messages = ref<Message[]>([]);
  const input = ref('');
  const isLoading = ref(false);
  const status = ref<'ready' | 'streaming' | 'error'>('ready');

  const handleSubmit = async (e?: any) => {
    if (e && e.preventDefault) e.preventDefault();
    if (!input.value.trim()) return;

    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: input.value };
    messages.value.push(userMsg);
    // const prompt = input.value;
    input.value = '';
    isLoading.value = true;
    status.value = 'streaming';

    try {
      const apiUrl = options.api || (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000/api/chat';
      console.log('Sending request to:', apiUrl);
      const res = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: messages.value }),
      });
      
      if (!res.ok) {
        const errorText = await res.text();
        console.error('Fetch error:', res.status, res.statusText, errorText);
        throw new Error(res.statusText);
      }
      
      const reader = res.body?.getReader();
      if (!reader) return;

      const assistantMsg: Message = { id: (Date.now() + 1).toString(), role: 'assistant', content: '' };
      messages.value.push(assistantMsg);
      
      const decoder = new TextDecoder();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        console.log('Received chunk:', chunk);
        assistantMsg.content += chunk;
      }
    } catch (err) {
      console.error('Stream error:', err);
      status.value = 'error';
    } finally {
      isLoading.value = false;
      status.value = 'ready';
    }
  };

  return { messages, input, handleSubmit, status, isLoading };
}
