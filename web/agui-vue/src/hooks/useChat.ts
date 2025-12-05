import { ref } from 'vue';

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'data';
  content: string;
  [key: string]: any;
}

export interface ReasoningStep {
  type: 'tool_start' | 'tool_end';
  tool: string;
  input?: any;
  output?: any;
  ts?: number;
}

export function useChat(options: { api?: string } = {}) {
  const messages = ref<Message[]>([]);
  const input = ref('');
  const isLoading = ref(false);
  const status = ref<'ready' | 'streaming' | 'error'>('ready');
  const reasoningSteps = ref<ReasoningStep[]>([]);

  /**
   * 发送消息并消费后端数据流（Data Stream Protocol）
   */
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
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.trim()) continue;
          
          // Parse Data Stream Protocol
          // Format: type:value
          const colonIndex = line.indexOf(':');
          if (colonIndex === -1) continue;

          const type = line.slice(0, colonIndex);
          const content = line.slice(colonIndex + 1);

          try {
            const parsedContent = JSON.parse(content);

            // 0: text part
            if (type === '0') {
              assistantMsg.content += parsedContent;
            }
            // 8: data message (tool calls etc)
            else if (type === '8') {
               // 处理工具调用进度为推理步骤
               const items = Array.isArray(parsedContent) ? parsedContent : [parsedContent];
               for (const it of items) {
                 if (it && (it.type === 'tool_start' || it.type === 'tool_end')) {
                   reasoningSteps.value.push({
                     type: it.type,
                     tool: it.tool,
                     input: it.input,
                     output: it.output,
                     ts: Date.now(),
                   });
                 }
               }
            }
            // 3: error
            else if (type === '3') {
              console.error('Stream error message:', parsedContent);
              status.value = 'error';
            }
          } catch (e) {
            console.warn('Failed to parse stream line:', line, e);
          }
        }
      }
    } catch (err) {
      console.error('Stream error:', err);
      status.value = 'error';
    } finally {
      isLoading.value = false;
      status.value = 'ready';
    }
  };

  return { messages, input, handleSubmit, status, isLoading, reasoningSteps };
}
