<script setup lang="ts">
import type { PromptInputMessage } from '@/components/ai-elements/prompt-input'
import type { ChatStatus, ToolUIPart } from 'ai'
import { Conversation, ConversationContent, ConversationScrollButton } from '@/components/ai-elements/conversation'
import {
  Message,
  MessageBranch,
  MessageBranchContent,
  MessageBranchNext,
  MessageBranchPage,
  MessageBranchPrevious,
  MessageBranchSelector,
  MessageContent,
  MessageResponse,
} from '@/components/ai-elements/message'
import {
  ModelSelector,
  ModelSelectorContent,
  ModelSelectorEmpty,
  ModelSelectorGroup,
  ModelSelectorInput,
  ModelSelectorItem,
  ModelSelectorList,
  ModelSelectorLogo,
  ModelSelectorLogoGroup,
  ModelSelectorName,
  ModelSelectorTrigger,
} from '@/components/ai-elements/model-selector'
import {
  PromptInput,
  PromptInputActionAddAttachments,
  PromptInputActionMenu,
  PromptInputActionMenuContent,
  PromptInputActionMenuTrigger,
  PromptInputAttachment,
  PromptInputAttachments,
  PromptInputBody,
  PromptInputButton,
  PromptInputFooter,
  PromptInputHeader,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputTools,
} from '@/components/ai-elements/prompt-input'
import { Reasoning, ReasoningContent, ReasoningTrigger } from '@/components/ai-elements/reasoning'
import { Source, Sources, SourcesContent, SourcesTrigger } from '@/components/ai-elements/sources'
import { Suggestion, Suggestions } from '@/components/ai-elements/suggestion'
import { CheckIcon, GlobeIcon, MicIcon } from 'lucide-vue-next'
import { streamChat } from '@/api/chat'
import { nanoid } from 'nanoid'
import { computed, ref } from 'vue'

interface MessageVersion {
  id: string
  content: string
}

interface MessageSource {
  href: string
  title: string
}

interface MessageReasoning {
  content: string
  duration: number
}

interface MessageTool {
  name: string
  description: string
  status: ToolUIPart['state']
  parameters: Record<string, unknown>
  result?: string
  error?: string
}

interface MessageType {
  key: string
  from: 'user' | 'assistant'
  sources?: MessageSource[]
  versions: MessageVersion[]
  reasoning?: MessageReasoning
  tools?: MessageTool[]
}

interface Model {
  id: string
  name: string
  chef: string
  chefSlug: string
  providers: string[]
}

const initialMessages: MessageType[] = [
 
]

const models: Model[] = [
  {
    id: 'gpt-4o',
    name: 'GPT-4o',
    chef: 'OpenAI',
    chefSlug: 'openai',
    providers: ['openai', 'azure'],
  },
]

const suggestions = []



const modelId = ref<string>(models[0].id)
const modelSelectorOpen = ref(false)
const useWebSearch = ref(false)
const useMicrophone = ref(false)
const status = ref<ChatStatus>('ready')
const messages = ref<MessageType[]>(cloneMessages(initialMessages))

const selectedModelData = computed(() => models.find(m => m.id === modelId.value))

function cloneMessages(data: MessageType[]): MessageType[] {
  return data.map(message => ({
    ...message,
    versions: message.versions.map(version => ({ ...version })),
    sources: message.sources ? message.sources.map(source => ({ ...source })) : undefined,
    reasoning: message.reasoning ? { ...message.reasoning } : undefined,
    tools: message.tools
      ? message.tools.map(tool => ({
          ...tool,
          parameters: { ...tool.parameters },
        }))
      : undefined,
  }))
}

function updateStreamingContent(versionId: string, content: string) {
  const target = messages.value.find(msg => msg.versions.some(version => version.id === versionId))
  if (!target)
    return
  const version = target.versions.find(v => v.id === versionId)
  if (!version)
    return
  version.content = content
  messages.value = [...messages.value]
}

