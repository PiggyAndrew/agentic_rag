import { defineStore } from 'pinia';
import { ref } from 'vue';
import { fetchSessions, createSession, deleteSession } from '@/api/chat_history';
import type { ChatSession } from '@/api/chat_history';
import type { ChatMessage } from '@/api/chat_history';

export const useChatStore = defineStore('chat', () => {
  const sessions = ref<ChatSession[]>([]);
  const currentSessionId = ref<string | null>(null);
  const messagesBySession = ref<Record<string, ChatMessage[]>>({});
  const uiMessagesBySession = ref<Record<string, any[]>>({});
  const statusBySession = ref<Record<string, 'ready' | 'submitted' | 'streaming'>>({});
  
  async function loadSessions() {
    sessions.value = await fetchSessions();
  }
  
  async function createNewSession(title: string = "New Chat") {
    const session = await createSession(title);
    sessions.value.unshift(session);
    currentSessionId.value = session.id;
    return session;
  }
  
  async function removeSession(id: string) {
    await deleteSession(id);
    sessions.value = sessions.value.filter(s => s.id !== id);
    if (currentSessionId.value === id) {
      currentSessionId.value = null;
    }
    delete messagesBySession.value[id];
    delete uiMessagesBySession.value[id];
    delete statusBySession.value[id];
  }
  
  function setCurrentSession(id: string) {
    currentSessionId.value = id;
  }
  function setStatus(id: string, st: 'ready' | 'submitted' | 'streaming') {
    statusBySession.value[id] = st;
  }
  function getStatus(id: string | null): 'ready' | 'submitted' | 'streaming' {
    if (!id) return 'ready';
    return statusBySession.value[id] || 'ready';
  }
  function setMessages(id: string, msgs: ChatMessage[]) {
    messagesBySession.value[id] = msgs.slice();
  }
  function appendMessage(id: string, msg: ChatMessage) {
    const list = messagesBySession.value[id] || [];
    messagesBySession.value[id] = [...list, msg];
  }
  function getMessages(id: string | null): ChatMessage[] {
    if (!id) return [];
    return messagesBySession.value[id] || [];
  }

  function setUiMessages(id: string, msgs: any[]) {
    uiMessagesBySession.value[id] = Array.isArray(msgs) ? msgs.slice() : [];
  }

  function getUiMessages(id: string | null): any[] | undefined {
    if (!id) return undefined;
    return uiMessagesBySession.value[id];
  }
  
  return {
    sessions,
    currentSessionId,
    messagesBySession,
    uiMessagesBySession,
    statusBySession,
    loadSessions,
    createNewSession,
    removeSession,
    setCurrentSession,
    setStatus,
    getStatus,
    setMessages,
    appendMessage,
    getMessages,
    setUiMessages,
    getUiMessages
  };
}, {
  persist: {
    paths: ['sessions', 'currentSessionId', 'messagesBySession', 'uiMessagesBySession', 'statusBySession']
  }
});
