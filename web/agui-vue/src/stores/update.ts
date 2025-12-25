import { defineStore } from 'pinia'

export interface UpdateState {
  visible: boolean
  status: 'idle' | 'checking' | 'downloading' | 'ready' | 'installing' | 'error'
  percent: number
  message: string
  path?: string
}

/**
 * 更新状态管理：控制悬浮窗显示与下载进度、结果
 */
export const useUpdateStore = defineStore('update', {
  state: (): UpdateState => ({
    visible: false,
    status: 'idle',
    percent: 0,
    message: '',
    path: undefined,
  }),
  actions: {
    /**
     * 显示并设置为检查更新状态
     */
    showChecking(message?: string): void {
      this.visible = true
      this.status = 'checking'
      this.message = message || '正在检查更新'
      this.percent = 0
      this.path = undefined
    },
    /**
     * 更新下载进度
     */
    setProgress(percent: number, message?: string): void {
      this.status = 'downloading'
      this.percent = Math.max(0, Math.min(100, Math.floor(percent)))
      if (message) this.message = message
    },
    /**
     * 设置就绪状态（下载完成）
     */
    setReady(path: string, message?: string): void {
      this.status = 'ready'
      this.percent = 100
      this.path = path
      this.message = message || '更新包已下载'
      this.visible = true
    },
    /**
     * 设置安装中状态
     */
    setInstalling(message?: string): void {
      this.status = 'installing'
      this.message = message || '正在启动安装程序'
    },
    /**
     * 设置错误状态
     */
    setError(message: string): void {
      this.status = 'error'
      this.message = message
      this.visible = true
    },
    /**
     * 隐藏悬浮窗
     */
    hide(): void {
      this.visible = false
      this.status = 'idle'
      this.percent = 0
      this.message = ''
      this.path = undefined
    },
  }
})

