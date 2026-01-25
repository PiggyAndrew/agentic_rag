<script setup lang="ts">
import { Check } from '@element-plus/icons-vue'

export interface ProviderOption {
  id: number
  name: string
  modelName: string
}

export interface ActiveConfigForm {
  apiBaseUrl: string
  activeLlmProviderId?: number
  activeEmbeddingProviderId?: number
  activeRerankerProviderId?: number
  activeVllProviderId?: number
}

const props = defineProps<{
  form: ActiveConfigForm
  llmProviders: ProviderOption[]
  embeddingProviders: ProviderOption[]
  rerankerProviders: ProviderOption[]
  vllProviders: ProviderOption[]
}>()

const emit = defineEmits<{
  'update:form': [value: ActiveConfigForm]
  save: []
}>()

function updateForm<K extends keyof ActiveConfigForm>(key: K, value: ActiveConfigForm[K]) {
  emit('update:form', { ...props.form, [key]: value })
}

function getProviderName(id: number | undefined, providers: ProviderOption[]): string {
  if (!id) return ''
  const provider = providers.find(p => p.id === id)
  return provider ? `${provider.name} (${provider.modelName})` : ''
}
</script>

<template>
  <div class="p-8 max-w-3xl mx-auto space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between pb-4 border-b border-border">
      <div>
        <h2 class="text-lg font-semibold text-foreground">全局设置</h2>
        <p class="text-xs text-muted-foreground">应用程序当前会话使用的设置</p>
      </div>
      <button
        type="button"
        @click="$emit('save')"
        class="transition-all duration-normal ease-out hover:shadow-primary-sm rounded-lg bg-primary text-primary-foreground px-4 py-2 text-sm font-medium flex items-center gap-2"
      >
        <Check class="size-4" />
        <span>保存更改</span>
      </button>
    </div>

    <!-- LLM Config -->
    <div class="grid gap-4">
      <h3 class="text-sm font-medium text-primary">LLM (对话模型)</h3>
      <div class="space-y-2">
        <label class="text-sm text-muted-foreground">选择模型提供商</label>
        <select
          :value="form.activeLlmProviderId"
          @change="updateForm('activeLlmProviderId', Number($event.target.value))"
          class="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
        >
          <option :value="undefined">请选择预设配置</option>
          <option v-for="p in llmProviders" :key="p.id" :value="p.id">
            {{ p.name }} - {{ p.modelName }}
          </option>
        </select>
        <div v-if="form.activeLlmProviderId" class="text-xs text-muted-foreground">
          已选择: {{ getProviderName(form.activeLlmProviderId, llmProviders) }}
        </div>
      </div>
    </div>

    <div class="h-px bg-border" />

    <!-- Embedding Config -->
    <div class="grid gap-4">
      <h3 class="text-sm font-medium text-primary">Embedding (向量模型)</h3>
      <div class="space-y-2">
        <label class="text-sm text-muted-foreground">选择模型提供商</label>
        <select
          :value="form.activeEmbeddingProviderId"
          @change="updateForm('activeEmbeddingProviderId', Number($event.target.value))"
          class="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
        >
          <option :value="undefined">请选择预设配置</option>
          <option v-for="p in embeddingProviders" :key="p.id" :value="p.id">
            {{ p.name }} - {{ p.modelName }}
          </option>
        </select>
      </div>
    </div>

    <div class="h-px bg-border" />

    <!-- Reranker Config -->
    <div class="grid gap-4">
      <h3 class="text-sm font-medium text-primary">Reranker (重排序模型)</h3>
      <div class="space-y-2">
        <label class="text-sm text-muted-foreground">选择模型提供商</label>
        <select
          :value="form.activeRerankerProviderId"
          @change="updateForm('activeRerankerProviderId', Number($event.target.value))"
          class="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
        >
          <option :value="undefined">请选择预设配置</option>
          <option v-for="p in rerankerProviders" :key="p.id" :value="p.id">
            {{ p.name }} - {{ p.modelName }}
          </option>
        </select>
      </div>
    </div>

    <div class="h-px bg-border" />

    <!-- VLL Config -->
    <div class="grid gap-4">
      <h3 class="text-sm font-medium text-primary">VLL (视觉语言模型)</h3>
      <div class="space-y-2">
        <label class="text-sm text-muted-foreground">选择模型提供商</label>
        <select
          :value="form.activeVllProviderId"
          @change="updateForm('activeVllProviderId', Number($event.target.value))"
          class="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
        >
          <option :value="undefined">请选择预设配置</option>
          <option v-for="p in vllProviders" :key="p.id" :value="p.id">
            {{ p.name }} - {{ p.modelName }}
          </option>
        </select>
      </div>
    </div>
  </div>
</template>
