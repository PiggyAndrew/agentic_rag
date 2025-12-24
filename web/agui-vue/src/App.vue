<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ChatLineSquare, FolderOpened } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const activePath = ref('/')
const isDark = ref<boolean>(document.documentElement.classList.contains('dark'))

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
        <el-switch
          v-model="isDark"
          inline-prompt
          active-text="暗黑"
          inactive-text="白色"
        />
      </div>
    </el-header>
    <el-main class="p-0 bg-background text-foreground">
      <RouterView />
    </el-main>
  </el-container>
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