async function streamResponse(versionId: string) {
  status.value = 'streaming'
  // 构造历史消息（仅取每条消息的最新版本）
  const history = messages.value.map(m => ({
    role: m.from,
    content: m.versions[m.versions.length - 1]?.content || ''
  }))
  try {
    const iter = await streamChat(history)
    let acc = ''
    for await (const ev of iter) {
      if (ev.type === 'text') {
        const chunk = normalizeTextChunk(ev.data)
        acc += chunk
        updateStreamingContent(versionId, acc)
      } else if (ev.type === 'error') {
        acc += `\n[Error] ${ev.data}`
        updateStreamingContent(versionId, acc)
      }
      // 可选：处理工具事件 ev.type === 'data' 并映射到 message.tools
    }
  } catch (e: any) {
    updateStreamingContent(versionId, `请求失败: ${e?.message || e}`)
  } finally {
    status.value = 'ready'
  }
}

/**
 * 规范化后端流式文本片段：
 * - 若是 JSON 字符串或对象，优先提取 answer/content/preview 等可读字段
 * - 其余情况回退为字符串化
 */
function normalizeTextChunk(value: unknown): string {
  // 字符串：尝试解析为 JSON
  if (typeof value === 'string') {
    const trimmed = value.trim()
    try {
      const obj = JSON.parse(trimmed)
      return extractText(obj)
    } catch {
      return trimmed
    }
  }
  // 对象或数组：提取可读内容
  if (value && typeof value === 'object') {
    return extractText(value as any)
  }
  return String(value ?? '')
}

/**
 * 从对象中尽可能提取可读文本：
 * - 优先 answer、content 等字段
 * - 数组则拼接 preview/content 字段
 * - 回退为 JSON 字符串
 */
function extractText(obj: any): string {
  if (obj == null) return ''
  if (typeof obj === 'string') return obj
  if (Array.isArray(obj)) {
    const parts = obj.map(item => {
      if (item == null) return ''
      if (typeof item === 'string') return item
      if (typeof item === 'object') {
        return (
          item.preview || item.content || item.answer || item.title || ''
        )
      }
      return String(item)
    }).filter(Boolean)
    return parts.join('\n')
  }
  if (typeof obj === 'object') {
    for (const key of ['answer', 'content', 'message', 'text']) {
      if (typeof obj[key] === 'string') return obj[key]
    }
    // 如果存在 messages 列表，取最后一条的 content
    const msgs = obj.messages || obj.message
    if (Array.isArray(msgs) && msgs.length) {
      const last = msgs[msgs.length - 1]
      if (last && typeof last.content === 'string') return last.content
    }
    try {
      return JSON.stringify(obj)
    } catch {
      return String(obj)
    }
  }
  return String(obj)
}

function addUserMessage(content: string) {
  const timestamp = Date.now()
  const userMessage: MessageType = {
    key: `user-${timestamp}`,
    from: 'user',
    versions: [
      {
        id: `user-${timestamp}`,
        content,
      },
    ],
  }

  messages.value = [...messages.value, userMessage]

  setTimeout(() => {
    const assistantVersionId = `assistant-${Date.now()}`
    const assistantMessage: MessageType = {
      key: `assistant-${Date.now()}`,
      from: 'assistant',
      versions: [
        {
          id: assistantVersionId,
          content: '',
        },
      ],
    }

    messages.value = [...messages.value, assistantMessage]
    streamResponse(assistantVersionId)
  }, 200)
}

function handleSubmit(message: PromptInputMessage) {
  const text = message.text.trim()
  const hasText = text.length > 0
  const hasAttachments = message.files.length > 0

  if (!hasText && !hasAttachments)
    return

  status.value = 'submitted'

  addUserMessage(hasText ? text : 'Sent with attachments')
}

function handleSuggestionClick(suggestion: string) {
  status.value = 'submitted'
  addUserMessage(suggestion)
}

function handleModelSelect(id: string) {
  modelId.value = id
  modelSelectorOpen.value = false
}

function toggleMicrophone() {
  useMicrophone.value = !useMicrophone.value
}

function toggleWebSearch() {
  useWebSearch.value = !useWebSearch.value
}
</script>

