/**
 * LLM配置管理API调用
 */

type ApiError = { code: number; message: string }
type ApiResponse<T = any> = { ok: boolean; data?: T; error?: ApiError | null }

import { getApiBase } from './api_base'

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${getApiBase()}${path}`, init)
  const body: ApiResponse<T> = await res.json().catch(() => ({ ok: false, error: { code: 500, message: '响应解析失败' } } as any))
  if (!body.ok) {
    const msg = body.error?.message || '请求失败'
    throw new Error(msg)
  }
  return body.data as T
}

// ============ LLM配置预设 ============

export interface LLMProviderType {
  value: string
  label: string
  description: string
  baseUrl: string
  defaultModel: string
  requiredParams: string[]
}

export interface LLMPreset {
  name: string
  providerType: string
  baseUrl: string
  defaultModel: string
  description: string
  requiredParams: string[]
  supportedCategories?: string[]
}

/**
 * 获取LLM配置预设列表
 */
export async function getLLMPresets(): Promise<LLMPreset[]> {
  return await apiRequest<LLMPreset[]>('/api/llm/presets')
}

// ============ LLM提供者配置 ============

export interface LLMProvider {
  id: number
  name: string
  category?: string
  providerType: string
  baseUrl: string | null
  apiKey: string | null
  modelName: string | null
  config: Record<string, any> | null
  isDefault: boolean
  isEnabled: boolean
  description: string | null
  createdAt: number
  updatedAt: number
}

export interface LLMProviderCreate {
  name: string
  category: string
  providerType: string
  baseUrl?: string
  apiKey?: string
  modelName?: string
  config?: Record<string, any>
  isDefault?: boolean
  description?: string
}

export interface LLMProviderUpdate {
  name?: string
  category?: string
  baseUrl?: string
  apiKey?: string
  modelName?: string
  config?: Record<string, any>
  isDefault?: boolean
  isEnabled?: boolean
  description?: string
}

/**
 * 获取LLM提供者配置列表
 */
export async function getLLMProviders(params?: {
  providerType?: string
  enabledOnly?: boolean
}): Promise<LLMProvider[]> {
  const query = new URLSearchParams()
  if (params?.providerType) query.set('provider_type', params.providerType)
  if (params?.enabledOnly !== undefined) query.set('enabled_only', String(params.enabledOnly))
  const queryString = query.toString()
  const path = `/api/llm/providers${queryString ? `?${queryString}` : ''}`
  return await apiRequest<LLMProvider[]>(path)
}

/**
 * 获取单个LLM提供者配置
 */
export async function getLLMProvider(id: number): Promise<LLMProvider> {
  return await apiRequest<LLMProvider>(`/api/llm/providers/${id}`)
}

/**
 * 创建LLM提供者配置
 */
export async function createLLMProvider(data: LLMProviderCreate): Promise<{ id: number }> {
  const res = await fetch(`${getApiBase()}/api/llm/providers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  const body: ApiResponse<{ id: number }> = await res.json()
  if (!body.ok) {
    const msg = body.error?.message || '创建失败'
    throw new Error(msg)
  }
  return body.data!
}

/**
 * 更新LLM提供者配置
 */
export async function updateLLMProvider(id: number, data: LLMProviderUpdate): Promise<{ id: number }> {
  const res = await fetch(`${getApiBase()}/api/llm/providers/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  const body: ApiResponse<{ id: number }> = await res.json()
  if (!body.ok) {
    const msg = body.error?.message || '更新失败'
    throw new Error(msg)
  }
  return body.data!
}

/**
 * 删除LLM提供者配置
 */
export async function deleteLLMProvider(id: number): Promise<void> {
  const res = await fetch(`${getApiBase()}/api/llm/providers/${id}`, {
    method: 'DELETE',
  })
  const body: ApiResponse<{ ok: boolean }> = await res.json()
  if (!body.ok) {
    const msg = body.error?.message || '删除失败'
    throw new Error(msg)
  }
}

/**
 * 设置默认LLM配置
 */
export async function setDefaultLLMProvider(id: number): Promise<{ id: number }> {
  const res = await fetch(`${getApiBase()}/api/llm/providers/${id}/set-default`, {
    method: 'POST',
  })
  const body: ApiResponse<{ id: number }> = await res.json()
  if (!body.ok) {
    const msg = body.error?.message || '设置失败'
    throw new Error(msg)
  }
  return body.data!
}

/**
 * 获取指定类型的默认LLM配置
 */
export async function getDefaultLLMProvider(providerType: string): Promise<LLMProvider> {
  return await apiRequest<LLMProvider>(`/api/llm/default/${providerType}`)
}

/**
 * 获取按类别解析的当前激活配置
 */
export async function getActiveLLMConfig(): Promise<{
  llm?: { id: number; baseUrl: string; apiKey: string; model: string; providerType: string }
  embedding?: { id: number; baseUrl: string; apiKey: string; model: string; providerType: string }
  reranker?: { id: number; baseUrl: string; apiKey: string; model: string; providerType: string }
  vll?: { id: number; baseUrl: string; apiKey: string; model: string; providerType: string }
  apiBaseUrl?: string
}> {
  return await apiRequest(`/api/llm/active`)
}

/**
 * 设置按类别的当前激活配置
 */
export async function setActiveLLMConfig(data: { llmId?: number; embeddingId?: number; rerankerId?: number; vllId?: number }): Promise<void> {
  const res = await fetch(`${getApiBase()}/api/llm/active`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  const body: ApiResponse = await res.json()
  if (!body.ok) {
    const msg = body.error?.message || '保存激活配置失败'
    throw new Error(msg)
  }
}

/**
 * 测试LLM连接
 */
export async function testLLMConnection(config: { baseUrl: string; apiKey: string; modelName: string }): Promise<{ message: string; details: any }> {
  const res = await fetch(`${getApiBase()}/api/llm/test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })
  const body: ApiResponse<{ message: string; details: any }> = await res.json()
  if (!body.ok) {
    const msg = body.error?.message || '连接测试失败'
    throw new Error(msg)
  }
  return body.data!
}
