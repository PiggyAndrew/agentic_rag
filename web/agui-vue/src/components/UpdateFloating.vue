<script setup lang="ts">
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useUpdateStore } from '@/stores/update'

const updateStore = useUpdateStore()
const visible = computed(() => updateStore.visible)
const percent = computed(() => updateStore.percent)
const status = computed(() => updateStore.status)
const message = computed(() => updateStore.message)
const canConfirm = computed(() => status.value === 'ready' && !!updateStore.path)

/**
 * 立即更新：通知宿主执行安装程序
 */
function confirmInstall(): void {
  if (!updateStore.path) return
  // @ts-ignore
  const webview = window?.chrome?.webview
  if (webview && typeof webview.postMessage === 'function') {
    updateStore.setInstalling()
    try {
      webview.postMessage(JSON.stringify({
        type: 'app_update_execute',
        payload: { path: updateStore.path, args: '' }
      }))
      ElMessage.success('已触发安装')
    } catch {
      ElMessage.error('触发安装失败')
    }
  } else {
    ElMessage.info('非宿主环境，无法自动安装')
  }
}

/**
 * 稍后再说：关闭悬浮窗
 */
function dismiss(): void {
  updateStore.hide()
}
</script>

<template>
  <teleport to="body">
    <div v-if="visible" class="fixed right-4 bottom-4 z-50">
      <el-card class="w-80 shadow-lg">
        <div class="text-sm font-medium mb-2">应用更新</div>
        <div class="text-xs text-muted-foreground mb-3">{{ message }}</div>
        <div v-if="status === 'downloading' || status === 'checking'" class="mb-3">
          <el-progress :percentage="percent" :status="percent===100?'success':''" :stroke-width="8" />
        </div>
        <div v-if="status === 'installing'" class="mb-3">
          <el-progress :percentage="100" status="success" :stroke-width="8" />
        </div>
        <div class="flex items-center justify-end gap-2">
          <el-button v-if="canConfirm" size="small" type="primary" @click="confirmInstall">立即更新</el-button>
          <el-button size="small" @click="dismiss">稍后再说</el-button>
        </div>
      </el-card>
    </div>
  </teleport>
  </template>

<style scoped>
.fixed { position: fixed; }
.right-4 { right: 1rem; }
.bottom-4 { bottom: 1rem; }
.w-80 { width: 20rem; }
.mb-2 { margin-bottom: 0.5rem; }
.mb-3 { margin-bottom: 0.75rem; }
.shadow-lg { box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -4px rgba(0,0,0,0.1); }
.text-sm { font-size: 0.875rem; }
.text-xs { font-size: 0.75rem; }
.font-medium { font-weight: 500; }
.text-muted-foreground { color: var(--el-text-color-secondary); }
.flex { display: flex; }
.items-center { align-items: center; }
.justify-end { justify-content: flex-end; }
.gap-2 { gap: 0.5rem; }
</style>

