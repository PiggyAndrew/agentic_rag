<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAiStore } from '@/stores/ai'
import {
  getLLMPresets,
  getLLMProviders,
  createLLMProvider,
  updateLLMProvider,
  deleteLLMProvider,
  testLLMConnection,
  setActiveLLMConfig,
  getActiveLLMConfig,
  type LLMPreset,
  type LLMProvider,
} from '@/api/llm'
import ConfigSidebar, { type NavItem } from '@/components/config/ConfigSidebar.vue'
import ActiveConfigPanel, { type ActiveConfigForm } from '@/components/config/ActiveConfigPanel.vue'
import ProviderLibraryPanel, { type Provider as LibraryProvider } from '@/components/config/ProviderLibraryPanel.vue'
import ProviderDialog, { type ProviderForm } from '@/components/config/ProviderDialog.vue'
import { Plus, Setting } from '@element-plus/icons-vue'

// 导航项
const navItems: NavItem[] = [
  { key: 'active-config', label: '当前激活配置', icon: Setting },
  { key: 'provider-library', label: '提供商库', icon: Plus },
]

// 状态
const activeTab = ref('active-config')
const store = useAiStore()
const loading = ref(false)
const providers = ref<LLMProvider[]>([])
const presets = ref<LLMPreset[]>([])

// 表单状态
const globalForm = reactive<ActiveConfigForm>({
  apiBaseUrl: store.apiBaseUrl,
  activeLlmProviderId: undefined,
  activeEmbeddingProviderId: undefined,
  activeRerankerProviderId: undefined,
  activeVllProviderId: undefined,
})

// 对话框状态
const showProviderDialog = ref(false)
const dialogMode = ref<'add' | 'edit'>('add')
const currentProvider = ref<LLMProvider | null>(null)

// 分类后的提供商
const llmProviders = computed(() =>
  providers.value.filter(p => (p.category || 'llm') === 'llm').map(p => ({
    id: p.id,
    name: p.name,
    modelName: p.modelName || ''
  }))
)

const embeddingProviders = computed(() =>
  providers.value.filter(p => (p.category || '') === 'embedding').map(p => ({
    id: p.id,
    name: p.name,
    modelName: p.modelName || ''
  }))
)

const rerankerProviders = computed(() =>
  providers.value.filter(p => (p.category || '') === 'reranker').map(p => ({
    id: p.id,
    name: p.name,
    modelName: p.modelName || ''
  }))
)

const vllProviders = computed(() =>
  providers.value.filter(p => (p.category || '') === 'vll').map(p => ({
    id: p.id,
    name: p.name,
    modelName: p.modelName || ''
  }))
)

// 对话框表单初始值
const dialogFormInitial = computed<ProviderForm | undefined>(() => {
  if (dialogMode.value === 'add') return undefined
  if (!currentProvider.value) return undefined
  return {
    name: currentProvider.value.name,
    category: currentProvider.value.category || 'llm',
    providerType: currentProvider.value.providerType,
    baseUrl: currentProvider.value.baseUrl || '',
    apiKey: currentProvider.value.apiKey || '',
    modelName: currentProvider.value.modelName || '',
    description: currentProvider.value.description || '',
  }
})

// API 基础 URL
function getApiBase(): string {
  const raw = (import.meta as any).env?.VITE_API_BASE || (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000'
  const s = String(raw || '').trim()
  if (!s) return 'http://localhost:8000'
  if (s.endsWith('/api/chat')) return s.slice(0, -'/api/chat'.length)
  return s.replace(/\/+$/, '')
}

// 全局配置操作
async function loadGlobalConfig() {
  try {
    const active = await getActiveLLMConfig()
    globalForm.activeLlmProviderId = active.llm?.id
    globalForm.activeEmbeddingProviderId = active.embedding?.id
    globalForm.activeRerankerProviderId = active.reranker?.id
    globalForm.activeVllProviderId = active.vll?.id
    await store.load()
  } catch (err: any) {
    console.warn('Load config failed:', err?.message || err)
  }
}

async function saveGlobalConfig() {
  store.apiBaseUrl = String(globalForm.apiBaseUrl || '').trim()
  const payload = (v: any, desc?: string) => JSON.stringify({ value: v, description: desc ?? undefined })
  try {
    await Promise.all([
      fetch(`${getApiBase()}/api/config/api_base_url`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: payload(String(globalForm.apiBaseUrl || '').trim())
      }),
      setActiveLLMConfig({
        llmId: globalForm.activeLlmProviderId,
        embeddingId: globalForm.activeEmbeddingProviderId,
        rerankerId: globalForm.activeRerankerProviderId,
        vllId: globalForm.activeVllProviderId,
      }),
    ])
    await store.load()
    ElMessage.success('配置已保存')
  } catch (err: any) {
    ElMessage.error(err?.message || '保存失败')
  }
}

