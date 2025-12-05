<script setup lang="ts">
import { useChat } from '@/hooks/useChat';


// 使用 ai SDK 的 useChat hook
// 默认端点为 /api/chat，已通过 vite proxy 转发到 localhost:8000
const { messages, input, handleSubmit, status } = useChat();
</script>

<template>
  <div class="flex flex-col h-screen bg-background text-foreground">
    <!-- Header -->
    <header class="flex items-center h-14 px-4 border-b shrink-0">
      <h1 class="text-lg font-semibold">Knowledge Base Chat</h1>
    </header>

    <!-- Chat Area -->
    <div class="flex-1 overflow-hidden">
      <Conversation class="h-full relative">
        <ConversationContent class="p-4 space-y-4 max-w-3xl mx-auto">
          
          <ConversationEmptyState v-if="messages.length === 0">
            <template #icon>
              <div class="w-12 h-12 bg-muted rounded-full flex items-center justify-center mb-4">
                <span class="text-2xl">🤖</span>
              </div>
            </template>
            <template #title>How can I help you today?</template>
            <template #description>
              Ask me anything about your knowledge base documents.
            </template>
          </ConversationEmptyState>

          <Message 
            v-for="m in messages" 
            :key="m.id"
            :from="m.role === 'user' ? 'user' : 'assistant'"
          >
            <MessageAvatar :fallback="m.role === 'user' ? 'ME' : 'AI'" />
            <MessageContent>
              <div class="prose dark:prose-invert text-sm" v-html="m.content"></div>
            </MessageContent>
            <MessageToolbar v-if="m.role === 'assistant'">
              <!-- Toolbar actions like copy, retry can be added here -->
            </MessageToolbar>
          </Message>

        </ConversationContent>
        <ConversationScrollButton />
      </Conversation>
    </div>

    <!-- Input Area -->
    <div class="p-4 border-t bg-background">
      <div class="max-w-3xl mx-auto">
        <PromptInput class="border rounded-xl shadow-sm bg-background">
          <PromptInputBody>
            <PromptInputTextarea 
              v-model="input" 
              placeholder="Type a message..." 
              @keydown.enter.exact.prevent="handleSubmit"
              :disabled="status === 'streaming'"
            />
          </PromptInputBody>
          <PromptInputFooter class="justify-between">
            <PromptInputTools>
              <PromptInputButton>
                <Paperclip class="w-4 h-4" />
                <span class="sr-only">Attach file</span>
              </PromptInputButton>
              <PromptInputButton>
                <Mic class="w-4 h-4" />
                <span class="sr-only">Voice input</span>
              </PromptInputButton>
            </PromptInputTools>
            <PromptInputSubmit @click="handleSubmit" :disabled="!input.trim() || status === 'streaming'">
              Send
            </PromptInputSubmit>
          </PromptInputFooter>
        </PromptInput>
        <div class="text-xs text-center text-muted-foreground mt-2">
          AI may make mistakes. Please review generated information.
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 确保 tailwind 样式生效 */
</style>
