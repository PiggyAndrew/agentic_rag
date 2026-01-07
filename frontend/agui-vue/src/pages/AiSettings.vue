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
  ElMessage.success('已保存 AI 配置')
}

function reset(): void {
  form.apiBaseUrl = ''
  form.llmApiKey = ''
  form.llmBaseUrl = ''
  form.llmModel = ''
  save()
}
</script>

<template>
  <el-container class="h-full w-full bg-background">
    <el-main class="p-6">
      <el-card class="max-w-2xl mx-auto">
        <div class="flex items-center justify-between mb-4">
          <div>
            <div class="text-base font-semibold">AI 配置</div>
            <div class="text-xs text-muted-foreground">为当前浏览器/客户端保存个人配置</div>
          </div>
          <div class="flex items-center gap-2">
            <el-button type="primary" @click="save">保存</el-button>
            <el-button @click="reset">清空</el-button>
          </div>
        </div>

        <el-form label-position="top">
          <el-form-item label="后端服务地址（可填 base，也可直接填 /api/chat）">
            <el-input v-model="form.apiBaseUrl" placeholder="http://localhost:8000" />
            <div v-if="chatApiPreview" class="text-xs text-muted-foreground mt-2">
              当前聊天接口：{{ chatApiPreview }}
            </div>
          </el-form-item>

          <el-divider />

          <el-form-item label="LLM Base URL（可选，默认走后端默认值）">
            <el-input v-model="form.llmBaseUrl" placeholder="https://api.deepseek.com/v1" />
          </el-form-item>

          <el-form-item label="LLM Model（可选）">
            <el-input v-model="form.llmModel" placeholder="deepseek-chat" />
          </el-form-item>

          <el-form-item label="LLM API Key（可选，按用户隔离）">
            <el-input v-model="form.llmApiKey" type="password" show-password placeholder="sk-..." />
          </el-form-item>
        </el-form>
      </el-card>
    </el-main>
  </el-container>
</template>

<style scoped>
.h-full { height: 100%; }
.w-full { width: 100%; }
.p-6 { padding: 1.5rem; }
.max-w-2xl { max-width: 42rem; }
.mx-auto { margin-left: auto; margin-right: auto; }
.mb-4 { margin-bottom: 1rem; }
.mt-2 { margin-top: 0.5rem; }
.text-base { font-size: 1rem; }
.font-semibold { font-weight: 600; }
.text-xs { font-size: 0.75rem; }
.text-muted-foreground { color: var(--el-text-color-secondary); }
.flex { display: flex; }
.items-center { align-items: center; }
.justify-between { justify-content: space-between; }
.gap-2 { gap: 0.5rem; }
</style>

