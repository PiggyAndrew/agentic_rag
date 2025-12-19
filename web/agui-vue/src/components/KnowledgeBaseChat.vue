<script setup lang="ts">
import type { PromptInputMessage } from "@/components/ai-elements/prompt-input";
import type { ChatStatus, ToolUIPart } from "ai";
import {
  Conversation,
  ConversationContent,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation";
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
} from "@/components/ai-elements/message";
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
} from "@/components/ai-elements/model-selector";
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
} from "@/components/ai-elements/prompt-input";
import {
  Reasoning,
  ReasoningContent,
  ReasoningTrigger,
} from "@/components/ai-elements/reasoning";
import {
  InlineCitation,
  InlineCitationCard,
  InlineCitationCardBody,
  InlineCitationCardTrigger,
  InlineCitationCarousel,
  InlineCitationCarouselContent,
  InlineCitationCarouselHeader,
  InlineCitationCarouselIndex,
  InlineCitationCarouselItem,
  InlineCitationCarouselNext,
  InlineCitationCarouselPrev,
  InlineCitationSource,
  InlineCitationText,
} from "@/components/ai-elements/inline-citation";
import {
  Source,
  Sources,
  SourcesContent,
  SourcesTrigger,
} from "@/components/ai-elements/sources";
import { Suggestion, Suggestions } from "@/components/ai-elements/suggestion";
import { CheckIcon, GlobeIcon, MicIcon } from "lucide-vue-next";
import { streamChat } from "@/api/chat";
import { nanoid } from "nanoid";
import { computed, ref } from "vue";
import {
  Tool,
  ToolContent,
  ToolHeader,
  ToolInput,
  ToolOutput,
} from "@/components/ai-elements/tool";
interface MessageVersion {
  id: string;
  content: string;
}

interface MessageSource {
  href: string;
  title: string;
}

interface MessageCitation {
  file_id: number;
  chunk_index: number;
  filename: string;
  content: string;
}

interface MessageReasoning {
  content: string;
  duration: number;
}

interface MessageTool {
  toolCallId: string;
  type: string;
  name: string;
  description: string;
  state: string;
  input: Record<string, unknown>;
  output?: string;
  error?: string;
}

interface MessageType {
  key: string;
  from: "user" | "assistant";
  sources?: MessageSource[];
  citations?: MessageCitation[];
  versions: MessageVersion[];
  reasoning?: MessageReasoning;
  tools?: MessageTool[];
}

interface Model {
  id: string;
  name: string;
  chef: string;
  chefSlug: string;
  providers: string[];
}

const models: Model[] = [
  {
    id: "deepseek",
    name: "deepseek-chat",
    chef: "Deepseek",
    chefSlug: "deepseek",
    providers: ["deepseek"],
  },
];

const suggestions = [];

const modelId = ref<string>(models[0].id);
const modelSelectorOpen = ref(false);
const useWebSearch = ref(false);
const useMicrophone = ref(false);
const status = ref<ChatStatus>("ready");
const messages = ref<MessageType[]>([]);

const selectedModelData = computed(() =>
  models.find((m) => m.id === modelId.value)
);

function updateStreamingContent(versionId: string, content: string) {
  const target = messages.value.find((msg) =>
    msg.versions.some((version) => version.id === versionId)
  );
  if (!target) return;
  const version = target.versions.find((v) => v.id === versionId);
  if (!version) return;
  version.content = content;
  messages.value = [...messages.value];
}

function normalizeToolOutput(value: any): any {
  if (value == null) return value;
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value;
  if (typeof value === "object") {
    const content = (value as any).content;
    if (typeof content === "string") return content;
    const output = (value as any).output;
    if (typeof output === "string") return output;
    return value;
  }
  return String(value);
}

function updateStreamingTool(versionId: string, toolEvent: any) {
  /**
   * 将后端工具事件映射到前端工具列表，仅更新工具面板，不将工具结果注入消息文本
   */
  const target = messages.value.find((msg) =>
    msg.versions.some((version) => version.id === versionId)
  );
  if (!target) return;

  if (!target.tools) target.tools = [];

  const { type, tool, input, output, id, error } = toolEvent;

  if (type === "tool_start") {
    target.tools = [
      ...target.tools,
      {
        toolCallId: id,
        type: `${tool}`,
        name: tool,
        description: `Calling ${tool}...`,
        state: "input-available",
        input: input || {},
      },
    ];
  } else if (type === "tool_end") {
    const t =
      target.tools.find((t) => t.toolCallId === id) ||
      target.tools
        .slice()
        .reverse()
        .find((t) => t.name === tool && t.state === "call");
    if (t) {
      t.state = "output-available";
      const normalized = normalizeToolOutput(output);
      t.output =
        typeof normalized === "string"
          ? normalized
          : JSON.stringify(normalized, null, 2);
      if (error) {
        t.state = "output-error";
        t.error = String(error);
      }
      target.tools = [...target.tools];
    }
  }
  messages.value = [...messages.value];
}

