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
      <div class="max-w-2xl mx-auto space-y-4">
        <!-- Author Card -->
        <div class="bg-card rounded-xl border border-border shadow-sm overflow-hidden">
          <div class="flex items-center justify-between p-6 border-b border-border">
            <div class="flex items-center gap-4">
              <div class="w-12 h-12 rounded-full bg-primary/10 text-primary flex items-center justify-center text-lg font-semibold">
                A
              </div>
              <div>
                <div class="text-base font-semibold text-foreground">{{ name }}</div>
                <div class="text-xs text-muted-foreground">Full Stack Engineer</div>
              </div>
            </div>
            <button
              class="px-4 py-2 text-sm font-medium text-primary bg-primary/10 rounded-lg transition-all duration-normal ease-out hover:bg-primary/20"
              @click="openLink(github)"
            >
              访问 GitHub
            </button>
          </div>

          <!-- Author Info -->
          <div class="p-6 space-y-4">
            <div class="flex items-center justify-between py-3 border-b border-border">
              <span class="text-sm text-muted-foreground w-20">姓名</span>
              <span class="text-sm text-foreground font-medium">{{ name }}</span>
            </div>
            <div class="flex items-center justify-between py-3 border-b border-border">
              <span class="text-sm text-muted-foreground w-20">GitHub</span>
              <el-link :href="github" target="_blank" class="text-sm">{{ github }}</el-link>
            </div>
            <div class="flex items-center justify-between py-3 border-b border-border">
              <span class="text-sm text-muted-foreground w-20">邮箱</span>
              <div class="flex items-center gap-2">
                <span class="text-sm text-foreground">{{ email }}</span>
                <button
                  class="px-2 py-1 text-xs font-medium text-foreground bg-muted rounded-lg hover:bg-muted/80 transition-colors"
                  @click="copyText(email)"
                >
                  复制
                </button>
              </div>
            </div>
            <div class="flex items-center justify-between py-3">
              <span class="text-sm text-muted-foreground w-20">微信</span>
              <div class="flex items-center gap-2">
                <span class="text-sm text-foreground">{{ wechat }}</span>
                <button
                  class="px-2 py-1 text-xs font-medium text-foreground bg-muted rounded-lg hover:bg-muted/80 transition-colors"
                  @click="copyText(wechat)"
                >
                  复制
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Divider -->
        <div class="flex items-center gap-4 my-6">
          <div class="flex-1 h-px bg-border"></div>
          <span class="text-sm font-medium text-muted-foreground">反馈与建议</span>
          <div class="flex-1 h-px bg-border"></div>
        </div>

        <!-- Feedback Card -->
        <div class="bg-card rounded-xl border border-border shadow-sm p-6">
          <div class="flex items-center gap-3 mb-4">
            <div class="w-10 h-10 rounded-lg bg-muted flex items-center justify-center text-muted-foreground">
              <el-icon><Link /></el-icon>
            </div>
            <div class="text-sm text-muted-foreground">如果你有问题或建议，欢迎：</div>
          </div>
          <div class="flex items-center justify-between">
            <el-link :href="REPO_URL" target="_blank" class="text-sm font-medium">{{ REPO_URL }}</el-link>
            <button
              class="flex items-center gap-2 px-4 py-2 text-sm font-medium text-primary bg-primary/10 rounded-lg transition-all duration-normal ease-out hover:bg-primary/20"
              @click="openLink(REPO_URL + '/issues')"
            >
              <el-icon><EditPen /></el-icon>
              提交 Issue
            </button>
          </div>
        </div>
      </div>
    </el-main>
  </el-container>
</template>

<style scoped>
/* Remove scoped styles - use Tailwind classes instead */
</style>
