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
  vllApiKey: string
  vllBaseUrl: string
  vllModel: string
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
    vllApiKey: '',
    vllBaseUrl: '',
    vllModel: '',
  }),
  persist: true,
  getters: {
    chatApiUrl(state): string {
      const base = (state.apiBaseUrl || '').trim().replace(/\/+$/, '')
      return base ? `${base}/api/chat` : 'http://localhost:8000/api/chat'
    },
  },
  actions: {
    async load() {
      // Fetch resolved config from backend
      try {
        const base = (this.apiBaseUrl || defaultApiBaseUrl()).trim().replace(/\/+$/, '')
        const res = await fetch(`${base}/api/config/active`)
        const body = await res.json()
        
        if (body.ok && body.data) {
          const data = body.data
          // Update API Base URL if provided
          if (data.apiBaseUrl) this.apiBaseUrl = data.apiBaseUrl

          // Populate LLM
          if (data.llm) {
            this.llmBaseUrl = data.llm.baseUrl || ''
            this.llmApiKey = data.llm.apiKey || ''
            this.llmModel = data.llm.model || ''
          }

          // Populate Embedding
          if (data.embedding) {
            this.embeddingBaseUrl = data.embedding.baseUrl || ''
            this.embeddingApiKey = data.embedding.apiKey || ''
            this.embeddingModel = data.embedding.model || ''
          }

          // Populate Reranker
          if (data.reranker) {
            this.rerankerBaseUrl = data.reranker.baseUrl || ''
            this.rerankerApiKey = data.reranker.apiKey || ''
            this.rerankerModel = data.reranker.model || ''
          }

          // Populate VLL
          if (data.vll) {
            this.vllBaseUrl = data.vll.baseUrl || ''
            this.vllApiKey = data.vll.apiKey || ''
            this.vllModel = data.vll.model || ''
          }
        }
      } catch (e) {
        console.warn('Failed to load active AI config', e)
      }
    }
  }
})
