<script setup lang="ts">
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthorStore } from '@/stores/author'
import { Link, EditPen } from '@element-plus/icons-vue'

const store = useAuthorStore()
const name = computed(() => store.name)
const github = computed(() => store.github)
const email = computed(() => store.email)
const wechat = computed(() => store.wechat)
const REPO_URL = 'https://github.com/PiggyAndrew/agentic_rag'

/**
 * 打开外部链接：用于跳转 GitHub 主页
 */
function openLink(url: string): void {
  window.open(url, '_blank')
}

/**
 * 复制文本到剪贴板：用于复制邮箱与微信号
 */
async function copyText(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板')
  } catch {
    const input = document.createElement('input')
    input.value = text
    document.body.appendChild(input)
    input.select()
    document.execCommand('copy')
    document.body.removeChild(input)
    ElMessage.success('已复制到剪贴板')
  }
}
</script>

<template>
  <el-container class="h-full w-full bg-background">
    <el-main class="p-6">
      <el-card class="max-w-2xl mx-auto">
        <div class="flex items-center justify-between mb-4">
          <div class="flex items-center gap-3">
            <el-avatar size="large">A</el-avatar>
            <div>
              <div class="text-base font-semibold">{{ name }}</div>
              <div class="text-xs text-muted-foreground">Full Stack Engineer</div>
            </div>
          </div>
          <el-button type="primary" plain @click="openLink(github)">访问 GitHub</el-button>
        </div>

        <el-descriptions title="作者信息" :column="1" border>
          <el-descriptions-item label="姓名">
            <span class="text-foreground">{{ name }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="GitHub">
            <el-link :href="github" target="_blank">{{ github }}</el-link>
          </el-descriptions-item>
          <el-descriptions-item label="邮箱">
            <div class="flex items-center gap-2">
              <span class="text-foreground">{{ email }}</span>
              <el-button size="small" @click="copyText(email)">复制</el-button>
            </div>
          </el-descriptions-item>
          <el-descriptions-item label="微信">
            <div class="flex items-center gap-2">
              <span class="text-foreground">{{ wechat }}</span>
              <el-button size="small" @click="copyText(wechat)">复制</el-button>
            </div>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-divider class="max-w-2xl mx-auto mt-4">反馈与建议</el-divider>
      <el-card class="max-w-2xl mx-auto" shadow="never">
        <div class="flex items-center gap-3">
          <el-icon><Link /></el-icon>
          <div class="text-sm text-muted-foreground">如果你有问题或建议，欢迎：</div>
        </div>
        <div class="flex items-center justify-between mt-3">
          <el-link :href="REPO_URL" target="_blank">{{ REPO_URL }}</el-link>
          <el-button size="small" type="primary" plain :icon="EditPen" @click="openLink(REPO_URL + '/issues')">提交 Issue</el-button>
        </div>
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
.mt-4 { margin-top: 1rem; }
.mt-2 { margin-top: 0.5rem; }
.mb-4 { margin-bottom: 1rem; }
.text-base { font-size: 1rem; }
.font-semibold { font-weight: 600; }
.text-xs { font-size: 0.75rem; }
.text-muted-foreground { color: var(--el-text-color-secondary); }
.text-foreground { color: var(--el-text-color-primary); }
.flex { display: flex; }
.items-center { align-items: center; }
.justify-between { justify-content: space-between; }
.gap-2 { gap: 0.5rem; }
.gap-3 { gap: 0.75rem; }
</style>
