<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ChatLineSquare, FolderOpened, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import UpdateFloating from '@/components/UpdateFloating.vue'
import { useUpdateStore } from '@/stores/update'

const router = useRouter()
const route = useRoute()
const activePath = ref('/')
const isDark = ref<boolean>(document.documentElement.classList.contains('dark'))
const FIXED_REPO = 'PiggyAndrew/agentic_rag'
const updateStore = useUpdateStore()

onMounted(() => {
  router.push(activePath.value)
  // 注册 WebView2 消息监听，反馈更新结果
  try {
    // @ts-ignore
    const webview = window?.chrome?.webview
    if (webview && typeof webview.addEventListener === 'function') {
      webview.addEventListener('message', (e: any) => {
        try {
          const data = typeof e?.data === 'string' ? JSON.parse(e.data) : e?.data
          if (data?.type === 'app_update_progress') {
            if (typeof data?.percent === 'number') {
              updateStore.setProgress(data.percent, data?.message)
            } else if (data?.message) {
              updateStore.showChecking(data.message)
            }
          } else if (data?.type === 'app_update_result') {
            if (data?.success) {
              if (data?.path) {
                updateStore.setReady(String(data.path), data?.message)
              } else {
                ElMessage.success(data?.message || '更新成功')
              }
            } else {
              updateStore.setError(String(data?.error || '更新失败'))
            }
          }
        } catch {}
      })
    }
  } catch {}
})


/**
 * 页面导航函数：根据传入路由路径进行页面切换
 */
function navigateTo(path: string): void {
  activePath.value = path
  router.push(path)
}

watch(() => route.path, (p) => {
  activePath.value = p
})

/**
 * 应用主题：根据 isDark 切换黑白主题（通过 .dark 类控制）
 */
function applyTheme(dark: boolean): void {
  const root = document.documentElement
  if (dark) {
    root.classList.add('dark')
  } else {
    root.classList.remove('dark')
  }
}

watch(isDark, (val) => applyTheme(val), { immediate: true })

/**
 * 检查并安装更新：固定仓库 PiggyAndrew/agentic_rag
 * - WebView2 宿主：发送 app_update_install，让 WPF 下载并运行安装器
 * - 浏览器环境：打开 Releases 页面
 */
async function checkAndInstallUpdate(): Promise<void> {
  // @ts-ignore
  const webview = window?.chrome?.webview
  if (webview && typeof webview.postMessage === 'function') {
    const payload = {
      type: 'app_update_install',
      payload: {
        repo: FIXED_REPO,
        assetMatch: 'Agentic_RAG_Installer.exe'
      }
    }
    try {
      updateStore.showChecking('正在检查更新')
      webview.postMessage(JSON.stringify(payload))
      ElMessage.success('开始检查并下载更新')
    } catch (e) {
      ElMessage.error('发送更新请求失败')
    }
  } else {
    const url = `https://github.com/${FIXED_REPO}/releases/latest`
    window.open(url, '_blank')
    ElMessage.info('已打开 Releases 页面，请手动下载更新')
  }
}
</script>

<template>
  <el-container class="h-screen w-screen">
    <el-header height="56px" class="border-b px-4 flex items-center justify-between">
      <div class="text-sm font-medium text-foreground">
        Agentic RAG
      </div>
      <div class="flex items-center gap-4">
        <el-menu
          mode="horizontal"
          :default-active="activePath"
          @select="navigateTo"
          class="border-0"
        >
          <el-menu-item index="/">
            <el-icon class="mr-1"><ChatLineSquare /></el-icon>
            聊天
          </el-menu-item>
          <el-menu-item index="/kb">
            <el-icon class="mr-1"><FolderOpened /></el-icon>
            知识库
          </el-menu-item>
        </el-menu>
        <el-button size="small" type="primary" plain @click="checkAndInstallUpdate">
          <el-icon class="mr-1"><Download /></el-icon>
          检查更新
        </el-button>
        <el-switch
          v-model="isDark"
          inline-prompt
          active-text="暗黑"
          inactive-text="白色"
        />
      </div>
    </el-header>
    <el-main class="p-0 bg-background text-foreground">
      <RouterView v-slot="{ Component }">
        <KeepAlive>
          <component :is="Component" />
        </KeepAlive>
      </RouterView>
    </el-main>
  </el-container>
  <UpdateFloating />
</template>

<style>
/* Remove scoped to ensure body/html styles apply */
html, body, #app {
  height: 100%;
  width: 100%;
  margin: 0;
  padding: 0;
  overflow: hidden;
}
.border-b { border-bottom: 1px solid var(--el-border-color); }
</style>