function updateStreamingCitations(versionId: string, payload: any) {
  const target = messages.value.find((msg) =>
    msg.versions.some((version) => version.id === versionId)
  );
  if (!target) return;

  const citations = Array.isArray(payload?.citations) ? payload.citations : [];
  target.citations = citations.map((c: any) => ({
    file_id: Number(c?.file_id ?? 0),
    chunk_index: Number(c?.chunk_index ?? 0),
    filename: String(c?.filename ?? ""),
    content: String(c?.content ?? ""),
  }));

  target.sources = target.citations.map((c) => ({
    href: `kb://file/${c.file_id}#chunk=${c.chunk_index}`,
    title: `${c.filename || "unknown"} #${c.chunk_index}`,
  }));

  messages.value = [...messages.value];
}

async function streamResponse(versionId: string) {
  status.value = "streaming";
  // 构造历史消息（仅取每条消息的最新版本）
  const history = messages.value.map((m) => ({
    role: m.from,
    content: m.versions[m.versions.length - 1]?.content || "",
  }));
  try {
    const iter = await streamChat(history);
    let acc = "";
    for await (const ev of iter) {
      if (ev.type === "text") {
        const chunk = normalizeTextChunk(ev.data);
        acc += chunk;
        updateStreamingContent(versionId, acc);
      } else if (ev.type === "error") {
        acc += `\n[Error] ${ev.data}`;
        updateStreamingContent(versionId, acc);
      } else if (ev.type === "data") {
        if (Array.isArray(ev.data)) {
          for (const item of ev.data) {
            if (item?.type === "tool_start" || item?.type === "tool_end") {
              updateStreamingTool(versionId, item);
            } else if (item?.type === "citations") {
              updateStreamingCitations(versionId, item);
            }
          }
        }
      }
    }
  } catch (e: any) {
    updateStreamingContent(versionId, `请求失败: ${e?.message || e}`);
  } finally {
    status.value = "ready";
  }
}

/**
 * 规范化后端流式文本片段：
 * - 若是 JSON 字符串或对象，优先提取 answer/content/preview 等可读字段
 * - 其余情况回退为字符串化
 */
function normalizeTextChunk(value: unknown): string {
  if (typeof value === "string") {
    const trimmed = value.trim();
    const looksLikeJson =
      (trimmed.startsWith("{") && trimmed.endsWith("}")) ||
      (trimmed.startsWith("[") && trimmed.endsWith("]"));
    if (looksLikeJson) {
      try {
        const obj = JSON.parse(trimmed);
        return extractText(obj);
      } catch {
        return value;
      }
    }
    return value;
  }
  // 对象或数组：提取可读内容
  if (value && typeof value === "object") {
    return extractText(value as any);
  }
  return String(value ?? "");
}

/**
 * 从对象中尽可能提取可读文本：
 * - 优先 answer、content 等字段
 * - 数组则拼接 preview/content 字段
 * - 回退为 JSON 字符串
 */
function extractText(obj: any): string {
  if (obj == null) return "";
  if (typeof obj === "string") return obj;
  if (Array.isArray(obj)) {
    const parts = obj
      .map((item) => {
        if (item == null) return "";
        if (typeof item === "string") return item;
        if (typeof item === "object") {
          return (
            item.preview || item.content || item.answer || item.title || ""
          );
        }
        return String(item);
      })
      .filter(Boolean);
    return parts.join("\n");
  }
  if (typeof obj === "object") {
    for (const key of ["answer", "content", "message", "text"]) {
      if (typeof obj[key] === "string") return obj[key];
    }
    // 如果存在 messages 列表，取最后一条的 content
    const msgs = obj.messages || obj.message;
    if (Array.isArray(msgs) && msgs.length) {
      const last = msgs[msgs.length - 1];
      if (last && typeof last.content === "string") return last.content;
    }
    try {
      return JSON.stringify(obj);
    } catch {
      return String(obj);
    }
  }
  return String(obj);
}

function addUserMessage(content: string) {
  const timestamp = Date.now();
  const userMessage: MessageType = {
    key: `user-${timestamp}`,
    from: "user",
    versions: [
      {
        id: `user-${timestamp}`,
        content,
      },
    ],
  };

  messages.value = [...messages.value, userMessage];

  setTimeout(() => {
    const assistantVersionId = `assistant-${Date.now()}`;
    const assistantMessage: MessageType = {
      key: `assistant-${Date.now()}`,
      from: "assistant",
      versions: [
        {
          id: assistantVersionId,
          content: "",
        },
      ],
    };

    messages.value = [...messages.value, assistantMessage];
    streamResponse(assistantVersionId);
  }, 200);
}