// 提供商管理操作
async function loadProviders() {
  loading.value = true
  try {
    const [pList, presetList] = await Promise.all([getLLMProviders(), getLLMPresets()])
    providers.value = pList
    presets.value = presetList
  } catch (error: any) {
    ElMessage.error(error?.message || '加载配置失败')
  } finally {
    loading.value = false
  }
}

function openAddDialog() {
  dialogMode.value = 'add'
  currentProvider.value = null
  showProviderDialog.value = true
}

function openEditDialog(provider: LLMProvider) {
  dialogMode.value = 'edit'
  currentProvider.value = provider
  showProviderDialog.value = true
}

async function handleProviderConfirm(form: ProviderForm) {
  try {
    if (dialogMode.value === 'add') {
      await createLLMProvider(form)
      ElMessage.success('创建成功')
    } else {
      await updateLLMProvider(currentProvider.value!.id, form)
      ElMessage.success('更新成功')
    }
    showProviderDialog.value = false
    currentProvider.value = null
    await loadProviders()
  } catch (error: any) {
    ElMessage.error(dialogMode.value === 'add' ? '创建失败' : '更新失败')
  }
}

async function handleProviderDelete(provider: LibraryProvider) {
  try {
    await ElMessageBox.confirm(
      `确定要删除配置 "${provider.name}" 吗？`,
      '删除确认',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    await deleteLLMProvider(provider.id)
    ElMessage.success('删除成功')
    await loadProviders()
  } catch (error: any) {
    if (error !== 'cancel') ElMessage.error(error?.message || '删除失败')
  }
}

async function handleTestConnection(form: ProviderForm) {
  try {
    const res = await testLLMConnection({
      baseUrl: form.baseUrl,
      apiKey: form.apiKey || '',
      modelName: form.modelName,
    })
    ElMessage.success(`连接成功: ${res.message}`)
  } catch (error: any) {
    ElMessage.error(`连接失败: ${error.message}`)
  }
}

// 生命周期
onMounted(async () => {
  await loadGlobalConfig()
  await loadProviders()
})
</script>

<template>
  <div class="h-full w-full bg-background font-sans flex overflow-hidden">
    <!-- 左侧导航栏 -->
    <ConfigSidebar
      :active-tab="activeTab"
      :nav-items="navItems"
      @update:active-tab="activeTab = $event"
    />

    <!-- 右侧内容区域 -->
    <div class="flex-1 min-w-0 overflow-auto">
      <!-- 当前激活配置 -->
      <ActiveConfigPanel
        v-show="activeTab === 'active-config'"
        :form="globalForm"
        :llm-providers="llmProviders"
        :embedding-providers="embeddingProviders"
        :reranker-providers="rerankerProviders"
        :vll-providers="vllProviders"
        @update:form="globalForm = $event"
        @save="saveGlobalConfig"
      />

      <!-- 提供商库 -->
      <ProviderLibraryPanel
        v-show="activeTab === 'provider-library'"
        :providers="providers"
        :loading="loading"
        @add="openAddDialog"
        @edit="openEditDialog"
        @delete="handleProviderDelete"
      />
    </div>

    <!-- 提供商对话框 -->
    <ProviderDialog
      v-model="showProviderDialog"
      :mode="dialogMode"
      :presets="presets"
      :initial-data="dialogFormInitial"
      @confirm="handleProviderConfirm"
      @test="handleTestConnection"
    />
  </div>
</template>
