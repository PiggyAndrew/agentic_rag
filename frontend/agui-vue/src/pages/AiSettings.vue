<script setup lang="ts">
import { computed, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { useAiStore } from '@/stores/ai'

const store = useAiStore()

const form = reactive({
  apiBaseUrl: store.apiBaseUrl,
  llmApiKey: store.llmApiKey,
  llmBaseUrl: store.llmBaseUrl,
  llmModel: store.llmModel,
  embeddingBaseUrl: store.embeddingBaseUrl,
  embeddingModel: store.embeddingModel,
  embeddingApiKey: store.embeddingApiKey,
  rerankerBaseUrl: store.rerankerBaseUrl,
  rerankerModel: store.rerankerModel,
  rerankerApiKey: store.rerankerApiKey,
})

const chatApiPreview = computed(() => {
  const base = String(form.apiBaseUrl || '').trim().replace(/\/+$/, '')
  return base ? `${base}/api/chat` : ''
})

function save(): void {
  store.apiBaseUrl = String(form.apiBaseUrl || '').trim()
  store.llmApiKey = String(form.llmApiKey || '').trim()
  store.llmBaseUrl = String(form.llmBaseUrl || '').trim()
  store.llmModel = String(form.llmModel || '').trim()
  store.embeddingBaseUrl = String(form.embeddingBaseUrl || '').trim()
  store.embeddingModel = String(form.embeddingModel || '').trim()
  store.embeddingApiKey = String(form.embeddingApiKey || '').trim()
  store.rerankerBaseUrl = String(form.rerankerBaseUrl || '').trim()
  store.rerankerModel = String(form.rerankerModel || '').trim()
  store.rerankerApiKey = String(form.rerankerApiKey || '').trim()
  ElMessage.success('已保存 AI 配置')
}

function reset(): void {
  form.apiBaseUrl = ''
  form.llmApiKey = ''
  form.llmBaseUrl = ''
  form.llmModel = ''
  form.embeddingBaseUrl = ''
  form.embeddingModel = ''
  form.embeddingApiKey = ''
  form.rerankerBaseUrl = ''
  form.rerankerModel = ''
  form.rerankerApiKey = ''
  save()
}
</script>

<template>
  <el-container class="h-full w-full bg-background">
    <el-main class="p-6">
      <el-card class="settings-card max-w-3xl mx-auto">
        <template #header>
          <div class="flex items-center justify-between">
            <div>
              <div class="text-lg font-semibold">AI 配置</div>
              <div class="text-xs text-muted-foreground">为当前浏览器/客户端保存个人配置</div>
            </div>
            <div class="flex items-center gap-2">
              <el-button @click="reset">清空</el-button>
              <el-button type="primary" @click="save">保存</el-button>
            </div>
          </div>
        </template>

        <el-tabs class="settings-tabs" type="border-card">
          <el-tab-pane label="通用">
            <el-form label-position="top">
              <el-row :gutter="16">
                <el-col :xs="24" :sm="24" :md="14">
                  <el-form-item label="后端服务地址（可填 base，也可直接填 /api/chat）">
                    <el-input v-model="form.apiBaseUrl" placeholder="http://localhost:8000" />
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :sm="24" :md="10">
                  <el-form-item label="当前聊天接口">
                    <div class="preview-box">
                      <el-tag v-if="chatApiPreview" size="small" effect="plain">{{ chatApiPreview }}</el-tag>
                      <span v-else class="text-xs text-muted-foreground">请先填写后端地址</span>
                    </div>
                  </el-form-item>
                </el-col>
              </el-row>
            </el-form>
          </el-tab-pane>

          <el-tab-pane label="LLM">
            <el-form label-position="top">
              <el-row :gutter="16">
                <el-col :xs="24" :sm="12">
                  <el-form-item label="LLM Base URL（可选，默认走后端默认值）">
                    <el-input v-model="form.llmBaseUrl" placeholder="https://api.deepseek.com/v1" />
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :sm="12">
                  <el-form-item label="LLM Model（可选）">
                    <el-input v-model="form.llmModel" placeholder="deepseek-chat" />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-row :gutter="16">
                <el-col :xs="24">
                  <el-form-item label="LLM API Key（可选，按用户隔离）">
                    <el-input v-model="form.llmApiKey" type="password" show-password placeholder="sk-..." />
                  </el-form-item>
                </el-col>
              </el-row>
            </el-form>
          </el-tab-pane>

          <el-tab-pane label="Embedding">
            <el-form label-position="top">
              <el-row :gutter="16">
                <el-col :xs="24" :sm="12">
                  <el-form-item label="Embedding Base URL（可选）">
                    <el-input v-model="form.embeddingBaseUrl" placeholder="https://api.xxx.com/v1" />
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :sm="12">
                  <el-form-item label="Embedding Model（可选）">
                    <el-input v-model="form.embeddingModel" placeholder="text-embedding-3-large" />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-row :gutter="16">
                <el-col :xs="24">
                  <el-form-item label="Embedding API Key（可选，按用户隔离）">
                    <el-input v-model="form.embeddingApiKey" type="password" show-password placeholder="sk-..." />
                  </el-form-item>
                </el-col>
              </el-row>
            </el-form>
          </el-tab-pane>

          <el-tab-pane label="Reranker">
            <el-form label-position="top">
              <el-row :gutter="16">
                <el-col :xs="24" :sm="12">
                  <el-form-item label="Reranker Base URL（可选）">
                    <el-input v-model="form.rerankerBaseUrl" placeholder="https://api.xxx.com/v1" />
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :sm="12">
                  <el-form-item label="Reranker Model（可选）">
                    <el-input v-model="form.rerankerModel" placeholder="bge-reranker-v2" />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-row :gutter="16">
                <el-col :xs="24">
                  <el-form-item label="Reranker API Key（可选，按用户隔离）">
                    <el-input v-model="form.rerankerApiKey" type="password" show-password placeholder="sk-..." />
                  </el-form-item>
                </el-col>
              </el-row>
            </el-form>
          </el-tab-pane>
        </el-tabs>
      </el-card>
    </el-main>
  </el-container>
</template>

<style scoped>
.h-full { height: 100%; }
.w-full { width: 100%; }
.p-6 { padding: 1.5rem; }
.max-w-2xl { max-width: 42rem; }
.max-w-3xl { max-width: 56rem; }
.mx-auto { margin-left: auto; margin-right: auto; }
.mb-4 { margin-bottom: 1rem; }
.mt-2 { margin-top: 0.5rem; }
.text-base { font-size: 1rem; }
.text-lg { font-size: 1.125rem; }
.font-semibold { font-weight: 600; }
.text-xs { font-size: 0.75rem; }
.text-muted-foreground { color: var(--el-text-color-secondary); }
.flex { display: flex; }
.items-center { align-items: center; }
.justify-between { justify-content: space-between; }
.gap-2 { gap: 0.5rem; }
.settings-card :deep(.el-card__header) { padding: 14px 16px; }
.settings-tabs { border-radius: 8px; overflow: hidden; }
.preview-box { display: flex; align-items: center; min-height: 32px; }
</style>
