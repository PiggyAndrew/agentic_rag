<script setup lang="ts">
import { ref, reactive, watch, computed } from 'vue'
import { Connection } from '@element-plus/icons-vue'

export interface LLMPreset {
  providerType: string
  name: string
  baseUrl: string
  defaultModel: string
  description?: string
  supportedCategories?: string[]
}

export interface ProviderForm {
  name: string
  category: 'llm' | 'embedding' | 'reranker' | 'vll'
  providerType: string
  baseUrl: string
  apiKey: string
  modelName: string
  description: string
}

const props = defineProps<{
  modelValue: boolean
  mode: 'add' | 'edit'
  presets: LLMPreset[]
  initialData?: ProviderForm
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  confirm: [form: ProviderForm]
  test: []
}>()

// Form state
const form = reactive<ProviderForm>({
  name: '',
  category: 'llm',
  providerType: 'openai',
  baseUrl: '',
  apiKey: '',
  modelName: '',
  description: ''
})

const testingConnection = ref(false)

// Computed
const filteredPresets = computed(() => {
  return props.presets.filter(p => {
    if (Array.isArray(p.supportedCategories) && p.supportedCategories.length > 0) {
      return p.supportedCategories.includes(form.category)
    }
    return form.category === 'llm'
  })
})

const title = computed(() => {
  return props.mode === 'edit' ? '编辑提供商' : '添加提供商'
})

const isFormValid = computed(() => {
  return form.name.trim() &&
         form.providerType &&
         form.baseUrl.trim() &&
         form.modelName.trim()
})

// Watchers
watch(() => props.modelValue, (show) => {
  if (show && props.mode === 'add') {
    resetForm()
  } else if (show && props.mode === 'edit' && props.initialData) {
    Object.assign(form, props.initialData)
  }
})

// Methods
function resetForm() {
  Object.assign(form, {
    name: '',
    category: 'llm',
    providerType: 'openai',
    baseUrl: '',
    apiKey: '',
    modelName: '',
    description: ''
  })
}

function handlePresetChange(type: string) {
  const preset = props.presets.find(p => p.providerType === type)
  if (preset) {
    form.baseUrl = preset.baseUrl
    form.modelName = preset.defaultModel
  }
}

function handleCancel() {
  emit('update:modelValue', false)
}

function handleConfirm() {
  if (!isFormValid.value) return
  emit('confirm', { ...form })
}

async function handleTestConnection() {
  if (!form.baseUrl.trim() || !form.modelName.trim()) {
    alert('请先填写 Base URL 和 模型名称')
    return
  }
  testingConnection.value = true
  try {
    emit('test')
    // Test result will be handled by parent
  } finally {
    testingConnection.value = false
  }
}
</script>

<template>
  <div v-if="modelValue" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
    <div class="bg-card rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-auto m-4">
      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-border">
        <h2 class="text-lg font-semibold text-foreground">{{ title }}</h2>
        <button
          type="button"
          @click="handleCancel"
          class="p-2 rounded hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
        >
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Body -->
      <div class="px-6 py-4 space-y-4">
        <!-- Name -->
        <div class="space-y-2">
          <label class="text-sm font-medium text-foreground">名称 <span class="text-destructive">*</span></label>
          <input
            v-model="form.name"
            type="text"
            placeholder="例如: My OpenAI GPT-4"
            class="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>

        <!-- Category -->
        <div class="space-y-2">
          <label class="text-sm font-medium text-foreground">模型类型</label>
          <div class="flex gap-2 flex-wrap">
            <button
              v-for="cat in ['llm', 'embedding', 'reranker', 'vll']"
              :key="cat"
              type="button"
              @click="form.category = cat as any; form.providerType = ''"
              :class="form.category === cat
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground hover:bg-muted/70'"
              class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            >
              {{ cat === 'llm' ? '对话模型 (LLM)' : cat === 'embedding' ? '向量模型 (Embedding)' : cat === 'reranker' ? '重排序模型 (Reranker)' : '视觉模型 (VLL)' }}
            </button>
          </div>
        </div>

        <!-- Provider Type -->
        <div class="space-y-2">
          <label class="text-sm font-medium text-foreground">提供商类型 <span class="text-destructive">*</span></label>
          <select
            :disabled="mode === 'edit'"
            v-model="form.providerType"
            @change="handlePresetChange(form.providerType)"
            class="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <option value="">选择类型</option>
            <option v-for="preset in filteredPresets" :key="preset.providerType" :value="preset.providerType">
              {{ preset.name }}
              <span v-if="preset.description" class="text-xs text-muted-foreground ml-2">{{ preset.description }}</span>
            </option>
          </select>
        </div>

        <!-- Base URL -->
        <div class="space-y-2">
          <label class="text-sm font-medium text-foreground">Base URL <span class="text-destructive">*</span></label>
          <input
            v-model="form.baseUrl"
            type="url"
            placeholder="https://api.openai.com/v1"
            class="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>

        <!-- Model Name -->
        <div class="space-y-2">
          <label class="text-sm font-medium text-foreground">模型名称 <span class="text-destructive">*</span></label>
          <input
            v-model="form.modelName"
            type="text"
            placeholder="gpt-4"
            class="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>

        <!-- API Key -->
        <div class="space-y-2">
          <label class="text-sm font-medium text-foreground">API Key</label>
          <input
            v-model="form.apiKey"
            type="password"
            placeholder="sk-..."
            class="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>

        <!-- Description -->
        <div class="space-y-2">
          <label class="text-sm font-medium text-foreground">描述</label>
          <textarea
            v-model="form.description"
            rows="2"
            placeholder="可选描述"
            class="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 resize-none"
          />
        </div>
      </div>

      <!-- Footer -->
      <div class="flex items-center justify-between gap-4 px-6 py-4 border-t border-border bg-muted/30">
        <button
          type="button"
          @click="handleTestConnection"
          :disabled="testingConnection || !form.baseUrl.trim() || !form.modelName.trim()"
          class="px-4 py-2 rounded-lg text-sm font-medium border border-warning text-warning hover:bg-warning/10 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors"
        >
          <Connection class="size-4" />
          <span>测试连接</span>
        </button>
        <div class="flex gap-2">
          <button
            type="button"
            @click="handleCancel"
            class="px-4 py-2 rounded-lg text-sm font-medium border border-border hover:bg-muted transition-colors"
          >
            取消
          </button>
          <button
            type="button"
            @click="handleConfirm"
            :disabled="!isFormValid"
            class="px-4 py-2 rounded-lg text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            确认
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