function handleSubmit(message: PromptInputMessage) {
  const text = message.text.trim();
  const hasText = text.length > 0;
  const hasAttachments = message.files.length > 0;

  if (!hasText && !hasAttachments) return;

  status.value = "submitted";

  addUserMessage(hasText ? text : "Sent with attachments");
}

function handleSuggestionClick(suggestion: string) {
  status.value = "submitted";
  addUserMessage(suggestion);
}

function handleModelSelect(id: string) {
  modelId.value = id;
  modelSelectorOpen.value = false;
}

function toggleMicrophone() {
  useMicrophone.value = !useMicrophone.value;
}

function toggleWebSearch() {
  useWebSearch.value = !useWebSearch.value;
}
</script>

<template>
  <div class="relative flex h-full w-full flex-col overflow-hidden">
    <div class="flex-1 min-h-0 relative">
      <Conversation class="h-full">
        <ConversationContent class="h-full overflow-y-auto px-4">
          <MessageBranch
            v-for="message in messages"
            :key="message.key"
            :default-branch="0"
          >
            <MessageBranchContent>
              <Message
                v-if="message.versions.length > 0"
                :key="`${message.key}-${
                  message.versions[message.versions.length - 1].id
                }`"
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

                  <div
                    v-if="message.tools && message.tools.length"
                    class="flex flex-col gap-2 pb-2"
                  >
                    <Tool v-for="tool in message.tools" :key="tool.toolCallId">
                      <ToolHeader
                        :state="tool.state"
                        :title="tool.name"
                        :type="tool.type"
                      />

                      <ToolContent>
                        <ToolInput :input="tool.input" />
                        <ToolOutput
                          :output="tool.output"
                          :error-text="tool.error"
                        />
                      </ToolContent>
                    </Tool>
                  </div>

                  <MessageContent>
                    <MessageResponse
                      :content="
                        message.versions[message.versions.length - 1].content
                      "
                    />
                    <div
                      v-if="message.citations && message.citations.length"
                      class="mt-3 text-sm leading-relaxed"
                    >
                      <InlineCitation>
                        <InlineCitationText>
                          已引用 {{ message.citations.length }} 个证据片段
                        </InlineCitationText>
                        <InlineCitationCard>
                          <InlineCitationCardTrigger
                            :sources="
                              message.citations.map(
                                (c) =>
                                  `kb://file/${c.file_id}#chunk=${c.chunk_index}`
                              )
                            "
                          />
                          <InlineCitationCardBody>
                            <InlineCitationCarousel>
                              <InlineCitationCarouselHeader>
                                <InlineCitationCarouselPrev />
                                <InlineCitationCarouselNext />
                                <InlineCitationCarouselIndex />
                              </InlineCitationCarouselHeader>
                              <InlineCitationCarouselContent>
                                <InlineCitationCarouselItem
                                  v-for="c in message.citations"
                                  :key="`${c.file_id}-${c.chunk_index}`"
                                >
                                  <InlineCitationSource
                                    :description="c.content"
                                    :title="`${c.filename || 'unknown'} #${
                                      c.chunk_index
                                    }`"
                                    :url="`kb://file/${c.file_id}#chunk=${c.chunk_index}`"
                                  />
                                </InlineCitationCarouselItem>
                              </InlineCitationCarouselContent>
                            </InlineCitationCarousel>
                          </InlineCitationCardBody>
                        </InlineCitationCard>
                      </InlineCitation>
                    </div>
                  </MessageContent>
                </div>
              </Message>
            </MessageBranchContent>
            <MessageToolbar v-if="message.from === 'assistant'">
              <MessageBranchSelector :from="message.from">
                <MessageBranchPrevious />
                <MessageBranchPage />
                <MessageBranchNext />
              </MessageBranchSelector>

              <MessageActions>
                <MessageAction label="Retry" tooltip="Regenerate response">
                  <RefreshCcwIcon class="size-4" />
                </MessageAction>

                <MessageAction label="Like" tooltip="Like this response">
                  <ThumbsUpIcon class="size-4" />
                </MessageAction>

                <MessageAction label="Dislike" tooltip="Dislike this response">
                  <ThumbsDownIcon class="size-4" />
                </MessageAction>

                <MessageAction label="Copy" tooltip="Copy to clipboard">
                  <CopyIcon class="size-4" />
                </MessageAction>
              </MessageActions>
            </MessageToolbar>
          </MessageBranch>
        </ConversationContent>
        <ConversationScrollButton />
      </Conversation>
    </div>

    <div class="shrink-0 border-t bg-background pt-4">
      <Suggestions class="px-4 pb-2">
        <Suggestion
          v-for="suggestion in suggestions"
          :key="suggestion"
          :suggestion="suggestion"
          @click="handleSuggestionClick"
        />
      </Suggestions>

      <div class="w-full px-4 pb-4">
        <PromptInput class="w-full" multiple global-drop @submit="handleSubmit">
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
                        v-for="m in models.filter(
                          (model) => model.chef === chef
                        )"
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
