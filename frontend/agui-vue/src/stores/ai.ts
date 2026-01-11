import { defineStore } from 'pinia'

export type AiConfigState = {
  apiBaseUrl: string
  llmApiKey: string
  llmBaseUrl: string
  llmModel: string
  embeddingApiKey: string
  embeddingBaseUrl: string
  embeddingModel: string
  rerankerApiKey: string
  rerankerBaseUrl: string
  rerankerModel: string
}

function defaultApiBaseUrl(): string {
  const raw = (import.meta as any).env?.VITE_API_BASE || (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000'
  const s = String(raw || '').trim()
  if (!s) return 'http://localhost:8000'
  if (s.endsWith('/api/chat')) return s.slice(0, -'/api/chat'.length)
  return s.replace(/\/+$/, '')
}

export const useAiStore = defineStore('ai', {
  state: (): AiConfigState => ({
    apiBaseUrl: defaultApiBaseUrl(),
    llmApiKey: '',
    llmBaseUrl: '',
    llmModel: '',
    embeddingApiKey: '',
    embeddingBaseUrl: '',
    embeddingModel: '',
    rerankerApiKey: '',
    rerankerBaseUrl: '',
    rerankerModel: '',
  }),
  persist: true,
  getters: {
    chatApiUrl(state): string {
      const base = (state.apiBaseUrl || '').trim().replace(/\/+$/, '')
      return base ? `${base}/api/chat` : 'http://localhost:8000/api/chat'
    },
  },
})
