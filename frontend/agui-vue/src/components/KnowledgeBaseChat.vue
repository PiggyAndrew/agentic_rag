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
  Source,
  Sources,
  SourcesContent,
  SourcesTrigger,
} from "@/components/ai-elements/sources";
import { Suggestion, Suggestions } from "@/components/ai-elements/suggestion";
import { CheckIcon, GlobeIcon, PencilIcon } from "lucide-vue-next";
import { streamChat } from "@/api/chat";
import { computed, ref, onMounted, watch } from "vue";
import { useKbStore } from "@/stores/kb";
import { useAiStore } from "@/stores/ai";
import { ElRadioGroup, ElRadio, ElDialog, ElButton, ElInput } from "element-plus";
import {
  Tool,
  ToolContent,
  ToolHeader,
  ToolInput,
  ToolOutput,
} from "@/components/ai-elements/tool";
import ChunkViewerDialog from "@/components/ChunkViewerDialog.vue";
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
} from "@/components/ai-elements/inline-citation";
import { marked } from "marked";
/**
 * 事件类型：LangChain 原始事件的类封装
 */
/**
 * 从 LangChain 的 `AIMessageChunk` 中提取 tool call 的 args 流式片段
 */
function extractToolCallArgsFromChunk(chunk: any): string {
  const toolCallChunks = Array.isArray(chunk?.tool_call_chunks)
    ? chunk.tool_call_chunks
    : [];
  const invalidToolCalls = Array.isArray(chunk?.invalid_tool_calls)
    ? chunk.invalid_tool_calls
    : [];

  const fromToolCallChunks = toolCallChunks
    .map((c: any) => (typeof c?.args === "string" ? c.args : ""))
    .filter(Boolean);
  if (fromToolCallChunks.length > 0) return fromToolCallChunks.join("");

  const fromInvalidToolCalls = invalidToolCalls
    .map((c: any) => (typeof c?.args === "string" ? c.args : ""))
    .filter(Boolean);
  return fromInvalidToolCalls.join("");
}

type ChatModelStreamEvent = {
  kind: "on_chat_model_stream";
  text: string;
};

type LLMNewTokenEvent = {
  kind: "on_llm_new_token";
  token: string;
};

type ChatModelEndEvent = {
  kind: "on_chat_model_end";
  content: unknown;
};

type LLMEndEvent = {
  kind: "on_llm_end";
  content: unknown;
};

type ToolStartEvent = {
  kind: "on_tool_start";
  tool: string;
  input: any;
  id: string;
};

type ToolEndEvent = {
  kind: "on_tool_end";
  tool: string;
  output: any;
  id: string;
};

type ToolErrorEvent = {
  kind: "on_tool_error";
  tool: string;
  id: string;
  error: string;
};

type StreamErrorEvent = {
  kind: "error";
  error: string;
};

type LangChainEvent =
  | ChatModelStreamEvent
  | LLMNewTokenEvent
  | ChatModelEndEvent
  | LLMEndEvent
  | ToolStartEvent
  | ToolEndEvent
  | ToolErrorEvent
  | StreamErrorEvent;
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
  metadata?: Record<string, any>;
}

interface MessageReasoning {
  content: string;
  duration: number;
}

