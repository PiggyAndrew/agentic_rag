import { defineStore } from 'pinia'

export interface KnowledgeBase {
  id: string
  name: string
  description?: string
  createdAt: number
}

export interface KBFile {
  id: string
  kbId: string
  name: string
  type: string
  createdAt: number
  chunkCount: number
  status: string
}

function getApiBase(): string {
  const base = (import.meta as any).env?.VITE_API_BASE || (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000'
  return base.replace(/\/$/, '')
}

export const useKbStore = defineStore('kb', {
  state: () => ({
    knowledgeBases: [] as KnowledgeBase[],
    selectedKbId: '' as string,
    filesByKb: {} as Record<string, KBFile[]>,
    loading: false as boolean,
  }),
  persist: true,
  actions: {
    /**
     * 拉取知识库列表
     */
    async fetchKnowledgeBases(): Promise<void> {
      this.loading = true
      try {
        const res = await fetch(`${getApiBase()}/api/kb`)
        const data = await res.json()
        this.knowledgeBases = data
        if (!this.selectedKbId && this.knowledgeBases.length > 0) {
          const first = this.knowledgeBases[0]
          if (first) this.selectedKbId = first.id
        }
      } finally {
        this.loading = false
      }
    },

    /**
     * 创建知识库
     */
    async createKnowledgeBase(name: string, description?: string): Promise<KnowledgeBase> {
      const res = await fetch(`${getApiBase()}/api/kb`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description }),
      })
      const kb = await res.json()
      this.knowledgeBases = [kb, ...this.knowledgeBases]
      if (!this.selectedKbId) this.selectedKbId = kb.id
      return kb
    },

    /**
     * 更新知识库名称或描述
     */
    async updateKnowledgeBase(kbId: string, name?: string, description?: string): Promise<KnowledgeBase> {
      const res = await fetch(`${getApiBase()}/api/kb/${kbId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description }),
      })
      const kb = await res.json()
      const idx = this.knowledgeBases.findIndex(k => k.id === kbId)
      if (idx >= 0) this.knowledgeBases[idx] = kb
      return kb
    },

    /**
     * 删除知识库
     */
    async deleteKnowledgeBase(kbId: string): Promise<void> {
      await fetch(`${getApiBase()}/api/kb/${kbId}`, { method: 'DELETE' })
      this.knowledgeBases = this.knowledgeBases.filter(k => k.id !== kbId)
      delete this.filesByKb[kbId]
      if (this.selectedKbId === kbId) {
        this.selectedKbId = this.knowledgeBases[0]?.id || ''
      }
    },

    /**
     * 拉取知识库文件列表
     */
    async fetchFiles(kbId: string): Promise<void> {
      const res = await fetch(`${getApiBase()}/api/kb/${kbId}/files`)
      const data = await res.json()
      this.filesByKb[kbId] = data
    },

    /**
     * 上传原始文件到后端 uploads 目录（仅保存原件，不向量化）
     */
    async uploadFile(kbId: string, file: File): Promise<KBFile> {
      const contentBase64 = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = () => {
          const dataUrl = String(reader.result || '')
          const idx = dataUrl.indexOf(',')
          resolve(idx >= 0 ? dataUrl.slice(idx + 1) : '')
        }
        reader.onerror = reject
        reader.readAsDataURL(file)
      })
      const res = await fetch(`${getApiBase()}/api/kb/${kbId}/files`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: file.name,
          type: file.type || 'application/octet-stream',
          contentBase64,
        }),
      })
      const item: KBFile = await res.json()
      const list = this.filesByKb[kbId] || []
      this.filesByKb[kbId] = [item, ...list]
      return item
    },

    /**
     * 查看文件片段
     */
    async fetchChunks(kbId: string, fileId: string): Promise<any[]> {
      const res = await fetch(`${getApiBase()}/api/kb/${kbId}/files/${fileId}/chunks`)
      const data = await res.json()
      return data
    },

    /**
     * 向量化指定文件名
     */
    async vectorizeFile(kbId: string, filename: string): Promise<KBFile> {
      const res = await fetch(`${getApiBase()}/api/kb/${kbId}/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename }),
      })
      const item: KBFile = await res.json()
      const list = this.filesByKb[kbId] || []
      const idx = list.findIndex(f => f.id === item.id)
      if (idx >= 0) {
        list[idx] = item
        this.filesByKb[kbId] = [...list]
      } else {
        this.filesByKb[kbId] = [item, ...list]
      }
      return item
    },

    /**
     * 删除文件
     */
    async deleteFile(fileId: string, kbId: string): Promise<void> {
      await fetch(`${getApiBase()}/api/files/${fileId}`, { method: 'DELETE' })
      const list = this.filesByKb[kbId] || []
      this.filesByKb[kbId] = list.filter(f => f.id !== fileId)
    },
  },
})
