<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import { aguiClient, type TextMessageContent } from '../services/agui'
import MarkdownIt from 'markdown-it'
import { UserOutlined, RobotOutlined, SendOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'

const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
})

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  isStreaming?: boolean
}

const messages = ref<ChatMessage[]>([])
const inputValue = ref('')
const isStreaming = ref(false)
const messagesEndRef = ref<HTMLElement | null>(null)

const scrollToBottom = async () => {
  await nextTick()
  messagesEndRef.value?.scrollIntoView({ behavior: 'smooth' })
}

watch(
  () => messages.value.length,
  () => scrollToBottom(),
)
watch(
  () => messages.value[messages.value.length - 1]?.content,
  () => scrollToBottom(),
)

onMounted(() => {
  // Subscribe to AG-UI events
  aguiClient.onTextMessageStartEvent((e) => {
    isStreaming.value = true
    messages.value.push({
      id: e.id,
      role: 'assistant',
      content: '',
      isStreaming: true,
    })
  })

  aguiClient.onTextMessageContentEvent((e: TextMessageContent) => {
    const lastMsg = messages.value[messages.value.length - 1]
    if (lastMsg && lastMsg.id === e.id) {
      lastMsg.content += e.delta
    }
  })

  aguiClient.onTextMessageEndEvent((e) => {
    const lastMsg = messages.value[messages.value.length - 1]
    if (lastMsg && lastMsg.id === e.id) {
      lastMsg.content = e.content // Ensure consistency
      lastMsg.isStreaming = false
    }
    isStreaming.value = false
  })
})

const handleSend = async () => {
  if (!inputValue.value.trim()) return
  if (isStreaming.value) {
    message.warning('请等待当前回答完成')
    return
  }

  const text = inputValue.value
  inputValue.value = ''

  // Add user message immediately
  messages.value.push({
    id: crypto.randomUUID(),
    role: 'user',
    content: text,
  })

  try {
    await aguiClient.sendUserMessage(text)
  } catch (err) {
    console.error(err)
    message.error('发送失败')
  }
}
</script>

<template>
  <a-layout class="chat-layout">
    <a-layout-header class="header">
      <div class="logo">AG-UI Assistant</div>
    </a-layout-header>
    
    <a-layout-content class="content">
      <div class="messages-container">
        <div v-if="messages.length === 0" class="empty-state">
          <a-typography-title :level="3">👋 你好！我是你的 AI 助手</a-typography-title>
          <a-typography-text type="secondary">请在下方输入问题开始对话...</a-typography-text>
        </div>

        <div
          v-for="msg in messages"
          :key="msg.id"
          class="message-row"
          :class="msg.role"
        >
          <div class="avatar-wrapper">
            <a-avatar 
              :style="{ backgroundColor: msg.role === 'user' ? '#1890ff' : '#52c41a' }"
            >
              <template #icon>
                <UserOutlined v-if="msg.role === 'user'" />
                <RobotOutlined v-else />
              </template>
            </a-avatar>
          </div>
          
          <div class="bubble-wrapper">
            <div class="bubble">
              <div v-if="msg.role === 'user'">{{ msg.content }}</div>
              <div v-else class="markdown-body" v-html="md.render(msg.content)"></div>
            </div>
            <div v-if="msg.isStreaming" class="streaming-indicator">
              <a-spin size="small" /> 正在思考...
            </div>
          </div>
        </div>
        <div ref="messagesEndRef" style="height: 1px"></div>
      </div>
    </a-layout-content>

    <a-layout-footer class="footer">
      <div class="input-container">
        <a-textarea
          v-model:value="inputValue"
          placeholder="输入消息..."
          :auto-size="{ minRows: 1, maxRows: 4 }"
          @pressEnter.prevent="handleSend"
          :disabled="isStreaming"
        />
        <a-button 
          type="primary" 
          shape="circle" 
          @click="handleSend"
          :disabled="!inputValue.trim() || isStreaming"
          class="send-btn"
        >
          <template #icon><SendOutlined /></template>
        </a-button>
      </div>
    </a-layout-footer>
  </a-layout>
</template>

<style scoped>
.chat-layout {
  height: 100vh;
  background: #f0f2f5;
}

.header {
  background: #fff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
  z-index: 10;
  display: flex;
  align-items: center;
  padding: 0 24px;
}

.logo {
  font-size: 18px;
  font-weight: bold;
  color: #333;
}

.content {
  padding: 24px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.messages-container {
  flex: 1;
  max-width: 800px;
  width: 100%;
  margin: 0 auto;
}

.empty-state {
  text-align: center;
  margin-top: 100px;
  opacity: 0.6;
}

.message-row {
  display: flex;
  margin-bottom: 24px;
  gap: 12px;
}

.message-row.user {
  flex-direction: row-reverse;
}

.avatar-wrapper {
  flex-shrink: 0;
}

.bubble-wrapper {
  max-width: 80%;
  display: flex;
  flex-direction: column;
}

.message-row.user .bubble-wrapper {
  align-items: flex-end;
}

.bubble {
  background: #fff;
  padding: 12px 16px;
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
  font-size: 15px;
  line-height: 1.6;
  word-break: break-word;
}

.message-row.user .bubble {
  background: #1890ff;
  color: #fff;
  border-top-right-radius: 2px;
}

.message-row.assistant .bubble {
  border-top-left-radius: 2px;
}

.streaming-indicator {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.footer {
  background: #fff;
  border-top: 1px solid #e8e8e8;
  padding: 16px 24px;
}

.input-container {
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.send-btn {
  flex-shrink: 0;
}

/* Basic Markdown Styles */
:deep(.markdown-body) {
  color: #333;
}
:deep(.markdown-body p) {
  margin-bottom: 8px;
}
:deep(.markdown-body p:last-child) {
  margin-bottom: 0;
}
:deep(.markdown-body pre) {
  background: #f6f8fa;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 8px 0;
}
:deep(.markdown-body code) {
  font-family: monospace;
  background: rgba(0,0,0,0.05);
  padding: 2px 4px;
  border-radius: 3px;
}
</style>