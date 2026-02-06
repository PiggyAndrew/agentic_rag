<script setup lang="ts">
import { computed, ref, nextTick, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, CopyDocument, Search } from '@element-plus/icons-vue'
import { StreamMarkdown } from 'streamdown-vue'

interface ChunkItem {
  file_id: number
  chunk_index: number
  content: string
  metadata?: Record<string, any>
  filename?: string  // 可选，从 metadata 中提取
  line_ranges?: Array<[number, number]>
  focus_line?: number
}

const props = defineProps<{
  modelValue: boolean
  chunks: ChunkItem[]
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const visible = computed<boolean>({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const total = computed<number>(() => (props.chunks?.length ?? 0))
const searchQuery = ref('')
const activeChunkKey = ref<string | null>(null)

const target = ref<{ fileId?: number | null; chunkIndex: number | null; line?: number | null } | null>(null)

function parseUrlFragment(): { fileId?: number | null; chunkIndex: number | null; line?: number | null } | null {
  if (typeof window === 'undefined') return null
  const hash = window.location.hash
  if (!hash) return null
  const raw = hash.startsWith('#') ? hash.slice(1) : hash
  const params = new URLSearchParams(raw)
  const chunkRaw = params.get('chunk')
  if (!chunkRaw) return null
  const chunkIndex = parseInt(chunkRaw, 10)
  if (!Number.isFinite(chunkIndex)) return null
  const fileRaw = params.get('fileId')
  const lineRaw = params.get('line')
  const fileId = fileRaw != null ? parseInt(fileRaw, 10) : null
  const line = lineRaw != null ? parseInt(lineRaw, 10) : null
  return { fileId: Number.isFinite(fileId) ? fileId : null, chunkIndex, line: Number.isFinite(line) ? line : null }
}

// 后端已统一重写图片URL至静态HTTP路径，这里直接渲染内容

const filteredChunks = computed(() => {
  if (!searchQuery.value) return props.chunks
  const q = searchQuery.value.toLowerCase()
  return props.chunks.filter(c =>
    c.content.toLowerCase().includes(q) ||
    c.chunk_index.toString().includes(q)
  )
})

// 无需处理图片链接，直接渲染服务器已重写的内容

async function copyContent(text: string): Promise<void> {
  await navigator.clipboard.writeText(text || '')
  ElMessage.success('已复制片段内容')
}

function chunkKeyOf(item: Pick<ChunkItem, 'file_id' | 'chunk_index'>): string {
  return `${item.file_id}:${item.chunk_index}`
}

function scrollToChunk(item: ChunkItem) {
  activeChunkKey.value = chunkKeyOf(item)
  nextTick(() => {
    const el = document.getElementById(`chunk-card-${chunkKeyOf(item)}`)
    if (el) {
      const container = el.closest('.el-scrollbar__wrap') as HTMLElement
      let behavior: ScrollBehavior = 'smooth'

      if (container) {
        const elRect = el.getBoundingClientRect()
        const containerRect = container.getBoundingClientRect()
        const delta = Math.abs(elRect.top - containerRect.top)
        // 超过 3000px (约3-4个屏幕高度) 则直接跳转
        if (delta > 3000) {
          behavior = 'auto'
        }
      }

      el.scrollIntoView({ behavior, block: 'start' })
    }
  })
}

const highlightedEl = ref<HTMLElement | null>(null)
const highlightTimer = ref<number | null>(null)

function formatRanges(ranges?: Array<[number, number]>): string[] {
  if (!ranges || ranges.length === 0) return []
  return ranges.map(([a, b]) => (a === b ? `L${a}` : `L${a}-${b}`))
}

function normalizeLineSnippet(line: string): string {
  let s = String(line ?? '').trim()
  if (!s) return ''
  s = s.replace(/^#{1,6}\s+/, '')
  s = s.replace(/^\s*(?:[-*+]|•)\s+/, '')
  s = s.replace(/^\s*\d+\.\s+/, '')
  s = s.replace(/\*\*(.*?)\*\*/g, '$1')
  s = s.replace(/__(.*?)__/g, '$1')
  s = s.replace(/`+/g, '')
  if (s.includes('|')) {
    const cells = s
      .split('|')
      .map((x) => x.trim())
      .filter((x) => x.length > 0 && x !== '---' && !/^:?-+:?$/.test(x))
    s = cells.join(' ')
  }
  s = s.replace(/\s+/g, ' ').trim()
  return s.slice(0, 80)
}

function clearHighlight() {
  if (highlightTimer.value != null) {
    window.clearTimeout(highlightTimer.value)
    highlightTimer.value = null
  }
  if (highlightedEl.value) {
    highlightedEl.value.dataset.citeHit = 'false'
    highlightedEl.value = null
  }
}

function highlightElement(el: HTMLElement) {
  clearHighlight()
  el.dataset.citeHit = 'true'
  highlightedEl.value = el
  highlightTimer.value = window.setTimeout(() => {
    clearHighlight()
  }, 1600)
}

function findTextHit(container: HTMLElement, needle: string): HTMLElement | null {
  const n = needle.toLowerCase()
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT)
  let current: Node | null = walker.nextNode()
  while (current) {
    const text = (current as Text).nodeValue ?? ''
    if (text.toLowerCase().includes(n)) {
      const el = (current as Text).parentElement
      if (el) return el
    }
    current = walker.nextNode()
  }
  return null
}

function scrollToLine(item: ChunkItem, line: number) {
  const lineNo = Math.max(1, Math.floor(line))
  scrollToChunk(item)
  nextTick(() => {
    requestAnimationFrame(() => {
      const container = document.getElementById(`chunk-markdown-${chunkKeyOf(item)}`) as HTMLElement | null
      if (!container) return
      const lines = String(item.content ?? '').split(/\r?\n/)
      const raw = lines[lineNo - 1] ?? ''
      const snippet = normalizeLineSnippet(raw)
      if (!snippet) return
      const hit = findTextHit(container, snippet)
      if (!hit) return
      hit.scrollIntoView({ behavior: 'smooth', block: 'center' })
      highlightElement(hit)
    })
  })
}

function getMetaCore(metadata?: Record<string, any> | null): any | null {
  if (!metadata) return null
  // 尝试从 data 字段获取（兼容旧格式）
  if (typeof metadata.data === 'object' && metadata.data !== null) return metadata.data
  // 如果没有 data 字段，直接使用 metadata（兼容新格式）
  return metadata
}

function getMetaNumber(metadata?: Record<string, any> | null): string | undefined {
  const core = getMetaCore(metadata)
  if (!core) return undefined
  // 尝试从 data.number 获取
  if (typeof core.number === 'string' || typeof core.number === 'number') {
    return String(core.number)
  }
  // 尝试直接从 metadata.number 获取
  if (metadata && (typeof metadata.number === 'string' || typeof metadata.number === 'number')) {
    return String(metadata.number)
  }
  return undefined
}

function getMetaTitle(metadata?: Record<string, any> | null): string | undefined {
  const core = getMetaCore(metadata)
  if (!core) return undefined
  // 尝试从 data.title 获取
  if (typeof core.title === 'string') {
    return core.title
  }
  // 尝试直接从 metadata.title 获取
  if (metadata && typeof metadata.title === 'string') {
    return metadata.title
  }
  return undefined
}

function getMetaFilename(metadata?: Record<string, any> | null): string | undefined {
  if (!metadata) return undefined
  // 尝试从 metadata.filename 获取（新格式）
  if (typeof metadata.filename === 'string') {
    return metadata.filename
  }
  // 尝试从 metadata.data.filename 获取（旧格式）
  const core = getMetaCore(metadata)
  if (core && typeof core.filename === 'string') {
    return core.filename
  }
  // 尝试从 metadata.title 获取（兼容 title 字段）
  if (typeof metadata.title === 'string') {
    return metadata.title
  }
  return undefined
}

// 监听对话框打开状态，解析 URL fragment 并滚动
watch(visible, async (newVal) => {
  if (newVal) {
    await nextTick()
    const parsed = parseUrlFragment()
    if (parsed?.chunkIndex != null) {
      target.value = parsed
      const byFile = parsed.fileId != null
        ? filteredChunks.value.find((c) => c.file_id === parsed.fileId && c.chunk_index === parsed.chunkIndex)
        : null
      const byChunk = filteredChunks.value.find((c) => c.chunk_index === parsed.chunkIndex)
      const item = byFile ?? byChunk
      if (item) {
        scrollToChunk(item)
        if (parsed.line != null) {
          scrollToLine(item, parsed.line)
        }
      }
    } else {
      target.value = null
      const focused = filteredChunks.value.find((c) => typeof c.focus_line === 'number' && c.focus_line > 0)
      if (focused) {
        scrollToChunk(focused)
        scrollToLine(focused, focused.focus_line as number)
      }
    }
  } else {
    target.value = null
    clearHighlight()
  }
})

// 组件挂载时，处理 URL fragment
onMounted(() => {
  const parsed = parseUrlFragment()
  if (parsed?.chunkIndex != null) {
    target.value = parsed
  }
})
</script>

<template>
  <el-dialog
    v-model="visible"
    :title="`文件片段详情（${total}）`"
    width="85%"
    class="!rounded-xl overflow-hidden"
    destroy-on-close
    align-center
    top="5vh"
  >
    <div class="flex h-[75vh] -mx-6 -my-5 border-t border-border">
      <!-- 左侧导航栏 -->
      <div class="w-72 border-r border-border bg-muted/30 flex flex-col shrink-0">
        <div class="p-4 border-b border-border bg-card/80 backdrop-blur-sm sticky top-0 z-10">
          <el-input
            v-model="searchQuery"
            placeholder="搜索片段内容..."
            size="default"
            class="!rounded-lg"
            clearable
          >
            <template #prefix>
              <el-icon class="text-muted-foreground"><Search /></el-icon>
            </template>
          </el-input>
        </div>

        <div class="flex-1 overflow-hidden">
          <el-scrollbar>
            <div class="p-3 space-y-2">
              <template v-if="filteredChunks.length > 0">
                <div
                  v-for="item in filteredChunks"
                  :key="chunkKeyOf(item)"
                  class="group relative px-4 py-3 rounded-xl cursor-pointer transition-all duration-normal ease-out border"
                  :class="activeChunkKey === chunkKeyOf(item)
                    ? 'bg-card border-primary/30 shadow-sm ring-1 ring-primary/10 z-10'
                    : 'bg-transparent border-transparent hover:bg-card hover:border-border hover:shadow-sm text-muted-foreground'"
                  @click="scrollToChunk(item)"
                >
                  <!-- 选中指示点 -->
                  <div v-if="activeChunkKey === chunkKeyOf(item)"
                    class="absolute left-1.5 top-1/2 -translate-y-1/2 w-1 h-8 bg-primary rounded-full">
                  </div>

                  <div class="flex items-center justify-between gap-2 mb-1.5">
                    <span class="font-mono font-bold text-xs px-2 py-0.5 rounded-lg"
                      :class="activeChunkKey === chunkKeyOf(item) ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground'">
                      #{{ item.chunk_index }}
                    </span>
                    <span class="text-[10px] text-muted-foreground font-medium">{{ item.content.length }} 字符</span>
                  </div>

                  <div class="text-xs text-foreground line-clamp-2 leading-relaxed opacity-80 group-hover:opacity-100">
                     {{ item.content.slice(0, 60) }}...
                  </div>

                  <template v-if="item.line_ranges && item.line_ranges.length > 0">
                    <div class="mt-2 pt-2 border-t border-dashed border-border flex flex-wrap gap-1">
                      <span class="text-[10px] text-muted-foreground font-medium">引用行</span>
                      <button
                        v-for="(tag, idx) in formatRanges(item.line_ranges)"
                        :key="idx"
                        type="button"
                        class="inline-flex items-center px-1.5 py-0.5 rounded-lg bg-primary/10 text-primary text-[10px] font-medium hover:bg-primary/15 transition-colors"
                        @click.stop="scrollToLine(item, (item.line_ranges?.[idx]?.[0] ?? 1))"
                      >
                        {{ tag }}
                      </button>
                    </div>
                  </template>

                  <template v-if="item.metadata && (getMetaNumber(item.metadata) || getMetaTitle(item.metadata))">
                     <div class="mt-2 pt-2 border-t border-dashed border-border flex flex-wrap gap-1">
                        <span v-if="getMetaNumber(item.metadata)" class="inline-flex items-center px-1.5 py-0.5 rounded-lg bg-blue-50 text-blue-600 text-[10px] font-medium dark:bg-blue-500/10 dark:text-blue-400">
                          {{ getMetaNumber(item.metadata) }}
                        </span>
                        <span v-if="getMetaTitle(item.metadata)" class="inline-flex items-center px-1.5 py-0.5 rounded-lg bg-muted text-muted-foreground text-[10px] truncate max-w-full">
                          {{ getMetaTitle(item.metadata) }}
                        </span>
                     </div>
                  </template>
                </div>
              </template>
              <div v-else class="py-12 flex flex-col items-center justify-center text-muted-foreground">
                <div class="w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-3">
                   <el-icon class="opacity-20" size="20"><Search /></el-icon>
                </div>
                <span class="text-xs">未找到匹配的片段</span>
              </div>
            </div>
          </el-scrollbar>
        </div>

        <div class="p-2 border-t border-border bg-card/50 text-[10px] text-center text-muted-foreground font-mono">
          {{ filteredChunks.length }} / {{ total }} FRAGMENTS
        </div>
      </div>

      <!-- 右侧内容区域 -->
      <div class="flex-1 flex flex-col min-w-0 min-h-0 bg-muted/20">
        <el-scrollbar :always="true" class="flex-1 min-h-0 chunk-viewer-scrollbar">
          <div class="p-8 space-y-8">
            <template v-if="filteredChunks.length > 0">
              <div
                v-for="item in filteredChunks"
                :key="chunkKeyOf(item)"
                :id="`chunk-card-${chunkKeyOf(item)}`"
                class="group bg-card rounded-xl border border-border shadow-sm transition-all duration-normal ease-out overflow-hidden scroll-mt-6 hover:shadow-md hover:border-primary/20"
                :class="activeChunkKey === chunkKeyOf(item) ? 'ring-2 ring-primary ring-offset-4 shadow-lg border-primary/20' : ''"
              >
                <!-- 片段头部 -->
                <div class="flex items-center justify-between px-5 py-3 bg-gradient-to-r from-muted to-card border-b border-border">
                  <div class="flex items-center gap-3">
                    <div class="flex items-center justify-center w-8 h-8 rounded-lg bg-card border border-border shadow-sm text-primary text-sm font-mono font-bold">
                      #{{ item.chunk_index }}
                    </div>
                    <div class="flex flex-col">
                      <span class="text-xs font-medium text-muted-foreground uppercase tracking-wide">Fragment ID</span>
                      <span class="text-[10px] text-muted-foreground/60 font-mono">Length: {{ item.content.length }}</span>
                    </div>
                  </div>
                  <div class="flex items-center gap-2">
                    <el-button
                      v-if="item.line_ranges && item.line_ranges.length > 0"
                      type="primary"
                      link
                      size="small"
                      @click="scrollToLine(item, item.line_ranges?.[0]?.[0] ?? 1)"
                      class="!text-muted-foreground hover:!text-primary transition-colors"
                    >
                      跳到引用行
                    </el-button>
                    <el-button
                      type="primary"
                      link
                      size="small"
                      :icon="CopyDocument"
                      @click="copyContent(item.content)"
                      class="!text-muted-foreground hover:!text-primary transition-colors"
                    >
                      复制
                    </el-button>
                  </div>
                </div>

                <!-- 片段内容 -->
                <div class="p-6">
                  <div class="relative group/content">
                    <div :id="`chunk-markdown-${chunkKeyOf(item)}`">
                      <StreamMarkdown
                        :content="item.content"
                        :shiki-theme="{ light: 'github-light', dark: 'github-dark' }"
                        class="text-sm leading-7 text-foreground font-normal prose prose-sm max-w-none prose-p:my-2 prose-headings:mb-3 prose-headings:mt-4 prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none"
                      />
                    </div>
                  </div>

                  <!-- 元数据展示 -->
                  <div v-if="item.metadata && Object.keys(item.metadata).length > 0" class="mt-6 pt-4 border-t border-dashed border-border">
                    <div class="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-3 flex items-center gap-2">
                      <el-icon><Document /></el-icon>
                      Metadata
                    </div>
                    <div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
                      <!-- 文件名特殊显示（优先显示） -->
                      <div v-if="getMetaFilename(item.metadata)" class="flex flex-col p-2 rounded-lg bg-blue-50 border border-blue-100 hover:bg-card hover:shadow-sm transition-all duration-normal ease-out dark:bg-blue-500/10 dark:border-blue-500/20">
                        <span class="text-[10px] font-medium text-blue-500 mb-0.5 uppercase dark:text-blue-400">filename</span>
                        <div class="text-xs text-blue-700 font-medium truncate" :title="getMetaFilename(item.metadata)" dark:text-blue-300>
                          <span class="truncate">{{ getMetaFilename(item.metadata) }}</span>
                        </div>
                      </div>
                      <!-- 其他元数据 -->
                      <div
                        v-for="(value, key) in Object.entries(item.metadata).filter(([k]) => k !== 'filename')"
                        :key="key"
                        class="flex flex-col p-2 rounded-lg bg-muted border border-border hover:bg-card hover:shadow-sm transition-all duration-normal ease-out"
                      >
                        <span class="text-[10px] font-medium text-muted-foreground mb-0.5 uppercase">{{ key }}</span>
                        <div class="text-xs text-foreground font-medium truncate" :title="String(value)">
                           <template v-if="typeof value === 'object' && value !== null">
                             <span class="truncate">{{ JSON.stringify(value) }}</span>
                           </template>
                           <template v-else>
                             {{ value }}
                           </template>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </template>
            <div v-else class="flex flex-col items-center justify-center h-full py-20 text-muted-foreground">
              <div class="w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-4">
                 <el-icon size="32" class="opacity-20"><Search /></el-icon>
              </div>
              <span class="text-sm font-medium text-foreground">未找到匹配的片段</span>
              <span class="text-xs mt-1">尝试更换搜索关键词</span>
            </div>
          </div>
        </el-scrollbar>
      </div>
    </div>
  </el-dialog>
</template>

<style scoped>
[data-cite-hit="true"] {
  background: color-mix(in oklab, var(--el-color-primary) 14%, transparent);
}

:deep(.chunk-viewer-scrollbar .el-scrollbar__wrap) {
  overflow-x: hidden;
}

:deep(.chunk-viewer-scrollbar .el-scrollbar__bar) {
  z-index: 10;
}

:deep(.chunk-viewer-scrollbar .el-scrollbar__bar.is-vertical) {
  width: 10px;
  right: 4px;
  opacity: 1;
}

:deep(.chunk-viewer-scrollbar .el-scrollbar__bar.is-vertical > div) {
  background-color: rgb(156 163 175 / 0.6);
}

:deep(.chunk-viewer-scrollbar .el-scrollbar__bar.is-horizontal) {
  height: 10px;
  bottom: 4px;
  opacity: 1;
}

:deep(.chunk-viewer-scrollbar .el-scrollbar__bar.is-horizontal > div) {
  background-color: rgb(156 163 175 / 0.6);
}
</style>
