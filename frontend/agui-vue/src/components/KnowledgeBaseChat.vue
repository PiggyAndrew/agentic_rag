<script setup lang="ts">
import type { PromptInputMessage } from "@/components/ai-elements/prompt-input";
import type { ChatStatus } from "ai";
import {
  Conversation,
  ConversationContent,
  ConversationScrollButton,
  ConversationEmptyState,
} from "@/components/ai-elements/conversation";
import {
  Message,
  MessageAction,
  MessageActions,
  MessageContent,
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
  Tool,
  ToolContent,
  ToolHeader,
  ToolInput,
  ToolOutput,
} from "@/components/ai-elements/tool";
import {
  PlusIcon,
  TrashIcon,
  MessageSquareIcon,
  PencilIcon,
  DatabaseIcon,
  XIcon,
  CornerDownLeftIcon,
  MoreHorizontalIcon,
} from "lucide-vue-next";
import { streamChat } from "@/api/chat";
import { computed, ref, onMounted, watch, provide, nextTick } from "vue";
import { useKbStore } from "@/stores/kb";
import { useAiStore } from "@/stores/ai";
import { useChatStore } from "@/stores/chat";
import { getApiBase } from "@/api/api_base";
import { fetchMessages, editMessage, updateSessionTitle } from "@/api/chat_history";
import type { ChatMessage } from "@/api/chat_history";
import { ElDialog, ElRadioGroup, ElRadio, ElButton, ElScrollbar, ElMessageBox, ElInput, ElDropdown, ElDropdownMenu, ElDropdownItem } from "element-plus";
import KnowledgeBaseCitation from "./KnowledgeBaseCitation.vue";
import { StreamMarkdown } from "streamdown-vue";
import ChunkViewerDialog from "./ChunkViewerDialog.vue";

// Content Parts 类型定义
type ContentPart =
  | { type: "text"; text: string }
  | { type: "reasoning"; text: string; reasoningId?: string; startTime?: number; duration?: number }
  | { type: "tool-call"; state: "input-available" | "output-available" | "output-error"; toolCallId: string; toolName: string; args: Record<string, unknown>; result?: string; error?: string };

interface MessageCitation {
  file_id: number;
  chunk_index: number;
  filename: string;
  content: string;
  metadata?: Record<string, any>;
}

interface MessageType {
  id: string;
  from: "user" | "assistant";
  versions: Array<{ id: string; content: string }>;
  citations?: MessageCitation[];
  contentParts?: ContentPart[];
}

// 状态管理
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
const citationDialogOpen = ref(false);
const citationDialogChunks = ref<any[]>([]);
const textAccByVersionId = new Map<string, string>();
const citeDataByKey = ref<Record<string, MessageCitation | null>>({});
const citeLoadingByKey = ref<Record<string, boolean>>({});
const editingTitleSessionId = ref<string | null>(null);
const editingTitle = ref("");
const titleInputRef = ref<HTMLInputElement | null>(null);
const pendingNameGenerations = new Map<string, ReturnType<typeof setTimeout>>();
const activeNameGenerations = new Set<string>();

const citePattern = /〔cite:([^〕]+)〕/g;

// 工具函数
function citeKey(fileId: number, chunkIndex: number): string {
  return `${fileId}:${chunkIndex}`;
}

const citationIndex = computed(() => {
  const map = new Map<string, MessageCitation>();
  for (const msg of messages.value) {
    if (!Array.isArray(msg.citations)) continue;
    for (const c of msg.citations) {
      if (typeof c?.file_id !== "number" || typeof c?.chunk_index !== "number") continue;
      const key = citeKey(c.file_id, c.chunk_index);
      if (!map.has(key)) map.set(key, c);
    }
  }
  return map;
});

function tryResolveFromIndex(fileId: number, chunkIndex: number): MessageCitation | null {
  const direct = citationIndex.value.get(citeKey(fileId, chunkIndex));
  if (direct) return direct;
  if (chunkIndex > 0) {
    const alt = citationIndex.value.get(citeKey(fileId, chunkIndex - 1));
    if (alt) return alt;
  }
  return null;
}