<template>
  <div class="relative flex size-full flex-col divide-y overflow-hidden">
    <Conversation >
      <ConversationContent >
        <MessageBranch
          v-for="message in messages"
          :key="message.key"
          :default-branch="0"
        >
          <MessageBranchContent>
            <Message
              v-for="version in message.versions"
              :key="`${message.key}-${version.id}`"
              :from="message.from"
            >
              <div>
                <Sources v-if="message.sources?.length">
                  <SourcesTrigger :count="message.sources.length" />
                  <SourcesContent>
                    <Source
                      v-for="source in message.sources"
                      :key="source.href"
                      :href="source.href"
                      :title="source.title"
                    />
                  </SourcesContent>
                </Sources>

                <Reasoning
                  v-if="message.reasoning"
                  :duration="message.reasoning.duration"
                >
                  <ReasoningTrigger />
                  <ReasoningContent :content="message.reasoning.content" />
                </Reasoning>

                <MessageContent>
                  <MessageResponse :content="version.content" />
                </MessageContent>
              </div>
            </Message>
          </MessageBranchContent>

          <MessageBranchSelector
            v-if="message.versions.length > 1"
            :from="message.from"
          >
            <MessageBranchPrevious />
            <MessageBranchPage />
            <MessageBranchNext />
          </MessageBranchSelector>
        </MessageBranch>
      </ConversationContent>
      <ConversationScrollButton />
    </Conversation>

    <div class="grid shrink-0 gap-4 pt-4">
      <Suggestions class="px-4">
        <Suggestion
          v-for="suggestion in suggestions"
          :key="suggestion"
          :suggestion="suggestion"
          @click="handleSuggestionClick"
        />
      </Suggestions>

      <div class="w-full px-4 pb-4">
        <PromptInput
          class="w-full"
          multiple
          global-drop
          @submit="handleSubmit"
        >
          <PromptInputHeader>
            <PromptInputAttachments>
              <template #default="{ file }">
                <PromptInputAttachment :file="file" />
              </template>
            </PromptInputAttachments>
          </PromptInputHeader>

          <PromptInputBody>
            <PromptInputTextarea />
          </PromptInputBody>

          <PromptInputFooter>
            <PromptInputTools>
              <PromptInputActionMenu>
                <PromptInputActionMenuTrigger />
                <PromptInputActionMenuContent>
                  <PromptInputActionAddAttachments />
                </PromptInputActionMenuContent>
              </PromptInputActionMenu>

              <PromptInputButton
                :variant="useMicrophone ? 'default' : 'ghost'"
                @click="toggleMicrophone"
              >
                <MicIcon :size="16" />
                <span class="sr-only">Microphone</span>
              </PromptInputButton>

              <PromptInputButton
                :variant="useWebSearch ? 'default' : 'ghost'"
                @click="toggleWebSearch"
              >
                <GlobeIcon :size="16" />
                <span>Search</span>
              </PromptInputButton>

              <ModelSelector v-model:open="modelSelectorOpen">
                <ModelSelectorTrigger as-child>
                  <PromptInputButton>
                    <ModelSelectorLogo
                      v-if="selectedModelData?.chefSlug"
                      :provider="selectedModelData.chefSlug"
                    />
                    <ModelSelectorName v-if="selectedModelData?.name">
                      {{ selectedModelData.name }}
                    </ModelSelectorName>
                  </PromptInputButton>
                </ModelSelectorTrigger>

                <ModelSelectorContent>
                  <ModelSelectorInput placeholder="Search models..." />
                  <ModelSelectorList>
                    <ModelSelectorEmpty>No models found.</ModelSelectorEmpty>

                    <ModelSelectorGroup
                      v-for="chef in ['OpenAI']"
                      :key="chef"
                      :heading="chef"
                    >
                      <ModelSelectorItem
                        v-for="m in models.filter(model => model.chef === chef)"
                        :key="m.id"
                        :value="m.id"
                        @select="() => handleModelSelect(m.id)"
                      >
                        <ModelSelectorLogo :provider="m.chefSlug" />
                        <ModelSelectorName>{{ m.name }}</ModelSelectorName>
                        <ModelSelectorLogoGroup>
                          <ModelSelectorLogo
                            v-for="provider in m.providers"
                            :key="provider"
                            :provider="provider"
                          />
                        </ModelSelectorLogoGroup>
                        <CheckIcon
                          v-if="modelId === m.id"
                          class="ml-auto size-4"
                        />
                        <div v-else class="ml-auto size-4" />
                      </ModelSelectorItem>
                    </ModelSelectorGroup>
                  </ModelSelectorList>
                </ModelSelectorContent>
              </ModelSelector>
            </PromptInputTools>

            <PromptInputSubmit
              :disabled="status === 'streaming'"
              :status="status"
            />
          </PromptInputFooter>
        </PromptInput>
      </div>
    </div>
  </div>
</template>
