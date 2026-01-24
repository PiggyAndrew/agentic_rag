<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
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
  <el-container class="h-screen w-screen font-sans bg-gray-50 dark:bg-gray-900 transition-colors duration-300">
    <el-header height="64px" class="border-b border-gray-200 dark:border-gray-800 px-6 flex items-center justify-between bg-white/80 dark:bg-gray-900/80 backdrop-blur-md sticky top-0 z-50 shadow-sm">
      <!-- Logo Area -->
      <div class="text-xl font-bold font-heading flex items-center gap-2 cursor-pointer transition-transform hover:scale-105" @click="navigateTo('/')">
        <div class="p-1.5 bg-blue-500/10 rounded-lg">
          <el-icon class="text-2xl text-blue-600 dark:text-blue-400"><ChatLineSquare /></el-icon>
        </div>
        <span class="bg-gradient-to-r from-blue-600 to-cyan-500 bg-clip-text text-transparent">Agentic RAG</span>
      </div>

      <!-- Right Actions -->
      <div class="flex items-center gap-4">
        <!-- Navigation Menu -->
        <el-menu
          mode="horizontal"
          :default-active="activePath"
          @select="navigateTo"
          :ellipsis="false"
          class="!border-0 !bg-transparent min-w-[300px]"
          :active-text-color="isDark ? '#60a5fa' : '#2563eb'"
          :text-color="isDark ? '#9ca3af' : '#4b5563'"
        >
          <el-menu-item index="/" class="!rounded-lg hover:!bg-blue-50 dark:hover:!bg-blue-900/20 mx-1 !h-10 my-auto flex items-center">
            <template #title>
              <div class="flex items-center gap-2">
                <el-icon><ChatLineSquare /></el-icon>
                <span class="font-medium">聊天</span>
              </div>
            </template>
          </el-menu-item>
          <el-menu-item index="/kb" class="!rounded-lg hover:!bg-blue-50 dark:hover:!bg-blue-900/20 mx-1 !h-10 my-auto flex items-center">
            <template #title>
              <div class="flex items-center gap-2">
                <el-icon><FolderOpened /></el-icon>
                <span class="font-medium">知识库</span>
              </div>
            </template>
          </el-menu-item>
          <el-menu-item index="/settings" class="!rounded-lg hover:!bg-blue-50 dark:hover:!bg-blue-900/20 mx-1 !h-10 my-auto flex items-center">
            <template #title>
              <div class="flex items-center gap-2">
                <el-icon><Setting /></el-icon>
                <span class="font-medium">配置</span>
              </div>
            </template>
          </el-menu-item>
          <el-menu-item index="/about" class="!rounded-lg hover:!bg-blue-50 dark:hover:!bg-blue-900/20 mx-1 !h-10 my-auto flex items-center">
             <template #title>
              <div class="flex items-center gap-2">
                <el-icon><User /></el-icon>
                <span class="font-medium">关于</span>
              </div>
            </template>
          </el-menu-item>
        </el-menu>

        <div class="h-6 w-px bg-gray-200 dark:bg-gray-700 mx-2"></div>

        <!-- Update Button -->
        <el-button 
          size="default" 
          type="primary" 
          plain 
          round
          @click="checkAndInstallUpdate"
          class="!px-4 hover:!scale-105 transition-transform"
        >
          <el-icon class="mr-1.5"><Download /></el-icon>
          更新
        </el-button>

        <!-- Theme Switch -->
        <el-switch
          v-model="isDark"
          inline-prompt
          :active-icon="Moon"
          :inactive-icon="Sunny"
          style="--el-switch-on-color: #374151; --el-switch-off-color: #e5e7eb; --el-switch-border-color: #d1d5db"
          class="ml-2"
        />
      </div>
    </el-header>

    <el-main class="p-0 bg-gray-50 dark:bg-gray-900 text-foreground overflow-hidden relative">
      <RouterView v-slot="{ Component }">
        <Transition name="fade" mode="out-in">
          <KeepAlive>
            <component :is="Component" />
          </KeepAlive>
        </Transition>
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

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Custom Menu Styles to override Element Plus defaults if needed */
.el-menu--horizontal .el-menu-item:not(.is-disabled):focus, 
.el-menu--horizontal .el-menu-item:not(.is-disabled):hover {
  background-color: transparent;
}
</style>