async function resolveCitation(fileId: number, chunkIndex: number): Promise<MessageCitation | null> {
  const fromIndex = tryResolveFromIndex(fileId, chunkIndex);
  if (fromIndex) return fromIndex;

  const key = citeKey(fileId, chunkIndex);
  const cached = citeDataByKey.value[key];
  if (cached) return cached;

  const kbId = selectedKbId.value;
  if (!kbId) return null;

  try {
    const chunks = await kbStore.fetchChunks(kbId, `f-${fileId}`);
    const find = (idx: number) =>
      Array.isArray(chunks)
        ? (chunks.find((c: any) => Number(c?.chunk_index) === idx) as any)
        : undefined;

    const found = find(chunkIndex) ?? (chunkIndex > 0 ? find(chunkIndex - 1) : undefined);
    if (!found) return null;

    const citation: MessageCitation = {
      file_id: fileId,
      chunk_index: Number(found.chunk_index),
      filename: String(found?.metadata?.filename ?? found?.metadata?.title ?? `file-${fileId}`),
      content: String(found?.content ?? ""),
      metadata: found?.metadata ?? undefined,
    };

    citeDataByKey.value = { ...citeDataByKey.value, [key]: citation };
    return citation;
  } catch (e: any) {
    console.error('Failed to resolve citation:', { fileId, chunkIndex, kbId, error: e?.message });
    return null;
  }
}

async function ensureCitationLoaded(fileId: number, chunkIndex: number): Promise<void> {
  const key = citeKey(fileId, chunkIndex);
  if (citeLoadingByKey.value[key]) return;
  if (tryResolveFromIndex(fileId, chunkIndex)) return;
  if (citeDataByKey.value[key]) return;
  citeLoadingByKey.value = { ...citeLoadingByKey.value, [key]: true };
  try {
    await resolveCitation(fileId, chunkIndex);
  } finally {
    citeLoadingByKey.value = { ...citeLoadingByKey.value, [key]: false };
  }
}

type CitationRef = { fileId: number; chunkIndex: number; lineRanges?: Array<[number, number]> };

async function openCitationDialog(
  fileIdOrRefs: number | CitationRef[],
  chunkIndex?: number
): Promise<void> {
  const refs: CitationRef[] = Array.isArray(fileIdOrRefs)
    ? fileIdOrRefs
    : [{ fileId: fileIdOrRefs, chunkIndex: Number(chunkIndex) }];

  const validRefs = refs.filter((r) => Number.isFinite(r.fileId) && Number.isFinite(r.chunkIndex));
  if (validRefs.length === 0) return;

  await Promise.all(validRefs.map((r) => ensureCitationLoaded(r.fileId, r.chunkIndex)));

  const chunkItems: any[] = [];
  for (const r of validRefs) {
    const citation =
      tryResolveFromIndex(r.fileId, r.chunkIndex) ?? citeDataByKey.value[citeKey(r.fileId, r.chunkIndex)];
    if (!citation) continue;

    const metadata = citation.metadata ? { ...citation.metadata } : {};
    if (citation.filename && citation.filename !== `file-${r.fileId}`) {
      metadata.filename = citation.filename;
    }

    chunkItems.push({
      file_id: citation.file_id,
      chunk_index: citation.chunk_index,
      content: citation.content,
      metadata,
      ...(Array.isArray(r.lineRanges) ? { line_ranges: r.lineRanges } : {}),
      ...(Array.isArray(r.lineRanges) && r.lineRanges.length > 0 ? { focus_line: r.lineRanges[0]?.[0] } : {}),
    });
  }

  if (chunkItems.length === 0) return;
  citationDialogChunks.value = chunkItems;
  citationDialogOpen.value = true;
}

// ==================== 标题编辑功能 ====================

function startEditingTitle(sessionId: string, currentTitle: string) {
  editingTitleSessionId.value = sessionId;
  editingTitle.value = currentTitle;
  nextTick(() => {
    titleInputRef.value?.focus();
    titleInputRef.value?.select();
  });
}

function cancelEditingTitle() {
  editingTitleSessionId.value = null;
  editingTitle.value = "";
}

const isSavingTitle = ref(false);

async function saveTitle() {
  const sessionId = editingTitleSessionId.value;
  if (!sessionId) return;

  const newTitle = editingTitle.value.trim();
  const session = chatStore.sessions.find(s => s.id === sessionId);
  
  // 如果标题为空，或者未发生变化，直接退出编辑状态
  if (!newTitle || (session && newTitle === session.title)) {
    cancelEditingTitle();
    return;
  }

  if (isSavingTitle.value) return;
  isSavingTitle.value = true;

  try {
    await updateSessionTitle(sessionId, newTitle);
    // 更新本地 store 中的标题
    if (session) {
      session.title = newTitle;
    }
    cancelEditingTitle();
  } catch (error: any) {
    console.error('Failed to update title:', error);
    // 即使失败也退出编辑状态，避免卡住
    cancelEditingTitle();
  } finally {
    isSavingTitle.value = false;
  }
}

function handleTitleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter') {
    event.preventDefault();
    saveTitle();
  } else if (event.key === 'Escape') {
    cancelEditingTitle();
  }
}

// ==================== 自动命名功能 ====================

async function generateConversationName(sessionId: string): Promise<void> {
  // 检查是否已有自定义标题（不是默认的 "New Chat"）
  const session = chatStore.sessions.find(s => s.id === sessionId);
  if (!session || session.title !== "New Chat") {
    return; // 如果已有自定义标题，不自动生成
  }

  const sessionMessages = chatStore.getMessages(sessionId);
  // 只获取前4条非空用户消息用于命名
  const messages = sessionMessages
    .filter(m => m.role === 'user' && m.content && m.content.trim())
    .slice(0, 4);

  if (messages.length === 0) return;

  try {
    const messagesText = messages.map(m => m.content).join('\n');
    const prompt = `请为以下对话生成一个简洁的标题（不超过10个字），概括对话的主要内容：

${messagesText}

只返回标题，不要包含任何其他内容或标点符号。`;

    const base = getApiBase().trim().replace(/\/+$/, '');
    const response = await fetch(`${base}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: [{ role: 'user', content: prompt }],
        stream: false,
      }),
    });

    if (!response.ok) throw new Error('Failed to generate title');

    const json = await response.json();
    const content = json?.content || json?.message?.content || '';
    const title = content
      .replace(/['"「」『』（）()【】\[\]{}]/g, '')
      .replace(/<[^>]*>/g, '')
      .trim()
      .slice(0, 15);

    if (title) {
      await updateSessionTitle(sessionId, title);
      const session = chatStore.sessions.find(s => s.id === sessionId);
      if (session) {
        session.title = title;
      }
    }
  } catch (error: any) {
    console.error('Failed to generate conversation name:', error);
  }
}

function scheduleGenerateName(sessionId: string) {
  const key = `name-${sessionId}`;

  // 如果已经有正在进行的请求，不重复发送
  if (activeNameGenerations.has(key)) {
    return;
  }

  // 清除之前的定时器
  const existingTimeout = pendingNameGenerations.get(key);
  if (existingTimeout) {
    clearTimeout(existingTimeout);
  }

  // 设置新的定时器，延迟1秒执行
  const timeout = setTimeout(async () => {
    pendingNameGenerations.delete(key);
    activeNameGenerations.add(key);

    try {
      await generateConversationName(sessionId);
    } finally {
      activeNameGenerations.delete(key);
    }
  }, 1000);

  pendingNameGenerations.set(key, timeout);
}

function rehypeInlineCitation() {
  const parseLineRanges = (raw: string | undefined): Array<[number, number]> | undefined => {
    const s = String(raw ?? "").trim();
    if (!s) return undefined;
    const parts = s.split(/[,，、\s]+/).filter(Boolean);
    const ranges: Array<[number, number]> = [];
    for (const part of parts) {
      const m = part.match(/^(\d+)(?:-(\d+))?$/);
      if (!m) continue;
      const start = Number(m[1]);
      const end = Number(m[2] ?? m[1]);
      if (!Number.isFinite(start) || !Number.isFinite(end)) continue;
      if (start <= 0 || end <= 0) continue;
      ranges.push([Math.min(start, end), Math.max(start, end)]);
    }
    return ranges.length ? ranges : undefined;
  };

  const parseCiteList = (inner: string) => {
    const items: Array<{ fileId: number; chunkIndex: number; lineRanges?: Array<[number, number]> }> = [];
    const entries = inner
      .split(";")
      .map((s) => s.trim())
      .filter(Boolean);

    for (const entry of entries) {
      const tokens = entry
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);

      const kv: Record<string, string> = {};
      let i = 0;
      while (i < tokens.length) {
        const token = tokens[i];
        if (!token) {
          i += 1;
          continue;
        }
        const eq = token.indexOf("=");
        if (eq <= 0) {
          i += 1;
          continue;
        }
        const key = token.slice(0, eq).trim();
        let val = token.slice(eq + 1).trim();
        if (key === "lines") {
          let j = i + 1;
          while (j < tokens.length && !(tokens[j] ?? "").includes("=")) {
            val = `${val},${tokens[j] ?? ""}`.trim();
            j += 1;
          }
          i = j;
        } else {
          i += 1;
        }
        kv[key] = val;
      }

      const fileId = Number(kv.fileId);
      const chunkIndex = Number(kv.chunkIndex);
      if (!Number.isFinite(fileId) || !Number.isFinite(chunkIndex)) continue;
      const lineRanges = parseLineRanges(kv.lines);
      items.push({ fileId, chunkIndex, ...(lineRanges ? { lineRanges } : {}) });
    }

    return items;
  };

  return (tree: any) => {
    const walk = (node: any) => {
      const children: any[] | undefined = node?.children;
      if (!Array.isArray(children) || children.length === 0) return;

      const nextChildren: any[] = [];
      for (const child of children) {
        if (child?.type === "text" && typeof child.value === "string") {
          const value = child.value as string;
          citePattern.lastIndex = 0;
          let last = 0;
          let matched = false;
          for (let m = citePattern.exec(value); m; m = citePattern.exec(value)) {
            matched = true;
            const start = m.index ?? 0;
            const end = start + m[0].length;
            const before = value.slice(last, start);
            if (before) nextChildren.push({ type: "text", value: before });

            const inner = String(m[1] ?? "");
            const cites = parseCiteList(inner);
            if (cites.length > 0) {
              nextChildren.push({
                type: "element",
                tagName: "inline-citation",
                properties: {
                  "data-cites": JSON.stringify(cites),
                },
                children: [],
              });
            } else {
              nextChildren.push({ type: "text", value: m[0] });
            }
            last = end;
          }
          if (matched) {
            const tail = value.slice(last);
            if (tail) nextChildren.push({ type: "text", value: tail });
          } else {
            nextChildren.push(child);
          }
        } else {
          walk(child);
          nextChildren.push(child);
        }
      }

      node.children = nextChildren;
    };

    walk(tree);
  };
}

function resolveAssetUrl(raw: unknown): string {
  const s = String(raw ?? "").trim();
  if (!s) return s;
  if (s.startsWith("data:") || s.startsWith("blob:")) return s;

  const base = getApiBase().replace(/\/$/, "");

  if (s.startsWith("/assets/")) return `${base}${s}`;
  if (s.startsWith("assets/")) return `${base}/${s}`;

  if (/^https?:\/\//i.test(s)) {
    try {
      const u = new URL(s);
      if ((u.pathname || "").startsWith("/assets/")) {
        return `${base}${u.pathname}${u.search}${u.hash}`;
      }
    } catch {
    }
  }

  return s;
}

function rehypeRewriteAssetUrls() {
  return (tree: any) => {
    const walk = (node: any) => {
      if (!node) return;
      if (node.type === "element" && node.tagName && node.properties) {
        if (node.tagName === "img" && node.properties.src) {
          node.properties.src = resolveAssetUrl(node.properties.src);
        } else if (node.tagName === "a" && node.properties.href) {
          node.properties.href = resolveAssetUrl(node.properties.href);
        }
      }
      const children: any[] | undefined = node?.children;
      if (!Array.isArray(children) || children.length === 0) return;
      for (const child of children) walk(child);
    };
    walk(tree);
  };
}

provide('citationContext', {
  selectedKbId,
  getApiBase: () => getApiBase(),
  ensureLoaded: ensureCitationLoaded,
  openDialog: openCitationDialog,
  getCitation: (fileId: number, chunkIndex: number) =>
    tryResolveFromIndex(fileId, chunkIndex) ?? citeDataByKey.value[citeKey(fileId, chunkIndex)] ?? null
});

const markdownComponents = {
  "inline-citation": KnowledgeBaseCitation,
};

function toUiMessages(list: ChatMessage[]): MessageType[] {
  return list.map((msg) => ({
    id: `${msg.role}-${msg.id}`,
    from: (msg.role === "assistant" ? "assistant" : "user") as "user" | "assistant",
    versions: [{ id: `${msg.role}-${msg.id}`, content: msg.content }],
    citations: msg.citations,
    // 为历史消息生成默认的 contentParts
    contentParts: msg.content ? [{ type: "text", text: msg.content }] : [],
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

function updateStreamingContent(sessionId: string, versionId: string, content: string) {
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

function updateContentPart(sessionId: string, versionId: string, part: ContentPart) {
  const sessionMessages = getSessionUiMessages(sessionId);
  const target = sessionMessages.find((msg) =>
    msg.versions.some((version) => version.id === versionId)
  );
  if (!target) return;

  if (!target.contentParts) {
    target.contentParts = [];
  }

  if (part.type === "tool-call") {
    const existingIndex = target.contentParts.findIndex((p) =>
      p.type === "tool-call" && (p as any).toolCallId === (part as any).toolCallId
    );
    if (existingIndex >= 0) {
      target.contentParts[existingIndex] = part;
    } else {
      target.contentParts.push(part);
    }
  } else if (part.type === "text") {
    const incoming = String((part as any).text ?? "");
    const prevAcc = textAccByVersionId.get(versionId) || "";

    let accNext = prevAcc;
    let delta = "";

    if (incoming.length === 0) {
      // no-op
    } else if (incoming.startsWith(prevAcc)) {
      delta = incoming.slice(prevAcc.length);
      accNext = incoming;
    } else if (prevAcc.length > 0 && prevAcc.startsWith(incoming)) {
      delta = "";
      accNext = prevAcc;
    } else {
      const max = Math.min(prevAcc.length, incoming.length);
      let overlap = 0;
      for (let k = max; k >= 1; k -= 1) {
        if (prevAcc.endsWith(incoming.slice(0, k))) {
          overlap = k;
          break;
        }
      }
      delta = incoming.slice(overlap);
      accNext = prevAcc + delta;
    }

    if (delta.length > 0) {
      const last = target.contentParts[target.contentParts.length - 1] as any;
      if (last && last.type === "text") {
        last.text = String(last.text || "") + delta;
      } else {
        target.contentParts.push({ type: "text", text: delta } as any);
      }
    }

    textAccByVersionId.set(versionId, accNext);
  } else if (part.type === "reasoning") {
    const reasoningParts = target.contentParts.filter((p) => p.type === "reasoning");
    if (reasoningParts.length > 0) {
      const lastReasoningPart = reasoningParts[reasoningParts.length - 1] as any;
      const newPart = part as any;
      const lastText = String(lastReasoningPart.text ?? "");
      const nextText = String(newPart.text ?? "");
      const sameStartTime =
        newPart.startTime != null &&
        lastReasoningPart.startTime != null &&
        newPart.startTime === lastReasoningPart.startTime;
      const isStreamingUpdate =
        sameStartTime ||
        (nextText.startsWith(lastText) && nextText.length >= lastText.length);
      if (isStreamingUpdate) {
        if (lastReasoningPart.text !== newPart.text) {
          lastReasoningPart.text = newPart.text;
        }
        if (newPart.duration !== undefined) {
          lastReasoningPart.duration = newPart.duration;
        }
        if (newPart.startTime !== undefined) {
          lastReasoningPart.startTime = newPart.startTime;
        }
      } else {
        target.contentParts.push(part);
      }
    } else {
      target.contentParts.push(part);
    }
  }

  setSessionUiMessages(sessionId, [...sessionMessages]);
}



function parseEvent(raw: any): any {
  const kind = raw?.event;
  if (!kind) return null;

  if (kind === "content_part") {
    const data = raw?.data;
    if (!data) return null;
    const partType = data?.type;
    if (!partType) return null;

    if (partType === "text") {
      return {
        kind: "content_part",
        part: {
          type: "text",
          text: data?.text || "",
        },
      };
    } else if (partType === "reasoning") {
      return {
        kind: "content_part",
        part: {
          type: "reasoning",
          text: data?.text || "",
          reasoningId: data?.reasoningId,
          startTime: data?.startTime,
          duration: raw?.duration,  // 从顶层获取 duration
        },
      };
    } else if (partType === "tool-call") {
      return {
        kind: "content_part",
        part: {
          type: "tool-call",
          state: data?.state || "input-available",
          toolCallId: data?.toolCallId || "",
          toolName: data?.toolName || "",
          args: data?.args || {},
          result: data?.result,
          error: data?.error,
        },
      };
    }
    return null;
  }
  return null;
}

// 操作函数
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

function handleSessionCommand(command: { action: string; session: any }) {
  const { action, session } = command;
  if (action === "rename") {
    startEditingTitle(session.id, session.title);
  } else if (action === "delete") {
    handleDeleteSession(session.id);
  }
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
      id: `assistant-${assistantId}`,
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
    streamResponse(assistantVersionId, sessionId, true);
  } finally {
    savingEdit.value = false;
  }
}

// 流式响应处理
async function streamResponse(
  versionId: string,
  sessionId: string,
  skipSaveUser: boolean = false
) {
  chatStore.setStatus(sessionId, "streaming");
  if (chatStore.currentSessionId === sessionId) {
    status.value = "streaming";
  }

  textAccByVersionId.delete(versionId);

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
      if (ev.kind === "content_part") {
        updateContentPart(sessionId, versionId, ev.part);
        if (ev.part.type === "text") {
          acc = (ev.part as any).text;
          updateStreamingContent(sessionId, versionId, acc);
        }
      }
    }
  } catch (e: any) {
    if (e.name === "AbortError") {
      return;
    }
    const errText = `请求失败: ${e?.message || e}`;
    updateStreamingContent(sessionId, versionId, errText);
  } finally {
    chatStore.setStatus(sessionId, "ready");
    textAccByVersionId.delete(versionId);
    const current = abortControllersBySession.get(sessionId);
    if (current === controller) {
      abortControllersBySession.delete(sessionId);
    }
    if (chatStore.currentSessionId === sessionId) {
      status.value = "ready";
    }
    // 对话完成后，尝试自动生成标题
    if (!skipSaveUser) {
      scheduleGenerateName(sessionId);
    }
  }
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
    id: `user-${timestamp}`,
    from: "user",
    versions: [{ id: `user-${timestamp}`, content }],
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
      id: `assistant-${assistantId}`,
      from: "assistant",
      versions: [{ id: assistantVersionId, content: "" }],
    };

    messages.value = [...messages.value, assistantMessage];
    setSessionUiMessages(sessionId, [...messages.value]);
    chatStore.appendMessage(sessionId, {
      id: assistantId,
      role: "assistant",
      content: "",
      createdAt: assistantId,
    });
    streamResponse(assistantVersionId, sessionId);
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

// 生命周期
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
  <div class="flex h-full w-full bg-background overflow-hidden">
    <!-- Sidebar -->
    <div class="w-64 flex-shrink-0 flex flex-col border-r border-border bg-card/50">
      <div class="p-4 border-b border-border">
        <button
          class="w-full h-10 rounded-lg bg-primary text-primary-foreground font-medium text-sm flex items-center justify-center gap-2 transition-all duration-normal ease-out hover:bg-primary/90 hover:shadow-primary-sm"
          @click="createNewChat"
        >
          <PlusIcon class="size-4" />
          <span>新对话</span>
        </button>
      </div>
      <ElScrollbar class="flex-1">
        <div class="p-2 space-y-1.5">
          <div
            v-for="session in chatStore.sessions"
            :key="session.id"
            class="group relative flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all duration-normal ease-out border"
            :class="chatStore.currentSessionId === session.id
              ? 'bg-card border-primary/30 shadow-sm ring-1 ring-primary/10 z-10'
              : 'bg-transparent border-transparent hover:bg-card hover:border-border hover:shadow-sm text-muted-foreground hover:text-foreground'"
            @click="chatStore.setCurrentSession(session.id)"
          >
            <!-- Active indicator -->
            <div v-if="chatStore.currentSessionId === session.id"
              class="absolute left-0 top-1/2 -translate-y-1/2 h-8 w-1 bg-primary rounded-r-full"
            />

            <MessageSquareIcon class="size-4 shrink-0" :class="chatStore.currentSessionId === session.id ? 'text-primary' : ''" />

            <!-- Title display/edit -->
            <div class="flex-1 min-w-0">
              <!-- 编辑模式 -->
              <input
                v-if="editingTitleSessionId === session.id"
                ref="titleInputRef"
                v-model="editingTitle"
                @blur="saveTitle"
                @keydown="handleTitleKeydown"
                class="w-full bg-transparent border-b border-primary text-sm focus:outline-none"
              />
              <!-- 显示模式 -->
              <div
                v-else
                class="truncate text-sm flex items-center gap-1"
              >
                {{ session.title }}
              </div>
            </div>

            <!-- Actions Dropdown -->
            <ElDropdown trigger="click" @command="handleSessionCommand" @click.stop>
              <button
                class="opacity-0 group-hover:opacity-100 p-1.5 hover:bg-muted rounded-lg transition-all duration-normal ease-out outline-none text-muted-foreground hover:text-foreground"
                :class="{ 'opacity-100': chatStore.currentSessionId === session.id }"
              >
                <MoreHorizontalIcon class="size-3.5" />
              </button>
              <template #dropdown>
                <ElDropdownMenu>
                  <ElDropdownItem :command="{ action: 'rename', session }">
                    <div class="flex items-center gap-2">
                      <PencilIcon class="size-3.5" />
                      <span>重命名</span>
                    </div>
                  </ElDropdownItem>
                  <ElDropdownItem :command="{ action: 'delete', session }" divided class="text-destructive">
                    <div class="flex items-center gap-2">
                      <TrashIcon class="size-3.5" />
                      <span>删除</span>
                    </div>
                  </ElDropdownItem>
                </ElDropdownMenu>
              </template>
            </ElDropdown>
          </div>

          <!-- Empty state for sessions -->
          <div v-if="chatStore.sessions.length === 0" class="py-12 text-center">
            <div class="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-muted mb-3">
              <MessageSquareIcon class="size-5 text-muted-foreground/40" />
            </div>
            <p class="text-xs text-muted-foreground">暂无对话记录</p>
          </div>
        </div>
      </ElScrollbar>
    </div>

    <!-- Main Content -->
    <div class="relative flex h-full flex-1 flex-col overflow-hidden bg-background">
      <div class="flex-1 min-h-0 relative">
        <Conversation class="h-full">
          <ConversationContent class="h-full overflow-y-auto px-6 md:px-12 pt-8 pb-6">
            <ConversationEmptyState v-if="messages.length === 0">
              <div class="text-center space-y-4">
                <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10">
                  <MessageSquareIcon class="size-8 text-primary" />
                </div>
                <div>
                  <h2 class="text-xl font-semibold font-heading text-foreground">开始新对话</h2>
                  <p class="text-sm text-muted-foreground mt-1">选择知识库并开始提问</p>
                </div>
              </div>
            </ConversationEmptyState>
            <div v-else class="w-full space-y-8 pb-8">
              <Message
                v-for="(message, messageIndex) in messages"
                :key="message.id"
                :from="message.from"
              >
                <div :class="message.from === 'user' ? 'w-full flex flex-col items-end' : 'w-full min-w-0'">
                  <!-- User Message Edit -->
                  <template v-if="message.from === 'user' && editingMessageIndex === messageIndex">
                    <ElInput
                      class="w-full"
                      v-model="editContent"
                      type="textarea"
                      :autosize="{ minRows: 2, maxRows: 6 }"
                    />
                    <div class="mt-2 flex gap-2 justify-end">
                      <MessageAction
                        label="取消"
                        tooltip="取消编辑"
                        variant="secondary"
                        size="sm"
                        @click="cancelEditing"
                      >
                        <XIcon class="size-4" />
                        <span>取消</span>
                      </MessageAction>
                      <MessageAction
                        label="发送"
                        tooltip="发送编辑"
                        variant="default"
                        size="sm"
                        :disabled="editContent.trim().length === 0 || savingEdit"
                        @click="saveEditing"
                      >
                        <CornerDownLeftIcon class="size-4" />
                        <span>发送</span>
                      </MessageAction>
                    </div>
                  </template>

                  <!-- Content Parts -->
                  <template v-else-if="message.contentParts && message.contentParts.length">
                    <template v-for="(part, idx) in message.contentParts" :key="`part-${idx}`">
                      <!-- Reasoning -->
                      <Reasoning
                        v-if="part.type === 'reasoning'"
                        :duration="part.duration"
                      >
                        <ReasoningTrigger />
                        <ReasoningContent :content="part.text" />
                      </Reasoning>

                      <!-- Tool Call -->
                      <Tool v-else-if="part.type === 'tool-call'">
                        <ToolHeader
                          :state="part.state"
                          :title="part.toolName"
                          :type="`tool-${part.toolName}`"
                        />
                        <ToolContent>
                          <ToolInput :input="part.args" />
                          <ToolOutput
                            :output="part.result"
                            :error-text="part.error"
                          />
                        </ToolContent>
                      </Tool>

                      <!-- Text -->
                      <MessageContent v-else-if="part.type === 'text'">
                        <StreamMarkdown
                          :shiki-theme="{
                            light: 'github-light',
                            dark: 'github-dark',
                          }"
                          :content="part.text"
                          :components="markdownComponents"
                          :rehype-plugins="[rehypeInlineCitation, rehypeRewriteAssetUrls]"
                          class="w-fit min-w-0 [&>*:first-child]:mt-0 [&>*:last-child]:mb-0 whitespace-normal break-words"
                        />
                      </MessageContent>
                    </template>
                    <!-- User Message Edit Action Button (below content) -->
                    <div v-if="message.from === 'user'" class="mt-2">
                      <MessageAction
                        label="编辑"
                        tooltip="编辑消息"
                        @click="startEditing(messageIndex)"
                      >
                        <PencilIcon class="size-4" />
                      </MessageAction>
                    </div>
                  </template>

                  <!-- 兼容旧数据 -->
                  <template v-else>
                    <div class="prose prose-sm max-w-none">
                      {{ latestContent(message) }}
                    </div>
                    <!-- User Message Edit Action Button (below content) -->
                    <div v-if="message.from === 'user'" class="mt-2">
                      <MessageAction
                        label="编辑"
                        tooltip="编辑消息"
                        @click="startEditing(messageIndex)"
                      >
                        <PencilIcon class="size-4" />
                      </MessageAction>
                    </div>
                  </template>
                </div>

                <!-- Message Actions -->
                <MessageActions>
                  <!-- <MessageAction
                    v-if="message.from === 'assistant'"
                    label="Retry"
                    tooltip="重新生成"
                  >
                    <RefreshCcwIcon class="size-4" />
                  </MessageAction>
                  <MessageAction
                    v-if="message.from === 'assistant'"
                    label="Like"
                    tooltip="点赞"
                  >
                    <ThumbsUpIcon class="size-4" />
                  </MessageAction>
                  <MessageAction
                    v-if="message.from === 'assistant'"
                    label="Dislike"
                    tooltip="点踩"
                  >
                    <ThumbsDownIcon class="size-4" />
                  </MessageAction>
                  <MessageAction label="Copy" tooltip="复制">
                    <CopyIcon class="size-4" />
                  </MessageAction> -->
                </MessageActions>
              </Message>
            </div>
          </ConversationContent>
          <ConversationScrollButton />
        </Conversation>
      </div>

      <!-- Input Area -->
      <div class="shrink-0 border-t border-border bg-card/80 backdrop-blur-md py-4 z-[var(--z-sticky)]">
        <div class="w-full px-6 md:px-12">
          <PromptInput
            class="w-full shadow-lg rounded-xl border border-border bg-card ring-1 ring-primary/5 transition-all duration-normal ease-out hover:shadow-xl hover:ring-primary/10"
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
                <PromptInputButton @click="kbSelectorOpen = true">
                  <DatabaseIcon :size="16" />
                  <span>知识库</span>
                </PromptInputButton>
              </PromptInputTools>

              <PromptInputSubmit
                :disabled="false"
                :status="status"
                @click="status === 'streaming' ? stopGeneration() : undefined"
              />
            </PromptInputFooter>
          </PromptInput>
        </div>
      </div>
    </div>

    <!-- KB Selector Dialog -->
    <ElDialog
      v-model="kbSelectorOpen"
      title="选择知识库"
      width="480px"
      append-to-body
      destroy-on-close
      class="!rounded-xl"
    >
      <div class="px-2 py-2">
        <ElRadioGroup v-model="selectedKbId">
          <div class="space-y-2">
            <ElRadio
              v-for="kb in kbStore.knowledgeBases"
              :key="kb.id"
              :label="kb.id"
              class="w-full p-3 rounded-xl hover:bg-muted transition-all duration-normal ease-out border border-transparent"
              :class="selectedKbId === kb.id ? 'bg-primary/5 border-primary/20' : ''"
            >
              <div class="flex items-center gap-3 pl-2">
                <DatabaseIcon class="size-5 text-primary" />
                <div>
                  <div class="font-medium text-sm text-foreground">{{ kb.name }}</div>
                  <div v-if="kb.description" class="text-xs text-muted-foreground mt-0.5">{{ kb.description }}</div>
                </div>
              </div>
            </ElRadio>
          </div>
        </ElRadioGroup>
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <ElButton @click="kbSelectorOpen = false">取消</ElButton>
          <ElButton type="primary" @click="kbSelectorOpen = false">确定</ElButton>
        </div>
      </template>
    </ElDialog>
  </div>

  <ChunkViewerDialog v-model="citationDialogOpen" :chunks="citationDialogChunks" />
</template>
