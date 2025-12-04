<template>
  <div class="flex flex-col h-screen bg-gray-900 text-white">
    <!-- Header -->
    <header class="p-4 border-b border-gray-700 bg-gray-800 flex items-center gap-2">
      <div class="w-3 h-3 rounded-full bg-green-500"></div>
      <h1 class="text-xl font-bold">Agentic RAG Chat</h1>
    </header>

    <!-- Messages -->
    <div class="flex-1 overflow-y-auto p-4 space-y-6" ref="messagesContainer">
      <div v-for="(msg, index) in messages" :key="index" 
           :class="['flex', msg.role === 'user' ? 'justify-end' : 'justify-start']">
        <div :class="['max-w-[85%] rounded-xl p-5 shadow-lg', 
                      msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-100 border border-gray-700']">
          <div class="prose prose-invert max-w-none" v-html="renderMarkdown(msg.content)"></div>
          
          <!-- Citations -->
          <div v-if="msg.citations && msg.citations.length > 0" class="mt-4 border-t border-gray-600 pt-3">
            <p class="text-xs font-bold text-gray-400 mb-2 uppercase tracking-wider flex items-center gap-1">
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
              Sources
            </p>
            <div class="grid gap-2">
              <div v-for="cite in msg.citations" :key="cite.file_id + '_' + cite.chunk_index" 
                   class="bg-gray-900/50 p-3 rounded-lg border border-gray-700/50 text-sm hover:bg-gray-900 transition-colors">
                <div class="flex justify-between items-baseline mb-1">
                  <span class="font-medium text-blue-400 text-xs truncate max-w-[200px]" :title="cite.filename">{{ cite.filename }}</span>
                  <span class="text-[10px] text-gray-500 bg-gray-800 px-1.5 py-0.5 rounded">Chunk {{ cite.chunk_index }}</span>
                </div>
                <div class="text-gray-400 text-xs leading-relaxed line-clamp-3 italic">"{{ cite.content }}"</div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div v-if="isLoading" class="flex justify-start animate-pulse">
        <div class="bg-gray-800 rounded-xl p-4 border border-gray-700 flex items-center gap-2">
          <div class="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
          <div class="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style="animation-delay: 150ms"></div>
          <div class="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style="animation-delay: 300ms"></div>
        </div>
      </div>
    </div>

    <!-- Input -->
    <div class="p-4 bg-gray-800 border-t border-gray-700">
      <div class="max-w-4xl mx-auto">
        <form @submit.prevent="sendMessage" class="relative flex items-center">
          <input v-model="inputMessage" 
                 type="text" 
                 class="w-full bg-gray-900 border border-gray-600 rounded-xl py-3 pl-4 pr-12 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
                 placeholder="Message Agentic RAG..."
                 :disabled="isLoading" />
          <button type="submit" 
                  class="absolute right-2 p-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg disabled:opacity-50 disabled:hover:bg-blue-600 transition-colors"
                  :disabled="isLoading || !inputMessage.trim()">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
          </button>
        </form>
        <div class="text-center text-xs text-gray-500 mt-2">
          Powered by LangGraph & CopilotKit
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch } from 'vue';
import axios from 'axios';
import { marked } from 'marked';

interface Citation {
  file_id: number;
  chunk_index: number;
  filename: string;
  content: string;
}

interface Message {
  role: 'user' | 'ai';
  content: string;
  citations?: Citation[];
}

const messages = ref<Message[]>([]);
const inputMessage = ref('');
const isLoading = ref(false);
const messagesContainer = ref<HTMLElement | null>(null);

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
    }
  });
};

watch(messages.value, scrollToBottom);

const renderMarkdown = (text: string) => {
  return marked(text);
};

const sendMessage = async () => {
  if (!inputMessage.value.trim() || isLoading.value) return;

  const userText = inputMessage.value;
  messages.value.push({ role: 'user', content: userText });
  inputMessage.value = '';
  isLoading.value = true;
  scrollToBottom();

  try {
    const response = await axios.post('http://localhost:8000/chat', {
      message: userText
    });

    const data = response.data;
    console.log("Agent response:", data);
    
    let answer = '';
    let citations: Citation[] = [];

    // Handle RAGAnswer structure
    if (data.answer) {
        answer = data.answer;
        citations = data.citations || [];
    } 
    // Handle LangGraph state (messages list)
    else if (data.messages && Array.isArray(data.messages)) {
        const lastMsg = data.messages[data.messages.length - 1];
        if (typeof lastMsg.content === 'string') {
            answer = lastMsg.content;
        } else {
            // Structured output sometimes in additional_kwargs or tool_calls
            answer = JSON.stringify(lastMsg);
        }
    }
    // Fallback
    else {
        answer = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
    }

    messages.value.push({
      role: 'ai',
      content: answer,
      citations: citations
    });
  } catch (error) {
    messages.value.push({
      role: 'ai',
      content: 'Error: Failed to get response from agent. Please ensure the backend is running.',
    });
    console.error(error);
  } finally {
    isLoading.value = false;
    scrollToBottom();
  }
};
</script>

<style>
/* Custom scrollbar */
::-webkit-scrollbar {
  width: 8px;
}
::-webkit-scrollbar-track {
  background: #1f2937; 
}
::-webkit-scrollbar-thumb {
  background: #4b5563; 
  border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
  background: #6b7280; 
}
</style>
