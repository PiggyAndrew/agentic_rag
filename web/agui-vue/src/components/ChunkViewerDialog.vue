<script setup lang="ts">
import { computed, ref, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, CopyDocument, Search } from '@element-plus/icons-vue'

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

const filteredChunks = computed(() => {
  if (!searchQuery.value) return props.chunks
  const q = searchQuery.value.toLowerCase()
  return props.chunks.filter(c => 
    c.content.toLowerCase().includes(q) || 
    c.chunk_index.toString().includes(q)
  )
})

/**
 * 复制片段内容到剪贴板
 */
async function copyContent(text: string): Promise<void> {
  await navigator.clipboard.writeText(text || '')
  ElMessage.success('已复制片段内容')
}

/**
 * 滚动到指定片段
 * 采用混合滚动策略：距离较近时平滑滚动，距离较远时直接跳转，兼顾体验与效率
 */
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
</script>

<template>
  <el-dialog 
    v-model="visible" 
    :title="`文件片段详情（${total}）`" 
    width="1100px" 
    class="chunk-dialog"
    destroy-on-close
    align-center
    top="5vh"
  >
    <div class="flex h-[75vh] border rounded-lg overflow-hidden bg-background">
      <!-- 左侧导航栏 -->
      <div class="w-64 border-r bg-gray-50 flex flex-col shrink-0">
        <div class="p-3 border-b bg-white">
          <el-input
            v-model="searchQuery"
            placeholder="搜索片段..."
            size="default"
            clearable
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </div>
        
        <div class="flex-1 overflow-hidden">
          <el-scrollbar>
            <div class="p-2 space-y-1">
              <template v-if="filteredChunks.length > 0">
                <div 
                  v-for="item in filteredChunks" 
                  :key="item.chunk_index"
                  class="px-3 py-2.5 rounded-md cursor-pointer hover:bg-gray-200/80 text-sm flex flex-col gap-1 transition-all duration-200 border border-transparent"
                  :class="activeChunkIndex === item.chunk_index ? 'bg-white border-primary/20 shadow-sm ring-1 ring-primary/10' : ''"
                  @click="scrollToChunk(item.chunk_index)"
                >
                  <div class="flex items-center justify-between gap-2">
                    <div class="flex items-center gap-2 min-w-0">
                      <span class="font-mono font-medium text-xs shrink-0" :class="activeChunkIndex === item.chunk_index ? 'text-primary' : 'text-gray-600'">#{{ item.chunk_index }}</span>
                      <template v-if="item.metadata">
                        <span v-if="item.metadata.number" class="text-xs text-gray-500 font-medium shrink-0">{{ item.metadata.number }}</span>
                        <span v-if="item.metadata.title" class="text-xs text-gray-500 truncate" :title="item.metadata.title">{{ item.metadata.title }}</span>
                      </template>
                    </div>
                    <span class="text-[10px] text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded-full shrink-0">{{ item.content.length }}字符</span>
                  </div>
                  <div class="text-xs text-gray-500 truncate opacity-80 pl-1 border-l-2" :class="activeChunkIndex === item.chunk_index ? 'border-primary/40' : 'border-gray-300'">
                    {{ item.content.slice(0, 30).replace(/[\r\n]+/g, ' ') }}...
                  </div>
                </div>
              </template>
              <div v-else class="py-8 text-center text-xs text-gray-400">
                无匹配结果
              </div>
            </div>
          </el-scrollbar>
        </div>
        
        <div class="p-2 border-t bg-gray-50 text-xs text-center text-gray-400 font-mono">
          显示: {{ filteredChunks.length }} / {{ total }}
        </div>
      </div>

      <!-- 右侧内容区域 -->
      <div class="flex-1 flex flex-col min-w-0 bg-gray-50/30">
        <el-scrollbar class="flex-1">
          <div class="p-6 space-y-6">
            <template v-if="filteredChunks.length > 0">
              <div 
                v-for="item in filteredChunks" 
                :key="item.chunk_index"
                :id="`chunk-card-${item.chunk_index}`"
                class="bg-white rounded-lg border shadow-sm transition-all duration-300 overflow-hidden scroll-mt-4"
                :class="activeChunkIndex === item.chunk_index ? 'ring-2 ring-primary ring-offset-2 shadow-md' : 'hover:shadow-md'"
              >
                <!-- 片段头部 -->
                <div class="flex items-center justify-between px-4 py-2.5 bg-gray-50/50 border-b">
                  <div class="flex items-center gap-3">
                    <span class="flex items-center justify-center w-7 h-7 rounded-md bg-white border shadow-sm text-primary text-xs font-mono font-bold">
                      #{{ item.chunk_index }}
                    </span>
                    <span class="text-xs text-gray-500 font-mono">
                      长度: {{ item.content.length }}
                    </span>
                  </div>
                  <el-button 
                    type="primary" 
                    link 
                    size="small" 
                    :icon="CopyDocument"
                    @click="copyContent(item.content)"
                  >
                    复制内容
                  </el-button>
                </div>

                <!-- 片段内容 -->
                <div class="p-5">
                  <div class="text-sm leading-relaxed text-gray-700 whitespace-pre-wrap font-mono bg-gray-50 rounded-md p-4 border border-gray-100">
                    {{ item.content }}
                  </div>
                  
                  <!-- 元数据展示 -->
                  <div v-if="item.metadata && Object.keys(item.metadata).length > 0" class="mt-4 pt-3 border-t border-dashed">
                    <div class="text-xs text-gray-400 mb-2 flex items-center gap-1.5 font-medium">
                      <el-icon><Document /></el-icon>
                      元数据信息
                    </div>
                    <div class="flex flex-wrap gap-2">
                      <div 
                        v-for="(value, key) in item.metadata" 
                        :key="key"
                        class="inline-flex items-center px-2.5 py-1 rounded bg-gray-100 border border-gray-200 text-xs text-gray-600 max-w-full hover:bg-gray-50 transition-colors"
                      >
                        <span class="font-medium mr-1.5 text-gray-500">{{ key }}:</span>
                        <template v-if="typeof value === 'object' && value !== null">
                           <span class="truncate max-w-[400px]" :title="JSON.stringify(value)">
                            <span v-for="(v, k) in value" :key="k">
                              <span>{{ v }}</span>
                            </span>
                           </span>
                        </template>
                        <template v-else>
                          <span class="truncate max-w-[200px] select-all" :title="String(value)">{{ value }}</span>
                        </template>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </template>
            <div v-else class="flex flex-col items-center justify-center h-full text-gray-400 pb-20">
              <el-icon size="64" class="mb-4 opacity-10"><Search /></el-icon>
              <span>未找到匹配的片段</span>
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
