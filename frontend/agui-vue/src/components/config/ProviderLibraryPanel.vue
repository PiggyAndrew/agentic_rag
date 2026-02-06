<script setup lang="ts">
import { Plus, Edit, Delete } from '@element-plus/icons-vue'

export interface Provider {
  id: number
  name: string
  providerType: string
  baseUrl?: string
  modelName?: string
  category?: string
}

defineProps<{
  providers: Provider[]
  loading: boolean
}>()

const emit = defineEmits<{
  add: []
  edit: [provider: Provider]
  delete: [provider: Provider]
}>()

function getCategoryLabel(provider: Provider): string {
  const map: Record<string, string> = {
    llm: 'LLM',
    embedding: 'Embedding',
    reranker: 'Reranker',
    vll: 'VLL'
  }
  return map[provider.category || 'llm'] || 'Other'
}

function getCategoryColor(provider: Provider): string {
  const map: Record<string, string> = {
    llm: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    embedding: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
    reranker: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
    vll: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300'
  }
  return map[provider.category || 'llm'] || 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-300'
}
</script>

<template>
  <div class="p-8">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h2 class="text-lg font-semibold text-foreground">已保存的提供商</h2>
        <p class="text-xs text-muted-foreground">管理您的可复用提供商配置</p>
      </div>
      <button
        type="button"
        @click="$emit('add')"
        class="transition-all duration-normal ease-out hover:shadow-primary-sm rounded-lg bg-primary text-primary-foreground px-4 py-2 text-sm font-medium flex items-center gap-2"
      >
        <Plus class="size-4" />
        <span>添加提供商</span>
      </button>
    </div>

    <!-- Provider Table -->
    <div v-if="!loading && providers.length > 0" class="rounded-xl overflow-hidden border border-border">
      <table class="w-full">
        <thead class="bg-muted/30">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-muted-foreground w-[180px]">名称</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-muted-foreground w-[100px]">类型</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-muted-foreground min-w-[200px]">Base URL</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-muted-foreground w-[150px]">模型</th>
            <th class="px-4 py-3 text-right text-xs font-medium text-muted-foreground w-[120px]">操作</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border">
          <tr v-for="provider in providers" :key="provider.id" class="hover:bg-muted/20 transition-colors">
            <td class="px-4 py-3 text-sm text-foreground">{{ provider.name }}</td>
            <td class="px-4 py-3">
              <span class="inline-flex items-center px-2 py-1 rounded text-xs font-medium" :class="getCategoryColor(provider)">
                {{ getCategoryLabel(provider) }}
              </span>
            </td>
            <td class="px-4 py-3 text-sm text-muted-foreground truncate max-w-[250px]" :title="provider.baseUrl">
              {{ provider.baseUrl || '-' }}
            </td>
            <td class="px-4 py-3 text-sm text-muted-foreground">{{ provider.modelName || '-' }}</td>
            <td class="px-4 py-3 text-right">
              <div class="flex items-center justify-end gap-1">
                <button
                  type="button"
                  @click="$emit('edit', provider)"
                  class="p-1.5 rounded hover:bg-primary/10 text-muted-foreground hover:text-primary transition-colors"
                  title="编辑"
                >
                  <Edit class="size-3.5" />
                </button>
                <button
                  type="button"
                  @click="$emit('delete', provider)"
                  class="p-1.5 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors"
                  title="删除"
                >
                  <Delete class="size-3.5" />
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Empty State -->
    <div v-else-if="!loading && providers.length === 0" class="flex flex-col items-center justify-center py-12 text-center">
      <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-muted mb-4">
        <Edit class="size-6 text-muted-foreground/40" />
      </div>
      <h3 class="text-sm font-medium text-foreground mb-1">暂无提供商</h3>
      <p class="text-xs text-muted-foreground mb-4">点击上方按钮添加您的第一个提供商配置</p>
    </div>

    <!-- Loading State -->
    <div v-else class="flex items-center justify-center py-12">
      <div class="text-sm text-muted-foreground">加载中...</div>
    </div>
  </div>
</template>
