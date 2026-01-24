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
  MessageAction,
  MessageActions,
  MessageToolbar,
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
  PromptInput,
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
import { GlobeIcon, PlusIcon, TrashIcon, MessageSquareIcon, RefreshCcwIcon, ThumbsUpIcon, ThumbsDownIcon, CopyIcon, PencilIcon } from "lucide-vue-next";
import { streamChat } from "@/api/chat";
import { computed, ref, onMounted, watch } from "vue";
import { useKbStore } from "@/stores/kb";
import { useAiStore } from "@/stores/ai";
import { useChatStore } from "@/stores/chat";
import { fetchMessages, editMessage } from "@/api/chat_history";
import type { ChatMessage } from "@/api/chat_history";
import { ElRadioGroup, ElRadio, ElDialog, ElButton, ElScrollbar, ElMessageBox, ElInput } from "element-plus";
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

const suggestions: string[] = [];
const status = ref<ChatStatus>("ready");
const messages = ref<MessageType[]>([]);
const kbStore = useKbStore();
const aiStore = useAiStore();
const chatStore = useChatStore();
const kbSelectorOpen = ref(false);
const selectedKbId = ref<string>("");
const abortControllersBySession = new Map<string, AbortController>();
const editingMessageIndex = ref<number | null>(null);
const editContent = ref<string>("");
const savingEdit = ref(false);

function toUiMessages(list: ChatMessage[]): MessageType[] {
  return list.map((msg) => ({
    key: `${msg.role}-${msg.id}`,
    from: (msg.role === "assistant" ? "assistant" : "user") as "user" | "assistant",
    versions: [{ id: `${msg.role}-${msg.id}`, content: msg.content }],
    citations: msg.citations,
  }));
}

function getSessionUiMessages(sessionId: string): MessageType[] {
  const cached = chatStore.getUiMessages(sessionId) as MessageType[] | undefined;
  if (Array.isArray(cached)) return cached as MessageType[];
  const base = toUiMessages(chatStore.getMessages(sessionId));
  chatStore.setUiMessages(sessionId, base as any);
  return base;
}

function setSessionUiMessages(sessionId: string, next: MessageType[]) {
  chatStore.setUiMessages(sessionId, next as any);
  if (chatStore.currentSessionId === sessionId) {
    messages.value = next;
  }
}

function updateStoredMessageContent(
  sessionId: string,
  messageId: number,
  content: string
) {
  const existing = chatStore.getMessages(sessionId);
  const idx = existing.findIndex((m) => m.id === messageId);
  if (idx < 0) return;
  const current = existing[idx];
  if (!current) return;
  const next = existing.slice();
  next[idx] = { ...current, content };
  chatStore.setMessages(sessionId, next);
}

function updateStoredMessageCitations(
  sessionId: string,
  messageId: number,
  citations: MessageCitation[]
) {
  const existing = chatStore.getMessages(sessionId);
  const idx = existing.findIndex((m) => m.id === messageId);
  if (idx < 0) return;
  const current = existing[idx];
  if (!current) return;
  const next = existing.slice();
  next[idx] = { ...current, citations };
  chatStore.setMessages(sessionId, next);
}

function stopGeneration() {
  const sessionId = chatStore.currentSessionId;
  if (!sessionId) return;
  const controller = abortControllersBySession.get(sessionId);
  if (controller) {
    controller.abort();
    abortControllersBySession.delete(sessionId);
  }
  status.value = "ready";
  chatStore.setStatus(sessionId, "ready");
}

async function createNewChat() {
  const session = await chatStore.createNewSession();
  chatStore.setMessages(session.id, []);
  chatStore.setUiMessages(session.id, []);
  chatStore.setStatus(session.id, "ready");
  messages.value = [];
  status.value = "ready";
}