interface MessageTool {
  toolCallId: string;
  type: ToolUIPart["type"];
  name: string;
  description: string;
  state: ToolUIPart["state"];
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

const suggestions: string[] = [];

const defaultModelId = models[0]?.id || "";
const modelId = ref<string>(defaultModelId);
const modelSelectorOpen = ref(false);
const status = ref<ChatStatus>("ready");
const messages = ref<MessageType[]>([]);
const kbStore = useKbStore();
const aiStore = useAiStore();
const kbSelectorOpen = ref(false);
const selectedKbId = ref<string>("");
const abortController = ref<AbortController | null>(null);

function stopGeneration() {
  if (abortController.value) {
    abortController.value.abort();
    abortController.value = null;
    status.value = "ready";
  }
}

const apiBase = computed<string>(() => {
  const raw =
    (import.meta as any).env?.VITE_API_BASE ||
    (import.meta as any).env?.VITE_API_URL ||
    "http://localhost:8000";
  const s = String(raw).replace(/\/$/, "");
  if (s.endsWith("/api/chat")) return s.slice(0, -"/api/chat".length);
  if (s.endsWith("/api")) return s.slice(0, -"/api".length);
  return s;
});

const selectedModelData = computed(() =>
  models.find((m) => m.id === modelId.value)
);

type InlineCiteRef = { fileId: number; chunkIndex: number };

type InlinePart =
  | { kind: "text"; text: string }
  | { kind: "cite"; index: number; refs: InlineCiteRef[] };

function latestContent(message: MessageType): string {
  return message.versions[message.versions.length - 1]?.content || "";
}

function parseInlineCiteRef(s: string): InlineCiteRef | null {
  const m = s
    .trim()
    .match(
      /file(?:Id|_id)\s*=\s*(\d+)\s*,\s*chunk(?:Index|_index)\s*=\s*(\d+)/i
    );
  if (!m) return null;
  return { fileId: Number(m[1]), chunkIndex: Number(m[2]) };
}

function tokenizeInlineCitations(content: string): InlinePart[] {
  const text = content || "";
  const out: InlinePart[] = [];
  let cursor = 0;
  let idx = 0;
  while (cursor < text.length) {
    const start = text.indexOf("〔cite:", cursor);
    if (start === -1) {
      out.push({ kind: "text", text: text.slice(cursor) });
      break;
    }
    const end = text.indexOf("〕", start);
    if (end === -1) {
      out.push({ kind: "text", text: text.slice(cursor) });
      break;
    }
    if (start > cursor) out.push({ kind: "text", text: text.slice(cursor, start) });
    const inner = text.slice(start + "〔cite:".length, end);
    const refs = inner
      .split(";")
      .map(parseInlineCiteRef)
      .filter(Boolean) as InlineCiteRef[];
    idx += 1;
    out.push({ kind: "cite", index: idx, refs });
    cursor = end + 1;
  }
  return out;
}

function renderInlineMarkdown(text: string): string {
  const r = marked.parseInline(text || "");
  return typeof r === "string" ? r : "";
}

function normalizeCitationDescription(s: string): string {
  const text = (s || "").replace(/[\r\n]+/g, " ").trim();
  if (text.length <= 240) return text;
  return text.slice(0, 240) + "...";
}

function buildChunkUrl(fileId: number, chunkIndex: number): string {
  const kid = selectedKbId.value || kbStore.selectedKbId || "kb-1";
  return `${apiBase.value}/api/kb/${kid}/files/f-${fileId}/chunks#chunk=${chunkIndex}`;
}

function buildCitationItems(message: MessageType, refs: InlineCiteRef[]) {
  const uniq = new Map<string, InlineCiteRef>();
  for (const r of refs || []) {
    const key = `${r.fileId}:${r.chunkIndex}`;
    if (!uniq.has(key)) uniq.set(key, r);
  }
  return Array.from(uniq.values()).map((r) => {
    const found = message.citations?.find(
      (c) => Number(c.file_id) === r.fileId && Number(c.chunk_index) === r.chunkIndex
    );
    const url = buildChunkUrl(r.fileId, r.chunkIndex);
    const titleParts: string[] = [];
    if (found?.filename) titleParts.push(found.filename);
    titleParts.push(`#${r.chunkIndex}`);
    if (found?.metadata?.number) titleParts.push(String(found.metadata.number));
    if (found?.metadata?.title) titleParts.push(String(found.metadata.title));
    const title = titleParts.join(" ").trim();
    return {
      key: `${r.fileId}:${r.chunkIndex}`,
      title: title || `fileId=${r.fileId} chunkIndex=${r.chunkIndex}`,
      url,
      description: normalizeCitationDescription(found?.content || ""),
    };
  });
}

function collectChunksForRefs(message: MessageType, refs: InlineCiteRef[]) {
  const need = new Set(refs.map((r) => `${r.fileId}:${r.chunkIndex}`));
  const out: any[] = [];
  for (const c of message.citations || []) {
    const key = `${Number(c.file_id)}:${Number(c.chunk_index)}`;
    if (need.has(key)) {
      out.push({
        file_id: Number(c.file_id),
        chunk_index: Number(c.chunk_index),
        content: String(c.content || ""),
        metadata: c.metadata || undefined,
      });
    }
  }
  return out;
}

const citationDialogOpen = ref(false);
const citationDialogChunks = ref<any[]>([]);

function openCitationDialogForRefs(message: MessageType, refs: InlineCiteRef[]) {
  citationDialogChunks.value = collectChunksForRefs(message, refs);
  citationDialogOpen.value = true;
}

function parseToolChunks(output: any): MessageCitation[] {
  const normalized = normalizeToolOutput(output);
  const raw = typeof normalized === "string" ? normalized.trim() : normalized;
  let data: any = raw;
  if (typeof raw === "string") {
    try {
      data = JSON.parse(raw);
    } catch {
      return [];
    }
  }
  if (!Array.isArray(data)) return [];
  const out: MessageCitation[] = [];
  for (const item of data) {
    if (!item || typeof item !== "object") continue;
    const file_id = Number((item as any).file_id ?? (item as any).fileId);
    const chunk_index = Number((item as any).chunk_index ?? (item as any).chunkIndex);
    if (!Number.isFinite(file_id) || !Number.isFinite(chunk_index)) continue;
    out.push({
      file_id,
      chunk_index,
      filename: String((item as any).filename ?? "unknown"),
      content: String((item as any).content ?? ""),
      metadata:
        (item as any).metadata && typeof (item as any).metadata === "object"
          ? (item as any).metadata
          : undefined,
    });
  }
  return out;
}

function upsertMessageCitations(versionId: string, chunks: MessageCitation[]) {
  if (!chunks || chunks.length === 0) return;
  const target = messages.value.find((msg) =>
    msg.versions.some((version) => version.id === versionId)
  );
  if (!target) return;
  const current = target.citations ? [...target.citations] : [];
  const map = new Map<string, MessageCitation>();
  for (const c of current) map.set(`${c.file_id}:${c.chunk_index}`, c);
  for (const c of chunks) map.set(`${c.file_id}:${c.chunk_index}`, c);
  target.citations = Array.from(map.values());
  messages.value = [...messages.value];
}

/**
 * 解析后端原始事件为结构化对象
 */
function parseEvent(raw: any): LangChainEvent | null {
  const kind = raw?.event;
  if (!kind) return null;
  if (kind === "on_chat_model_stream") {
    const chunk = raw?.data?.chunk;
    const c = chunk?.content;
    if (typeof c === "string" && c.length > 0) {
      return { kind, text: c };
    }
    const args = extractToolCallArgsFromChunk(chunk);
    if (args) {
      return { kind, text: args };
    }
    return null;
  }
  if (kind === "on_llm_new_token") {
    const t = raw?.data?.token;
    if (typeof t === "string") {
      return { kind, token: t };
    }
    return null;
  }
  if (kind === "on_chat_model_end" || kind === "on_llm_end") {
    const c = raw?.data?.output?.content;
    if (c != null) {
      return { kind, content: c } as ChatModelEndEvent | LLMEndEvent;
    }
    return null;
  }
  if (kind === "on_tool_start") {
    const name = String(raw?.name ?? "");
    const id = String(raw?.run_id ?? "");
    const input = raw?.data?.input ?? {};
    if (name) {
      return { kind, tool: name, input, id };
    }
    return null;
  }
  if (kind === "on_tool_end") {
    const name = String(raw?.name ?? "");
    const id = String(raw?.run_id ?? "");
    const output = raw?.data?.output;
    if (name) {
      return { kind, tool: name, output, id };
    }
    return null;
  }
  if (kind === "on_tool_error") {
    const name = String(raw?.name ?? "");
    const id = String(raw?.run_id ?? "");
    const err = raw?.data?.error;
    const msg = typeof err === "string" ? err : String(err ?? "");
    if (name) {
      return { kind, tool: name, id, error: msg };
    }
    return null;
  }
  if (kind === "error") {
    const err = raw?.data?.error;
    const msg = typeof err === "string" ? err : String(err ?? "");
    if (msg) {
      return { kind, error: msg };
    }
    return null;
  }
  return null;
}

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

// function updateStreamingReasoning(versionId: string, content: string) {
//   const target = messages.value.find((msg) =>
//     msg.versions.some((version) => version.id === versionId)
//   );
//   if (!target) return;
//   target.reasoning = {
//     content,
//     duration: 0,
//   };
//   messages.value = [...messages.value];
// }

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
        type: `tool-${tool}`,
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
        .find((t) => t.name === tool && t.state === "input-available");
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

/**
 * 消费后端原始事件流（JSONL）并更新 UI：
 * - 文本：on_chat_model_stream / on_llm_new_token / on_*_end 的 content
 * - 工具：on_tool_start / on_tool_end / on_tool_error
 */
async function streamResponse(versionId: string) {
  status.value = "streaming";
  abortController.value = new AbortController();
  const history = messages.value.map((m) => ({
    role: m.from,
    content: m.versions[m.versions.length - 1]?.content || "",
  }));
  try {
    const iter = await streamChat(
      history,
      selectedKbId.value ? selectedKbId.value : undefined,
      {
        apiUrl: aiStore.chatApiUrl,
        llmApiKey: aiStore.llmApiKey,
        llmBaseUrl: aiStore.llmBaseUrl,
        llmModel: aiStore.llmModel,
        signal: abortController.value.signal,
      }
    );
    let acc = "";
    for await (const raw of iter) {
      const ev = parseEvent(raw);
      if (!ev) continue;
      if (ev.kind === "on_chat_model_stream") {
        acc += normalizeTextChunk(ev.text);
        updateStreamingContent(versionId, acc);
      }
      //  else if (ev.kind === "on_llm_new_token") {
      //   acc += String(ev.token);
      //   updateStreamingContent(versionId, acc);
      // } else if (ev.kind === "on_chat_model_end" || ev.kind === "on_llm_end") {
      //   acc += normalizeTextChunk(ev.content);
      //   updateStreamingContent(versionId, acc);
      //   updateStreamingReasoning(versionId, acc);
      // } 
      else if (ev.kind === "on_tool_start") {
        updateStreamingTool(versionId, {
          type: "tool_start",
          tool: ev.tool,
          input: ev.input || {},
          id: ev.id,
        });
      } else if (ev.kind === "on_tool_end") {
        updateStreamingTool(versionId, {
          type: "tool_end",
          tool: ev.tool,
          output: ev.output,
          id: ev.id,
        });
        if (ev.tool === "read_file_chunks" || ev.tool === "read_file_chunks_multi") {
          const chunks = parseToolChunks(ev.output);
          upsertMessageCitations(versionId, chunks);
        }
      } else if (ev.kind === "on_tool_error") {
        updateStreamingTool(versionId, {
          type: "tool_end",
          tool: ev.tool,
          output: null,
          id: ev.id,
          error: String(ev.error || "Tool error"),
        });
      } else if (ev.kind === "error") {
        acc += `\n[Error] ${ev.error}`;
        updateStreamingContent(versionId, acc);
      }
    }
  } catch (e: any) {
    if (e.name === 'AbortError') {
      // User aborted
      return;
    }
    updateStreamingContent(versionId, `请求失败: ${e?.message || e}`);
  } finally {
    status.value = "ready";
    abortController.value = null;
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

const editingMessageKey = ref<string | null>(null);
const editingContent = ref<string>("");

function triggerAssistantResponse() {
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

function startEditing(message: MessageType) {
  editingMessageKey.value = message.key;
  editingContent.value = latestContent(message);
}

function cancelEditing() {
  editingMessageKey.value = null;
  editingContent.value = "";
}

function submitEdit(key: string) {
  stopGeneration();
  const index = messages.value.findIndex((m) => m.key === key);
  if (index === -1) return;

  const msg = messages.value[index];
  if (!msg) return;

  const newContent = editingContent.value.trim();
  
  if (!newContent) return;

  // Add new version
  const newVersionId = `user-${Date.now()}`;
  msg.versions.push({
    id: newVersionId,
    content: newContent,
  });

  // Truncate subsequent messages
  messages.value = messages.value.slice(0, index + 1);

  cancelEditing();
  triggerAssistantResponse();
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

  triggerAssistantResponse();
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

onMounted(() => {
  kbStore.fetchKnowledgeBases();
});

/**
 * 默认选中第一个知识库：
 * - 在知识库列表加载完成时，如果当前未选择，则选中第一个
 * - 优先使用 Pinia 中的 selectedKbId 回填
 */
watch(
  () => kbStore.knowledgeBases,
  (list) => {
    if (Array.isArray(list) && list.length > 0 && !selectedKbId.value) {
      const defaultId = kbStore.selectedKbId || list[0]?.id;
      if (defaultId) selectedKbId.value = defaultId;
    }
  },
  { immediate: true }
);
</script>

<template>
  <div class="relative flex h-full w-full flex-col overflow-hidden bg-gray-50">
    <div class="flex-1 min-h-0 relative">
      <Conversation class="h-full">
        <ConversationContent class="h-full overflow-y-auto px-4 md:px-8 pt-6 pb-4 scroll-smooth">
          <div class="w-full space-y-8 pb-8">
            <MessageBranch
              v-for="message in messages"
              :key="message.key"
              :default-branch="0"
            >
            <MessageBranchContent>
              <Message
                v-if="message.versions.length > 0"
                :key="`${message.key}-${
                  message.versions[message.versions.length - 1]?.id || ''
                }`"
                :from="message.from"
                class="gap-4"
              >
                <div :class="message.from === 'user' ? 'w-full flex flex-col items-end' : 'w-full min-w-0'">
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

                  <Tool
                    v-for="tool in message.tools"
                    :key="tool.toolCallId"
                    v-if="message.tools && message.tools.length"
                  >
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

                  <template v-if="message.from === 'user'">
                    <div 
                      v-if="editingMessageKey === message.key" 
                      class="w-full max-w-2xl self-end bg-white dark:bg-zinc-900 p-4 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm transition-all"
                    >
                      <ElInput
                        v-model="editingContent"
                        type="textarea"
                        :autosize="{ minRows: 2, maxRows: 8 }"
                        class="mb-3 font-normal"
                        resize="none"
                        placeholder="输入修改后的内容..."
                      />
                      <div class="flex justify-end gap-2">
                        <ElButton size="small" round @click="cancelEditing">取消</ElButton>
                        <ElButton type="primary" size="small" round @click="submitEdit(message.key)">
                          发送
                        </ElButton>
                      </div>
                    </div>
                    <div v-else class="flex items-start gap-3 flex-row-reverse group is-user pl-10">
                      <div class="flex flex-col pt-1 opacity-0 group-hover:opacity-100 transition-all duration-200">
                        <button
                          class="p-2 rounded-full text-gray-400 hover:text-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 dark:hover:text-gray-200 transition-colors"
                          @click="startEditing(message)"
                          title="编辑消息"
                        >
                          <PencilIcon class="size-3.5" />
                        </button>
                      </div>
                      <MessageContent>
                        <div class="whitespace-pre-wrap">{{ latestContent(message) }}</div>
                      </MessageContent>
                    </div>
                  </template>

                  <MessageContent v-else>
                    <template
                      v-if="
                        message.from === 'assistant' &&
                        latestContent(message).includes('〔cite:')
                      "
                    >
                      <div class="whitespace-pre-wrap text-sm leading-relaxed">
                        <template
                          v-for="(part, pidx) in tokenizeInlineCitations(
                            latestContent(message)
                          )"
                          :key="pidx"
                        >
                          <span
                            v-if="part.kind === 'text'"
                            v-html="renderInlineMarkdown(part.text)"
                          />
                          <InlineCitation v-else class="inline-flex items-center">
                            <InlineCitationCard>
                              <InlineCitationCardTrigger
                                :label="`[${part.index}]`"
                                :sources="
                                  buildCitationItems(message, part.refs).map(
                                    (s) => s.url
                                  )
                                "
                              />
                              <InlineCitationCardBody>
                                <InlineCitationCarousel>
                                  <InlineCitationCarouselHeader>
                                    <InlineCitationCarouselPrev />
                                    <InlineCitationCarouselNext />
                                    <InlineCitationCarouselIndex />
                                    <ElButton
                                      size="small"
                                      type="primary"
                                      plain
                                      @click="openCitationDialogForRefs(message, part.refs)"
                                    >查看全部</ElButton>
                                  </InlineCitationCarouselHeader>
                                  <InlineCitationCarouselContent>
                                    <InlineCitationCarouselItem
                                      v-for="item in buildCitationItems(
                                        message,
                                        part.refs
                                      )"
                                      :key="item.key"
                                    >
                                      <InlineCitationSource
                                        :description="item.description"
                                        :title="item.title"
                                        :url="item.url"
                                      />
                                    </InlineCitationCarouselItem>
                                  </InlineCitationCarouselContent>
                                </InlineCitationCarousel>
                              </InlineCitationCardBody>
                            </InlineCitationCard>
                          </InlineCitation>
                        </template>
                      </div>
                    </template>
                    <MessageResponse v-else :content="latestContent(message)" />
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
          </div>
        </ConversationContent>
        <ConversationScrollButton />
      </Conversation>
    </div>

    <div class="shrink-0 border-t border-gray-100 bg-white/80 backdrop-blur-md py-4 z-10">
      <div class="w-full px-4 md:px-8">
        <Suggestions class="mb-3 px-1">
          <Suggestion
            v-for="suggestion in suggestions"
            :key="suggestion"
            :suggestion="suggestion"
            @click="handleSuggestionClick"
          />
        </Suggestions>

        <div class="w-full">
          <PromptInput class="w-full shadow-lg rounded-2xl border border-gray-200 bg-white ring-1 ring-black/5 transition-shadow hover:shadow-xl" multiple global-drop @submit="handleSubmit">
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

              <!-- <PromptInputButton
                :variant="useMicrophone ? 'default' : 'ghost'"
                @click="toggleMicrophone"
              >
                <MicIcon :size="16" />
                <span class="sr-only">Microphone</span>
              </PromptInputButton> -->

              <!-- <PromptInputButton
                :variant="useWebSearch ? 'default' : 'ghost'"
                @click="toggleWebSearch"
              >
                <GlobeIcon :size="16" />
                <span>Search</span>
              </PromptInputButton> -->

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

              <PromptInputButton @click="kbSelectorOpen = true">
                <GlobeIcon :size="16" />
                <span>Select Knowledge Base</span>
              </PromptInputButton>
            </PromptInputTools>

            <PromptInputSubmit
              :disabled="false"
              :status="status"
              @click="status === 'streaming' ? stopGeneration() : undefined"
            />
          </PromptInputFooter>
        </PromptInput>
        <ElDialog v-model="kbSelectorOpen" title="选择知识库" width="520px">
          <div class="px-2 py-2">
            <ElRadioGroup v-model="selectedKbId">
              <div class="grid grid-cols-2 gap-2">
                <ElRadio
                  v-for="kb in kbStore.knowledgeBases"
                  :key="kb.id"
                  :label="kb.id"
                >
                  {{ kb.name }}
                </ElRadio>
              </div>
            </ElRadioGroup>
          </div>
          <template #footer>
            <div class="flex justify-end gap-2">
              <ElButton @click="kbSelectorOpen = false">取消</ElButton>
              <ElButton type="primary" @click="kbSelectorOpen = false"
                >确定</ElButton
              >
            </div>
          </template>
        </ElDialog>
      </div>
      </div>
    </div>
  </div>

  <ChunkViewerDialog v-model="citationDialogOpen" :chunks="citationDialogChunks" />
</template>
