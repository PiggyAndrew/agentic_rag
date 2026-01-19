<script setup lang="ts">
import { computed, ref, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, CopyDocument, Search } from '@element-plus/icons-vue'
import { StreamMarkdown } from 'streamdown-vue'

interface ChunkItem {
  file_id?: number
  chunk_index: number
  content: string
  metadata?: Record<string, any>
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
const activeChunkIndex = ref<number | null>(null)

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

function scrollToChunk(index: number) {
  activeChunkIndex.value = index
  nextTick(() => {
    const el = document.getElementById(`chunk-card-${index}`)
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

function getMetaCore(metadata?: Record<string, any> | null): any | null {
  if (!metadata) return null
  const data = (metadata as any).data
  if (data && typeof data === 'object') return data
  return metadata
}

function getMetaNumber(metadata?: Record<string, any> | null): string | undefined {
  const core = getMetaCore(metadata)
  if (!core) return undefined
  const value = (core as any).number
  if (value === undefined || value === null) return undefined
  return String(value)
}

function getMetaTitle(metadata?: Record<string, any> | null): string | undefined {
  const core = getMetaCore(metadata)
  if (!core) return undefined
  const value = (core as any).title
  if (typeof value !== 'string') return undefined
  return value
}
</script>

<template>
  <el-dialog 
    v-model="visible" 
    :title="`文件片段详情（${total}）`" 
    width="85%" 
    class="chunk-dialog !rounded-xl overflow-hidden"
    destroy-on-close
    align-center
    top="5vh"
  >
    <div class="flex h-[75vh] -mx-6 -my-5 border-t border-gray-100">
      <!-- 左侧导航栏 -->
      <div class="w-72 border-r bg-gray-50/50 flex flex-col shrink-0">
        <div class="p-4 border-b bg-white/80 backdrop-blur-sm sticky top-0 z-10">
          <el-input
            v-model="searchQuery"
            placeholder="搜索片段内容..."
            size="default"
            class="!rounded-lg"
            clearable
          >
            <template #prefix>
              <el-icon class="text-gray-400"><Search /></el-icon>
            </template>
          </el-input>
        </div>
        
        <div class="flex-1 overflow-hidden">
          <el-scrollbar>
            <div class="p-3 space-y-2">
              <template v-if="filteredChunks.length > 0">
                <div 
                  v-for="item in filteredChunks" 
                  :key="item.chunk_index"
                  class="group relative px-4 py-3 rounded-xl cursor-pointer transition-all duration-300 border"
                  :class="activeChunkIndex === item.chunk_index 
                    ? 'bg-white border-primary/30 shadow-md ring-1 ring-primary/10 z-10' 
                    : 'bg-transparent border-transparent hover:bg-white hover:border-gray-200 hover:shadow-sm text-gray-600'"
                  @click="scrollToChunk(item.chunk_index)"
                >
                  <!-- 选中指示点 -->
                  <div v-if="activeChunkIndex === item.chunk_index" 
                    class="absolute left-1.5 top-1/2 -translate-y-1/2 w-1 h-8 bg-primary rounded-full">
                  </div>

                  <div class="flex items-center justify-between gap-2 mb-1.5">
                    <span class="font-mono font-bold text-xs px-2 py-0.5 rounded-md" 
                      :class="activeChunkIndex === item.chunk_index ? 'bg-primary/10 text-primary' : 'bg-gray-100 text-gray-500'">
                      #{{ item.chunk_index }}
                    </span>
                    <span class="text-[10px] text-gray-400 font-medium">{{ item.content.length }} 字符</span>
                  </div>
                  
                  <div class="text-xs text-gray-600 line-clamp-2 leading-relaxed opacity-90 group-hover:opacity-100">
                     {{ item.content.slice(0, 60) }}...
                  </div>

                  <template v-if="item.metadata && (getMetaNumber(item.metadata) || getMetaTitle(item.metadata))">
                     <div class="mt-2 pt-2 border-t border-dashed border-gray-100 flex flex-wrap gap-1">
                        <span v-if="getMetaNumber(item.metadata)" class="inline-flex items-center px-1.5 py-0.5 rounded bg-blue-50 text-blue-600 text-[10px] font-medium">
                          {{ getMetaNumber(item.metadata) }}
                        </span>
                        <span v-if="getMetaTitle(item.metadata)" class="inline-flex items-center px-1.5 py-0.5 rounded bg-gray-100 text-gray-600 text-[10px] truncate max-w-full">
                          {{ getMetaTitle(item.metadata) }}
                        </span>
                     </div>
                  </template>
                </div>
              </template>
              <div v-else class="py-12 flex flex-col items-center justify-center text-gray-400">
                <div class="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center mb-3">
                   <el-icon class="opacity-30" size="20"><Search /></el-icon>
                </div>
                <span class="text-xs">未找到匹配的片段</span>
              </div>
            </div>
          </el-scrollbar>
        </div>
        
        <div class="p-2 border-t bg-white/50 text-[10px] text-center text-gray-400 font-mono">
          {{ filteredChunks.length }} / {{ total }} FRAGMENTS
        </div>
      </div>

      <!-- 右侧内容区域 -->
      <div class="flex-1 flex flex-col min-w-0 bg-gray-50/30">
        <el-scrollbar class="flex-1">
          <div class="p-8 space-y-8">
            <template v-if="filteredChunks.length > 0">
              <div 
                v-for="item in filteredChunks" 
                :key="item.chunk_index"
                :id="`chunk-card-${item.chunk_index}`"
                class="group bg-white rounded-xl border border-gray-100 shadow-sm transition-all duration-300 overflow-hidden scroll-mt-6 hover:shadow-md hover:border-primary/20"
                :class="activeChunkIndex === item.chunk_index ? 'ring-2 ring-primary ring-offset-4 shadow-lg border-primary/20' : ''"
              >
                <!-- 片段头部 -->
                <div class="flex items-center justify-between px-5 py-3 bg-gradient-to-r from-gray-50 to-white border-b border-gray-100">
                  <div class="flex items-center gap-3">
                    <div class="flex items-center justify-center w-8 h-8 rounded-lg bg-white border shadow-sm text-primary text-sm font-mono font-bold">
                      #{{ item.chunk_index }}
                    </div>
                    <div class="flex flex-col">
                      <span class="text-xs font-medium text-gray-500 uppercase tracking-wide">Fragment ID</span>
                      <span class="text-[10px] text-gray-400 font-mono">Length: {{ item.content.length }}</span>
                    </div>
                  </div>
                  <el-button 
                    type="primary" 
                    link 
                    size="small" 
                    :icon="CopyDocument"
                    @click="copyContent(item.content)"
                    class="!text-gray-400 hover:!text-primary transition-colors"
                  >
                    复制
                  </el-button>
                </div>

                <!-- 片段内容 -->
                <div class="p-6">
                  <div class="relative group/content">
                    <StreamMarkdown
                      :content="item.content"
                      :shiki-theme="{ light: 'github-light', dark: 'github-dark' }"
                      class="text-sm leading-7 text-gray-700 font-normal prose prose-sm max-w-none prose-p:my-2 prose-headings:mb-3 prose-headings:mt-4 prose-code:bg-gray-100 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none"
                    />
                  </div>
                  
                  <!-- 元数据展示 -->
                  <div v-if="item.metadata && Object.keys(item.metadata).length > 0" class="mt-6 pt-4 border-t border-dashed border-gray-200">
                    <div class="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-3 flex items-center gap-2">
                      <el-icon><Document /></el-icon>
                      Metadata
                    </div>
                    <div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
                      <div 
                        v-for="(value, key) in item.metadata" 
                        :key="key"
                        class="flex flex-col p-2 rounded-lg bg-gray-50 border border-gray-100 hover:bg-white hover:shadow-sm transition-all duration-200"
                      >
                        <span class="text-[10px] font-medium text-gray-400 mb-0.5 uppercase">{{ key }}</span>
                        <div class="text-xs text-gray-700 font-medium truncate" :title="String(value)">
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
            <div v-else class="flex flex-col items-center justify-center h-full py-20 text-gray-400">
              <div class="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
                 <el-icon size="32" class="opacity-20"><Search /></el-icon>
              </div>
              <span class="text-sm font-medium text-gray-500">未找到匹配的片段</span>
              <span class="text-xs mt-1 text-gray-400">尝试更换搜索关键词</span>
            </div>
          </div>
        </el-scrollbar>
      </div>
    </div>
  </el-dialog>
</template>

<style scoped>
/* 移除之前的样式，使用 Tailwind 类为主 */
</style>
