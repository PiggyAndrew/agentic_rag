<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
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
  type LLMProviderCreate,
} from '@/api/llm'
import { Plus, Connection, Delete, Edit, Check } from '@element-plus/icons-vue'

const activeTab = ref('active-config')
const store = useAiStore()
const loading = ref(false)
const providers = ref<LLMProvider[]>([])
const presets = ref<LLMPreset[]>([])
const selectedCategory = ref<'llm' | 'embedding' | 'reranker' | 'vll'>('llm')
const filteredPresets = computed(() =>
  presets.value.filter(p => {
    if (Array.isArray(p.supportedCategories) && p.supportedCategories.length > 0) {
      return p.supportedCategories.includes(selectedCategory.value)
    }
    return selectedCategory.value === 'llm'
  })
)

// ================= Global / Active Config Logic =================

const globalForm = reactive({
  apiBaseUrl: store.apiBaseUrl,
  activeLlmProviderId: undefined as number | undefined,
  activeEmbeddingProviderId: undefined as number | undefined,
  activeRerankerProviderId: undefined as number | undefined,
  activeVllProviderId: undefined as number | undefined,
})

function getApiBase(): string {
  const raw = (import.meta as any).env?.VITE_API_BASE || (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000'
  const s = String(raw || '').trim()
  if (!s) return 'http://localhost:8000'
  if (s.endsWith('/api/chat')) return s.slice(0, -'/api/chat'.length)
  return s.replace(/\/+$/, '')
}

async function loadGlobalConfig(): Promise<void> {
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

async function saveGlobalConfig(): Promise<void> {
  store.apiBaseUrl = String(globalForm.apiBaseUrl || '').trim()
  const payload = (v: any, desc?: string) => JSON.stringify({ value: v, description: desc ?? undefined })
  try {
    await Promise.all([
      // Save API Base URL
      fetch(`${getApiBase()}/api/config/api_base_url`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: payload(String(globalForm.apiBaseUrl || '').trim()) }),
      // Set defaults by category in one request
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

      // ================= Provider Management Logic =================

const showAddDialog = ref(false)
const showEditDialog = ref(false)
const currentProvider = ref<LLMProvider | null>(null)
const testingConnection = ref(false)

const formRef = ref<FormInstance>()
const form = reactive<LLMProviderCreate>({
  name: '',
  category: 'llm',
  providerType: 'openai',
  baseUrl: '',
  apiKey: '',
  modelName: '',
  config: {},
  isDefault: false,
  description: '',
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入配置名称', trigger: 'blur' }],
  providerType: [{ required: true, message: '请选择提供者类型', trigger: 'change' }],
  baseUrl: [{ required: true, message: '请输入Base URL', trigger: 'blur' }],
  modelName: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
}

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

function handlePresetChange(type: string) {
  const preset = presets.value.find(p => p.providerType === type)
  if (preset) {
    form.baseUrl = preset.baseUrl
    form.modelName = preset.defaultModel
  }
}

function openAddDialog() {
  Object.assign(form, {
    name: '',
    category: selectedCategory.value,
    providerType: 'openai',
    baseUrl: '',
    apiKey: '',
    modelName: '',
    config: {},
    isDefault: false,
    description: '',
  })
  showAddDialog.value = true
}

async function handleAdd() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    try {
      await createLLMProvider(form)
      ElMessage.success('创建成功')
      showAddDialog.value = false
      await loadProviders()
    } catch (error: any) {
      ElMessage.error(error?.message || '创建失败')
    }
  })
}

function openEditDialog(provider: LLMProvider) {
  currentProvider.value = provider
  Object.assign(form, {
    name: provider.name,
    category: provider.category || selectedCategory.value,
    providerType: provider.providerType,
    baseUrl: provider.baseUrl || '',
    apiKey: provider.apiKey || '',
    modelName: provider.modelName || '',
    config: provider.config || {},
    isDefault: provider.isDefault,
    description: provider.description || '',
  })
  showEditDialog.value = true
}

async function handleEdit() {
  if (!formRef.value || !currentProvider.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    try {
      await updateLLMProvider(currentProvider.value!.id, form)
      ElMessage.success('更新成功')
      showEditDialog.value = false
      currentProvider.value = null
      await loadProviders()
    } catch (error: any) {
      ElMessage.error(error?.message || '更新失败')
    }
  })
}

async function handleDelete(provider: LLMProvider) {
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

async function handleTestConnection() {
  if (!form.baseUrl || !form.modelName) {
    ElMessage.warning('请先填写 Base URL 和 模型名称')
    return
  }
  testingConnection.value = true
  try {
    const res = await testLLMConnection({
      baseUrl: form.baseUrl!,
      apiKey: form.apiKey || '',
      modelName: form.modelName!,
    })
    ElMessage.success(`连接成功: ${res.message}`)
  } catch (error: any) {
    ElMessage.error(`连接失败: ${error.message}`)
  } finally {
    testingConnection.value = false
  }
}

onMounted(async () => {
  await loadGlobalConfig()
  await loadProviders()
})
</script>

<template>
  <el-container class="h-full w-full bg-background font-sans">
    <el-main class="p-6">
      <div class="max-w-5xl mx-auto space-y-6">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-2xl font-bold font-heading text-foreground">AI 配置管理</h1>
            <p class="text-sm text-muted-foreground">管理您的 AI 提供商和全局设置</p>
          </div>
        </div>

        <el-tabs v-model="activeTab" type="border-card" class="rounded-xl shadow-sm border-0">
          <!-- Tab 1: Active Configuration -->
          <el-tab-pane label="当前激活配置" name="active-config">
            <div class="space-y-6 p-4">
              <div class="flex items-center justify-between pb-4 border-b">
                <div>
                  <h2 class="text-lg font-semibold">全局设置</h2>
                  <p class="text-xs text-muted-foreground">应用程序当前会话使用的设置</p>
                </div>
                <el-button type="primary" @click="saveGlobalConfig">
                  <el-icon class="mr-1"><Check /></el-icon>
                  保存更改
                </el-button>
              </div>

              <!-- General -->
              <!-- <div class="grid gap-4">
                <h3 class="text-sm font-medium text-primary">通用设置</h3>
                <el-form-item label="后端 API URL">
                  <el-input v-model="globalForm.apiBaseUrl" placeholder="http://localhost:8000" />
                </el-form-item>
              </div>

              <el-divider /> -->

              <!-- LLM Config -->
              <div class="grid gap-4">
                <h3 class="text-sm font-medium text-primary">LLM (对话模型)</h3>
                <el-form-item label="选择模型提供商">
                  <el-select 
                    v-model="globalForm.activeLlmProviderId"
                    placeholder="请选择预设配置" 
                    style="width: 100%"
                  >
                    <el-option v-for="p in providers.filter(pp => (pp.category || 'llm') === 'llm')" :key="p.id" :label="p.name" :value="p.id">
                      <div class="flex items-center justify-between">
                        <span>{{ p.name }}</span>
                        <span class="text-xs text-muted-foreground">{{ p.modelName }}</span>
                      </div>
                    </el-option>
                  </el-select>
                  <div v-if="globalForm.activeLlmProviderId" class="mt-2 text-xs text-muted-foreground">
                    已选择: {{ providers.find(p => p.id === globalForm.activeLlmProviderId)?.name }} ({{ providers.find(p => p.id === globalForm.activeLlmProviderId)?.modelName }})
                  </div>
                </el-form-item>
              </div>

              <el-divider />

              <!-- Embedding Config -->
              <div class="grid gap-4">
                <h3 class="text-sm font-medium text-primary">Embedding (向量模型)</h3>
                <el-form-item label="选择模型提供商">
                  <el-select 
                    v-model="globalForm.activeEmbeddingProviderId"
                    placeholder="请选择预设配置" 
                    style="width: 100%"
                  >
                    <el-option v-for="p in providers.filter(pp => (pp.category || '') === 'embedding')" :key="p.id" :label="p.name" :value="p.id">
                      <div class="flex items-center justify-between">
                        <span>{{ p.name }}</span>
                        <span class="text-xs text-muted-foreground">{{ p.modelName }}</span>
                      </div>
                    </el-option>
                  </el-select>
                </el-form-item>
              </div>

              <el-divider />

              <!-- Reranker Config -->
              <div class="grid gap-4">
                <h3 class="text-sm font-medium text-primary">Reranker (重排序模型)</h3>
                <el-form-item label="选择模型提供商">
                  <el-select 
                    v-model="globalForm.activeRerankerProviderId"
                    placeholder="请选择预设配置" 
                    style="width: 100%"
                  >
                    <el-option v-for="p in providers.filter(pp => (pp.category || '') === 'reranker')" :key="p.id" :label="p.name" :value="p.id">
                      <div class="flex items-center justify-between">
                        <span>{{ p.name }}</span>
                        <span class="text-xs text-muted-foreground">{{ p.modelName }}</span>
                      </div>
                    </el-option>
                  </el-select>
                </el-form-item>
              </div>

              <el-divider />

              <!-- VLL Config -->
              <div class="grid gap-4">
                <h3 class="text-sm font-medium text-primary">VLL (视觉语言模型)</h3>
                <el-form-item label="选择模型提供商">
                  <el-select 
                    v-model="globalForm.activeVllProviderId"
                    placeholder="请选择预设配置" 
                    style="width: 100%"
                  >
                    <el-option v-for="p in providers.filter(pp => (pp.category || '') === 'vll')" :key="p.id" :label="p.name" :value="p.id">
                      <div class="flex items-center justify-between">
                        <span>{{ p.name }}</span>
                        <span class="text-xs text-muted-foreground">{{ p.modelName }}</span>
                      </div>
                    </el-option>
                  </el-select>
                </el-form-item>
              </div>
            </div>
          </el-tab-pane>

          <!-- Tab 2: Provider Library -->
          <el-tab-pane label="提供商库" name="provider-library">
            <div class="p-4">
              <div class="flex items-center justify-between mb-4">
                <div>
                  <h2 class="text-lg font-semibold">已保存的提供商</h2>
                  <p class="text-xs text-muted-foreground">管理您的可复用提供商配置</p>
                </div>
                <el-button type="primary" @click="openAddDialog">
                  <el-icon class="mr-1"><Plus /></el-icon>
                  添加提供商
                </el-button>
              </div>

              <el-table :data="providers" v-loading="loading" stripe class="rounded-lg overflow-hidden border">
                <el-table-column prop="name" label="名称" width="180" font-weight="bold" />
                <el-table-column prop="providerType" label="类型" width="120">
                  <template #default="{ row }">
                    <el-tag size="small" effect="plain">{{ row.providerType }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="baseUrl" label="Base URL" min-width="200" show-overflow-tooltip />
                <el-table-column prop="modelName" label="模型" width="150" />
                <el-table-column label="操作" width="150" align="right">
                  <template #default="{ row }">
                    <el-button link type="primary" size="small" @click="openEditDialog(row)">
                      <el-icon><Edit /></el-icon>
                    </el-button>
                    <el-button link type="danger" size="small" @click="handleDelete(row)">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>

      <!-- Add/Edit Dialog -->
      <el-dialog 
        v-model="showAddDialog" 
        :title="showEditDialog ? '编辑提供商' : '添加提供商'" 
        width="600px"
        destroy-on-close
      >
        <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
          <el-form-item label="名称" prop="name">
            <el-input v-model="form.name" placeholder="例如: My OpenAI GPT-4" />
          </el-form-item>
          <el-form-item label="模型类型">
            <el-radio-group v-model="selectedCategory" @change="form.providerType = ''">
              <el-radio-button label="llm">对话模型 (LLM)</el-radio-button>
              <el-radio-button label="embedding">向量模型 (Embedding)</el-radio-button>
              <el-radio-button label="reranker">重排序模型 (Reranker)</el-radio-button>
              <el-radio-button label="vll">视觉模型 (VLL)</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="提供商类型" prop="providerType">
            <el-select
              v-model="form.providerType"
              placeholder="选择类型"
              @change="handlePresetChange"
              style="width: 100%"
            >
              <el-option
                v-for="preset in filteredPresets"
                :key="preset.providerType"
                :label="preset.name"
                :value="preset.providerType"
              >
                <span>{{ preset.name }}</span>
                <span class="text-xs text-muted-foreground ml-2">{{ preset.description }}</span>
              </el-option>
            </el-select>
          </el-form-item>
          <div class="grid grid-cols-2 gap-4">
            <el-form-item label="Base URL" prop="baseUrl" class="col-span-2">
              <el-input v-model="form.baseUrl" placeholder="https://api.openai.com/v1" />
            </el-form-item>
            <el-form-item label="模型名称" prop="modelName">
              <el-input v-model="form.modelName" placeholder="gpt-4" />
            </el-form-item>
            <el-form-item label="API Key" class="col-span-2">
              <el-input v-model="form.apiKey" type="password" show-password placeholder="sk-..." />
            </el-form-item>
          </div>
          <el-form-item label="描述">
            <el-input v-model="form.description" type="textarea" :rows="2" placeholder="可选描述" />
          </el-form-item>
        </el-form>
        <template #footer>
          <div class="flex justify-between w-full">
            <el-button 
              type="warning" 
              plain 
              @click="handleTestConnection" 
              :loading="testingConnection"
            >
              <el-icon class="mr-1"><Connection /></el-icon>
              测试连接
            </el-button>
            <div>
              <el-button @click="showAddDialog = false; showEditDialog = false">取消</el-button>
              <el-button type="primary" @click="showEditDialog ? handleEdit() : handleAdd()">确认</el-button>
            </div>
          </div>
        </template>
      </el-dialog>
      
      <!-- Shared Edit Dialog state wrapper -->
      <el-dialog 
        v-model="showEditDialog" 
        title="编辑提供商" 
        width="600px"
        destroy-on-close
      >
        <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
          <el-form-item label="名称" prop="name">
            <el-input v-model="form.name" />
          </el-form-item>
          <el-form-item label="提供商类型" prop="providerType">
            <el-select v-model="form.providerType" disabled>
              <el-option
                v-for="preset in presets"
                :key="preset.providerType"
                :label="preset.name"
                :value="preset.providerType"
              />
            </el-select>
          </el-form-item>
          <div class="grid grid-cols-2 gap-4">
            <el-form-item label="Base URL" prop="baseUrl" class="col-span-2">
              <el-input v-model="form.baseUrl" />
            </el-form-item>
            <el-form-item label="模型名称" prop="modelName">
              <el-input v-model="form.modelName" />
            </el-form-item>
            <el-form-item label="API Key" class="col-span-2">
              <el-input v-model="form.apiKey" type="password" show-password />
            </el-form-item>
          </div>
          <el-form-item label="描述">
            <el-input v-model="form.description" type="textarea" :rows="2" />
          </el-form-item>
        </el-form>
        <template #footer>
          <div class="flex justify-between w-full">
            <el-button 
              type="warning" 
              plain 
              @click="handleTestConnection" 
              :loading="testingConnection"
            >
              <el-icon class="mr-1"><Connection /></el-icon>
              测试连接
            </el-button>
            <div>
              <el-button @click="showEditDialog = false">取消</el-button>
              <el-button type="primary" @click="handleEdit">确认</el-button>
            </div>
          </div>
        </template>
      </el-dialog>
    </el-main>
  </el-container>
</template>

<style scoped>
:deep(.el-tabs__content) {
  padding: 0;
}
:deep(.el-card__header) {
  padding: 1rem 1.5rem;
}
</style>
