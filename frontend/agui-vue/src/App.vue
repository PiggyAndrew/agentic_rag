<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ChatLineSquare, FolderOpened, Download, User, Setting, Moon, Sunny } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import UpdateFloating from '@/components/UpdateFloating.vue'
import { useUpdateStore } from '@/stores/update'

const router = useRouter()
const route = useRoute()
const activePath = ref('/')
const isDark = ref<boolean>(document.documentElement.classList.contains('dark'))
const FIXED_REPO = 'PiggyAndrew/agentic_rag'
const updateStore = useUpdateStore()

// Navigation items configuration
const navItems = computed(() => [
  { path: '/', label: '聊天', icon: ChatLineSquare },
  { path: '/kb', label: '知识库', icon: FolderOpened },
  { path: '/settings', label: '配置', icon: Setting },
  { path: '/about', label: '关于', icon: User },
])

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
                updateStore.hide()
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
  console.log(path);
  
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
  <div class="h-screen w-screen font-sans flex flex-col">
    <header class="h-16 border-b border-gray-200 dark:border-gray-800 px-6 flex items-center justify-between bg-white/80 dark:bg-gray-900/80 backdrop-blur-md sticky top-0 z-50 shadow-sm">
      <!-- Logo Area -->
      <div
        class="flex items-center gap-3 cursor-pointer transition-transform hover:scale-[1.02]"
        @click="navigateTo('/')"
      >
        <span class="text-xl font-bold bg-gradient-to-r from-blue-600 to-cyan-500 bg-clip-text text-transparent">
          Agentic RAG
        </span>
      </div>

      <!-- Right Actions -->
      <div class="flex items-center gap-3">
        <!-- Navigation Menu -->
        <nav class="flex items-center gap-1">
          <button
            v-for="item in navItems"
            :key="item.path"
            :class="[
              'flex items-center gap-2 px-4 h-10 rounded-lg font-medium text-sm transition-all',
              activePath === item.path
                ? 'bg-blue-500/10 dark:bg-blue-400/10 text-blue-600 dark:text-blue-400'
                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-200'
            ]"
            @click="navigateTo(item.path)"
          >
            <el-icon :size="18">
              <ChatLineSquare v-if="item.path === '/'" />
              <FolderOpened v-else-if="item.path === '/kb'" />
              <Setting v-else-if="item.path === '/settings'" />
              <User v-else-if="item.path === '/about'" />
            </el-icon>
            <span>{{ item.label }}</span>
          </button>
        </nav>

        <div class="h-5 w-px bg-gray-200 dark:bg-gray-700 mx-1" />

        <!-- Update Button -->
        <button
          class="flex items-center gap-2 px-4 h-9 rounded-lg font-medium text-sm text-blue-600 dark:text-blue-400 bg-blue-500/10 dark:bg-blue-400/10 hover:bg-blue-500/20 dark:hover:bg-blue-400/20 transition-all"
          @click="checkAndInstallUpdate"
        >
          <el-icon :size="16"><Download /></el-icon>
          <span class="hidden sm:inline">更新</span>
        </button>

        <!-- Theme Switch -->
        <button
          :class="[
            'w-9 h-9 rounded-lg flex items-center justify-center transition-all',
            'focus:outline-none focus:ring-2 focus:ring-blue-500/50',
            isDark ? 'bg-blue-500/20 dark:bg-blue-400/20 text-blue-600 dark:text-blue-400' : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400'
          ]"
          @click="isDark = !isDark"
          :title="isDark ? '切换到亮色模式' : '切换到暗色模式'"
        >
          <el-icon :size="18">
            <Moon v-if="isDark" />
            <Sunny v-else />
          </el-icon>
        </button>
      </div>
    </header>

    <main class="flex-1 overflow-hidden relative bg-gray-50 dark:bg-gray-900">
      <RouterView v-slot="{ Component }">
          <KeepAlive>
            <component :is="Component" />
          </KeepAlive>
      </RouterView>
    </main>
  </div>
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

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--duration-fast) var(--ease-out);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
