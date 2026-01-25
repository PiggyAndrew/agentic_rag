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

</script>

<template>
  <teleport to="body">
    <div v-if="visible" class="fixed right-4 bottom-4 z-[var(--z-modal)]">
      <div class="w-80 rounded-xl bg-card border border-border shadow-xl p-4">
        <div class="text-sm font-medium text-foreground mb-2">应用更新</div>
        <div class="text-xs text-muted-foreground mb-3">{{ message }}</div>
        <div v-if="status === 'downloading' || status === 'checking'" class="mb-3">
          <el-progress :percentage="percent" :status="percent===100?'success':''" :stroke-width="8" />
        </div>
        <div v-if="status === 'installing'" class="mb-3">
          <el-progress :percentage="100" status="success" :stroke-width="8" />
        </div>
        <div class="flex items-center justify-end">
          <button
            v-if="canConfirm"
            class="px-4 py-2 text-sm font-medium text-primary-foreground bg-primary rounded-lg transition-all duration-normal ease-out hover:bg-primary/90 hover:shadow-primary-sm"
            @click="confirmInstall"
          >
            立即更新
          </button>
        </div>
      </div>
    </div>
  </teleport>
  </template>

<style scoped>
/* Remove scoped styles - use Tailwind classes instead */
</style>
