import { z } from 'zod'
import {
  EventType,
  TextMessageStartEventSchema,
  TextMessageContentEventSchema,
  TextMessageEndEventSchema,
} from '@ag-ui/core'

// Lightweight AG-UI client stub for browser usage
// Now integrated with real backend streaming.

// Derive types from Zod schemas provided by AG-UI
export type TextMessageStart = z.infer<typeof TextMessageStartEventSchema>
export type TextMessageContent = z.infer<typeof TextMessageContentEventSchema>
export type TextMessageEnd = z.infer<typeof TextMessageEndEventSchema>

type StartHandler = (e: TextMessageStart) => void
type ContentHandler = (e: TextMessageContent) => void
type EndHandler = (e: TextMessageEnd) => void

export class AguiClient {
  private onStart?: StartHandler
  private onContent?: ContentHandler
  private onEnd?: EndHandler

  onTextMessageStartEvent(handler: StartHandler) {
    this.onStart = handler
  }
  onTextMessageContentEvent(handler: ContentHandler) {
    this.onContent = handler
  }
  onTextMessageEndEvent(handler: EndHandler) {
    this.onEnd = handler
  }

  async sendUserMessage(message: string) {
    const runId = 'run-' + Date.now();
    const agentId = 'agent-deepseek';

    try {
      const response = await fetch('/api/chat', { // 使用 /api 前缀，通过代理转发
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message,
          runId,
          agentId,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Response body is null');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        
        // 保留最后一个可能不完整的数据块
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmedLine = line.trim();
          if (!trimmedLine.startsWith('data: ')) continue;

          const jsonStr = trimmedLine.substring(6); // Remove 'data: ' prefix
          try {
            const event = JSON.parse(jsonStr);
            // 验证并分发事件
            if (event.type === EventType.TEXT_MESSAGE_START) {
              this.onStart?.(event);
            } else if (event.type === EventType.TEXT_MESSAGE_CONTENT) {
              this.onContent?.(event);
            } else if (event.type === EventType.TEXT_MESSAGE_END) {
              this.onEnd?.(event);
            }
          } catch (e) {
            console.error('Error parsing SSE event:', e, jsonStr);
          }
        }
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      // 发送一个错误消息给 UI
      const errorId = 'error-' + Date.now();
      this.onContent?.({
        type: EventType.TEXT_MESSAGE_CONTENT,
        id: errorId,
        runId,
        agentId,
        delta: `\n[Error: ${error instanceof Error ? error.message : String(error)}]`,
        timestamp: Date.now(),
      } as any); // 使用 any 绕过类型检查，如果类型定义过严
      
      this.onEnd?.({
        type: EventType.TEXT_MESSAGE_END,
        id: errorId,
        runId,
        agentId,
        timestamp: Date.now(),
        source: 'system' // 或者其他允许的值
      } as any);
    }
  }
}

export const aguiClient = new AguiClient()
