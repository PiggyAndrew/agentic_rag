import { defineStore } from 'pinia'
import { getApiBase } from '../api/api_base'

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
  return getApiBase()
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
  actions: {
    getChatApiUrl(): string {
      const base = getApiBase().trim().replace(/\/+$/, '')
      return `${base}/api/chat`
    },
    async load() {
      // Fetch resolved config from backend
      try {
        const base = getApiBase().trim().replace(/\/+$/, '')
        if (base) this.apiBaseUrl = base
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
