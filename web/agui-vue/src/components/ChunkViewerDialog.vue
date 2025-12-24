<script setup lang="ts">
import { computed } from 'vue'
import { ElMessage } from 'element-plus'

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

/**
 * 计算文本长度（字符数）
 */
function contentLength(text: string): number {
  return (text || '').length
}

/**
 * 格式化元信息为短文本
 */
function formatMetadata(meta?: Record<string, any>): string {
  if (!meta) return ''
  const entries = Object.entries(meta).slice(0, 4)
  return entries.map(([k, v]) => `${k}: ${String(v)}`).join(' | ')
}

/**
 * 复制片段内容到剪贴板
 */
async function copyContent(text: string): Promise<void> {
  await navigator.clipboard.writeText(text || '')
  ElMessage.success('已复制片段内容')
}
</script>

<template>
  <el-dialog v-model="visible" :title="`文件片段（${total}）`" width="800px" class="chunk-dialog">
    <div class="toolbar">
      <span class="muted">共 {{ total }} 个片段</span>
    </div>
    <el-table :data="props.chunks" height="520" class="chunk-table" row-key="chunk_index">
      <el-table-column type="expand" width="48">
        <template #default="{ row }">
          <div class="expand-content">
            <div class="expand-meta" v-if="row.metadata">
              <span class="meta-label">元信息</span>
              <span class="meta-text">{{ formatMetadata(row.metadata) }}</span>
            </div>
            <pre class="code">{{ row.content }}</pre>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="chunk_index" label="索引" width="90" />
      <el-table-column label="长度" width="100">
        <template #default="{ row }">
          {{ contentLength(row.content) }}
        </template>
      </el-table-column>
      <el-table-column label="元信息" min-width="200">
        <template #default="{ row }">
          <span class="meta-preview">{{ formatMetadata(row.metadata) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="内容预览" min-width="320">
        <template #default="{ row }">
          <span class="preview">{{ row.content?.slice(0, 160) }}{{ (row.content?.length || 0) > 160 ? '…' : '' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button size="small" @click="copyContent(row.content)">复制</el-button>
        </template>
      </el-table-column>
    </el-table>
    <template #footer>
      <div class="footer">
        <el-button @click="visible = false">关闭</el-button>
      </div>
    </template>
  </el-dialog>
  </template>

<style scoped>
.chunk-dialog :deep(.el-dialog__body) {
  padding-top: 8px;
}
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 2px 10px;
}
.muted {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.chunk-table :deep(.el-table__expanded-cell) {
  padding: 8px 16px;
}
.expand-content {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
}
.expand-meta {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.meta-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.meta-text {
  font-size: 12px;
  color: var(--el-text-color-regular);
}
.code {
  margin: 0;
  padding: 10px 12px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  background: var(--el-fill-color-light);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
}
.preview {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 12px;
  color: var(--el-text-color-regular);
}
.meta-preview {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.footer {
  display: flex;
  justify-content: flex-end;
}
</style>