async function handleDeleteSession(id: string) {
  try {
    await ElMessageBox.confirm(
      "确定要删除该会话吗？此操作不可撤销。",
      "删除确认",
      {
        confirmButtonText: "删除",
        cancelButtonText: "取消",
        type: "warning",
      }
    );
    const controller = abortControllersBySession.get(id);
    if (controller) {
      controller.abort();
      abortControllersBySession.delete(id);
    }
    await chatStore.removeSession(id);
  } catch {
    // 用户取消
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


type InlineCiteRef = { fileId: number; chunkIndex: number };

type InlinePart =
  | { kind: "text"; text: string }
  | { kind: "cite"; index: number; refs: InlineCiteRef[] };

function latestContent(message: MessageType): string {
  return message.versions[message.versions.length - 1]?.content || "";
}

function startEditing(index: number) {
  const target = messages.value[index];
  if (!target || target.from !== "user") return;
  editingMessageIndex.value = index;
  editContent.value = latestContent(target);
}

function cancelEditing() {
  editingMessageIndex.value = null;
  editContent.value = "";
}

async function saveEditing() {
  const sessionId = chatStore.currentSessionId;
  if (!sessionId) return;
  const idx = editingMessageIndex.value;
  if (idx === null) return;
  const content = editContent.value.trim();
  if (!content) return;
  if (savingEdit.value) return;
  savingEdit.value = true;
  stopGeneration();
  try {
    const latest = await fetchMessages(sessionId);
    if (latest.length > 0) {
      chatStore.setMessages(sessionId, latest);
      const uiLatest = toUiMessages(latest);
      chatStore.setUiMessages(sessionId, uiLatest as any);
      messages.value = uiLatest;
    }
    const current = chatStore.getMessages(sessionId);
    const target = current[idx];
    if (!target || target.role !== "user") {
      return;
    }
    await editMessage(sessionId, target.id, content);
    const updated = await fetchMessages(sessionId);
    chatStore.setMessages(sessionId, updated);
    const ui = toUiMessages(updated);
    chatStore.setUiMessages(sessionId, ui as any);
    messages.value = ui;
    editingMessageIndex.value = null;
    editContent.value = "";
    const assistantId = Date.now();
    const assistantVersionId = `assistant-${assistantId}`;
    const assistantMessage: MessageType = {
      key: `assistant-${assistantId}`,
      from: "assistant",
      versions: [{ id: assistantVersionId, content: "" }],
    };
    const nextMessages = [...messages.value, assistantMessage];
    setSessionUiMessages(sessionId, nextMessages);
    chatStore.appendMessage(sessionId, {
      id: assistantId,
      role: "assistant",
      content: "",
      createdAt: assistantId,
    });
    streamResponse(assistantVersionId, sessionId, assistantId, true);
  } finally {
    savingEdit.value = false;
  }
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

function upsertMessageCitations(
  sessionId: string,
  versionId: string,
  chunks: MessageCitation[]
) {
  if (!chunks || chunks.length === 0) return [];
  const sessionMessages = getSessionUiMessages(sessionId);
  const target = sessionMessages.find((msg) =>
    msg.versions.some((version) => version.id === versionId)
  );
  if (!target) return [];
  const current = target.citations ? [...target.citations] : [];
  const map = new Map<string, MessageCitation>();
  for (const c of current) map.set(`${c.file_id}:${c.chunk_index}`, c);
  for (const c of chunks) map.set(`${c.file_id}:${c.chunk_index}`, c);
  const nextCitations = Array.from(map.values());
  target.citations = nextCitations;
  setSessionUiMessages(sessionId, [...sessionMessages]);
  return nextCitations;
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

function updateStreamingContent(
  sessionId: string,
  versionId: string,
  content: string
) {
  const sessionMessages = getSessionUiMessages(sessionId);
  const target = sessionMessages.find((msg) =>
    msg.versions.some((version) => version.id === versionId)
  );
  if (!target) return;
  const version = target.versions.find((v) => v.id === versionId);
  if (!version) return;
  version.content = content;
  setSessionUiMessages(sessionId, [...sessionMessages]);
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

function updateStreamingTool(
  sessionId: string,
  versionId: string,
  toolEvent: any
) {
  /**
   * 将后端工具事件映射到前端工具列表，仅更新工具面板，不将工具结果注入消息文本
   */
  const sessionMessages = getSessionUiMessages(sessionId);
  const target = sessionMessages.find((msg) =>
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
  setSessionUiMessages(sessionId, [...sessionMessages]);
}

/**
 * 消费后端原始事件流（JSONL）并更新 UI：
 * - 文本：on_chat_model_stream / on_llm_new_token / on_*_end 的 content
 * - 工具：on_tool_start / on_tool_end / on_tool_error
 */
async function streamResponse(
  versionId: string,
  sessionId: string,
  assistantMessageId: number,
  skipSaveUser: boolean = false
) {
  chatStore.setStatus(sessionId, "streaming");
  if (chatStore.currentSessionId === sessionId) {
    status.value = "streaming";
  }

  const previous = abortControllersBySession.get(sessionId);
  if (previous) {
    previous.abort();
    abortControllersBySession.delete(sessionId);
  }

  const controller = new AbortController();
  abortControllersBySession.set(sessionId, controller);

  const history = getSessionUiMessages(sessionId)
    .map((m) => ({
      role: m.from,
      content: m.versions[m.versions.length - 1]?.content || "",
    }))
    .filter((m) => m.content.trim().length > 0);
  try {
    const iter = await streamChat(
      history,
      selectedKbId.value ? selectedKbId.value : undefined,
      {
        apiUrl: aiStore.chatApiUrl,
        llmApiKey: aiStore.llmApiKey,
        llmBaseUrl: aiStore.llmBaseUrl,
        llmModel: aiStore.llmModel,
        signal: controller.signal,
        sessionId,
        skipSaveUser,
      }
    );
    let acc = "";
    for await (const raw of iter) {
      const ev = parseEvent(raw);
      if (!ev) continue;
      if (ev.kind === "on_chat_model_stream") {
        acc += normalizeTextChunk(ev.text);
        updateStreamingContent(sessionId, versionId, acc);
        updateStoredMessageContent(sessionId, assistantMessageId, acc);
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
        updateStreamingTool(sessionId, versionId, {
          type: "tool_start",
          tool: ev.tool,
          input: ev.input || {},
          id: ev.id,
        });
      } else if (ev.kind === "on_tool_end") {
        updateStreamingTool(sessionId, versionId, {
          type: "tool_end",
          tool: ev.tool,
          output: ev.output,
          id: ev.id,
        });
        if (ev.tool === "read_file_chunks" || ev.tool === "read_file_chunks_multi") {
          const chunks = parseToolChunks(ev.output);
          const nextCitations = upsertMessageCitations(sessionId, versionId, chunks);
          updateStoredMessageCitations(sessionId, assistantMessageId, nextCitations);
        }
      } else if (ev.kind === "on_tool_error") {
        updateStreamingTool(sessionId, versionId, {
          type: "tool_end",
          tool: ev.tool,
          output: null,
          id: ev.id,
          error: String(ev.error || "Tool error"),
        });
      } else if (ev.kind === "error") {
        acc += `\n[Error] ${ev.error}`;
        updateStreamingContent(sessionId, versionId, acc);
        updateStoredMessageContent(sessionId, assistantMessageId, acc);
      }
    }
  } catch (e: any) {
    if (e.name === "AbortError") {
      // User aborted
      return;
    }
    const errText = `请求失败: ${e?.message || e}`;
    updateStreamingContent(sessionId, versionId, errText);
    updateStoredMessageContent(sessionId, assistantMessageId, errText);
  } finally {
    chatStore.setStatus(sessionId, "ready");
    const current = abortControllersBySession.get(sessionId);
    if (current === controller) {
      abortControllersBySession.delete(sessionId);
    }
    if (chatStore.currentSessionId === sessionId) {
      status.value = "ready";
    }
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

async function addUserMessage(content: string) {
  if (!chatStore.currentSessionId) {
    const title = content.slice(0, 20) || "New Chat";
    const session = await chatStore.createNewSession(title);
    chatStore.setMessages(session.id, []);
    chatStore.setUiMessages(session.id, []);
    chatStore.setStatus(session.id, "submitted");
  } else {
    chatStore.setStatus(chatStore.currentSessionId, "submitted");
  }

  const sessionId = chatStore.currentSessionId;
  if (!sessionId) return;
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
  setSessionUiMessages(sessionId, [...messages.value]);
  chatStore.appendMessage(sessionId, {
    id: timestamp,
    role: "user",
    content,
    createdAt: timestamp,
  });

  setTimeout(() => {
    const assistantId = Date.now();
    const assistantVersionId = `assistant-${assistantId}`;
    const assistantMessage: MessageType = {
      key: `assistant-${assistantId}`,
      from: "assistant",
      versions: [
        {
          id: assistantVersionId,
          content: "",
        },
      ],
    };

    messages.value = [...messages.value, assistantMessage];
    setSessionUiMessages(sessionId, [...messages.value]);
    chatStore.appendMessage(sessionId, {
      id: assistantId,
      role: "assistant",
      content: "",
      createdAt: assistantId,
    });
    streamResponse(assistantVersionId, sessionId, assistantId);
  }, 200);
}

async function handleSubmit(message: PromptInputMessage) {
  const text = message.text.trim();
  const hasText = text.length > 0;
  const hasAttachments = Array.isArray(message.files) && message.files.length > 0;

  if (!hasText && !hasAttachments) return;

  status.value = "submitted";

  await addUserMessage(hasText ? text : "Sent with attachments");
}

async function handleSuggestionClick(suggestion: string) {
  status.value = "submitted";
  await addUserMessage(suggestion);
}


onMounted(async () => {
  kbStore.fetchKnowledgeBases();
  await chatStore.loadSessions();
});

watch(
  () => chatStore.currentSessionId,
  async (newId) => {
    if (newId) {
      status.value = chatStore.getStatus(newId) as ChatStatus;

      const uiCached = chatStore.getUiMessages(newId) as MessageType[] | undefined;
      if (Array.isArray(uiCached)) {
        messages.value = uiCached;
        return;
      }

      const cached = chatStore.getMessages(newId);
      if (cached.length > 0) {
        const ui = toUiMessages(cached);
        chatStore.setUiMessages(newId, ui as any);
        messages.value = ui;
      }

      const history = await fetchMessages(newId);
      chatStore.setMessages(newId, history);
      
      const ui = toUiMessages(chatStore.getMessages(newId));
      chatStore.setUiMessages(newId, ui as any);
      messages.value = ui;
    } else {
      messages.value = [];
      status.value = "ready";
    }
  },
  { immediate: true }
);

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
  <div class="flex h-full w-full bg-white overflow-hidden">
    <!-- Sidebar -->
    <div class="w-64 flex-shrink-0 flex flex-col border-r bg-gray-50/50">
      <div class="p-4 border-b">
        <ElButton type="primary" class="w-full" @click="createNewChat">
          <PlusIcon class="mr-2 size-4" /> New Chat
        </ElButton>
      </div>
      <ElScrollbar class="flex-1">
        <div class="p-2 space-y-1">
          <div
            v-for="session in chatStore.sessions"
            :key="session.id"
            class="group flex items-center justify-between p-2 rounded-lg cursor-pointer hover:bg-gray-100 transition-colors"
            :class="chatStore.currentSessionId === session.id ? 'bg-gray-200' : ''"
            @click="chatStore.setCurrentSession(session.id)"
          >
            <div class="flex items-center gap-2 overflow-hidden">
                <MessageSquareIcon class="size-4 shrink-0 text-gray-500" />
                <span class="truncate text-sm text-gray-700">{{ session.title }}</span>
            </div>
            <button
              class="opacity-0 group-hover:opacity-100 p-1 hover:bg-gray-300 rounded text-gray-500 hover:text-red-500 transition-all"
              @click.stop="handleDeleteSession(session.id)"
            >
              <TrashIcon class="size-3" />
            </button>
          </div>
        </div>
      </ElScrollbar>
    </div>

    <div class="relative flex h-full flex-1 flex-col overflow-hidden bg-gray-50">
      <div class="flex-1 min-h-0 relative">
      <Conversation class="h-full">
        <ConversationContent class="h-full overflow-y-auto px-4 md:px-8 pt-6 pb-4 scroll-smooth">
          <div class="w-full space-y-8 pb-8">
            <MessageBranch
              v-for="(message, messageIndex) in messages"
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

                  <MessageContent>
                    <div v-if="message.from === 'user'">
                      <div v-if="editingMessageIndex === messageIndex">
                        <ElInput
                          class="w-full"
                          v-model="editContent"
                          type="textarea"
                          :autosize="{ minRows: 2, maxRows: 6 }"
                          :input-style="{
                            backgroundColor: '#ffffff',
                            border: '1px solid #3b82f6',
                          }"
                        />
                        <div class="mt-2 flex gap-2 justify-end">
                          <ElButton size="small" @click="cancelEditing">取消</ElButton>
                          <ElButton
                            size="small"
                            :loading="savingEdit"
                            :disabled="editContent.trim().length === 0"
                            @click="saveEditing"
                          >发送</ElButton>
                        </div>
                      </div>
                      <div v-else>
                        {{ latestContent(message) }}
                      </div>
                    </div>
                    <template
                      v-else-if="
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
            <MessageToolbar v-if="message.from === 'user'" :class="message.from === 'user' ? 'w-full flex flex-col items-end' : 'w-full min-w-0'">
              <MessageActions>
                <MessageAction label="Edit" tooltip="Edit message" @click="startEditing(messageIndex)">
                  <PencilIcon class="size-4" />
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
              <!-- <PromptInputActionMenu>
                <PromptInputActionMenuTrigger />
                <PromptInputActionMenuContent>
                  <PromptInputActionAddAttachments />
                </PromptInputActionMenuContent>
              </PromptInputActionMenu> -->

              <!-- <ModelSelector v-model:open="modelSelectorOpen">
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
              </ModelSelector> -->

              <PromptInputButton @click="kbSelectorOpen = true">
                <GlobeIcon :size="16" />
                <span>选择知识库</span>
              </PromptInputButton>
            </PromptInputTools>

            <PromptInputSubmit
              :disabled="false"
              :status="status"
              @click="status === 'streaming' ? stopGeneration() : undefined"
            />
          </PromptInputFooter>
        </PromptInput>
        <ElDialog 
          v-model="kbSelectorOpen" 
          title="选择知识库" 
          width="520px" 
          append-to-body 
          destroy-on-close
        >
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
 </div>
</template>
