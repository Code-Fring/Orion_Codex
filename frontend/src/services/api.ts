import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios'
import type { APIError } from '../types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

class APIClient {
  private client: AxiosInstance
  private accessToken: string | null = null
  private refreshToken: string | null = null

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000,
    })

    this.setupInterceptors()
    this.loadTokensFromStorage()
  }

  private loadTokensFromStorage() {
    this.accessToken = localStorage.getItem('access_token')
    this.refreshToken = localStorage.getItem('refresh_token')
  }

  private saveTokensToStorage() {
    if (this.accessToken) {
      localStorage.setItem('access_token', this.accessToken)
    } else {
      localStorage.removeItem('access_token')
    }
    if (this.refreshToken) {
      localStorage.setItem('refresh_token', this.refreshToken)
    } else {
      localStorage.removeItem('refresh_token')
    }
  }

  private setupInterceptors() {
    // Request interceptor to add auth header
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        if (this.accessToken) {
          config.headers.Authorization = `Bearer ${this.accessToken}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    // Response interceptor for token refresh
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError<APIError>) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

        if (error.response?.status === 401 && !originalRequest._retry && this.refreshToken) {
          originalRequest._retry = true

          try {
            await this.refreshAccessToken()
            originalRequest.headers.Authorization = `Bearer ${this.accessToken}`
            return this.client(originalRequest)
          } catch {
            this.clearTokens()
            window.location.href = '/login'
          }
        }

        return Promise.reject(error)
      }
    )
  }

  private async refreshAccessToken() {
    const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
      refresh_token: this.refreshToken,
    })
    this.accessToken = response.data.access_token
    this.refreshToken = response.data.refresh_token
    this.saveTokensToStorage()
  }

  setTokens(accessToken: string, refreshToken: string) {
    this.accessToken = accessToken
    this.refreshToken = refreshToken
    this.saveTokensToStorage()
  }

  clearTokens() {
    this.accessToken = null
    this.refreshToken = null
    this.saveTokensToStorage()
  }

  getAccessToken() {
    return this.accessToken
  }

  // Auth endpoints
  async login(email: string, password: string) {
    const response = await this.client.post('/auth/login', { email, password })
    return response.data
  }

  async register(email: string, password: string, name: string) {
    const response = await this.client.post('/auth/register', { email, password, name })
    return response.data
  }

  async getCurrentUser() {
    const response = await this.client.get('/auth/me')
    return response.data
  }

  async logout() {
    await this.client.post('/auth/logout')
  }

  // Project endpoints
  async listProjects(params?: { skip?: number; limit?: number; status?: string }) {
    const response = await this.client.get('/projects', { params })
    return response.data
  }

  async getProject(projectId: string) {
    const response = await this.client.get(`/projects/${projectId}`)
    return response.data
  }

  async createProject(data: { name: string; description?: string; prompt: string; tech_stack_preferences?: Record<string, any> }) {
    const response = await this.client.post('/projects', data)
    return response.data
  }

  async updateProject(projectId: string, data: { name?: string; description?: string; status?: string }) {
    const response = await this.client.patch(`/projects/${projectId}`, data)
    return response.data
  }

  async deleteProject(projectId: string) {
    await this.client.delete(`/projects/${projectId}`)
  }

  async regenerateProject(projectId: string) {
    const response = await this.client.post(`/projects/${projectId}/regenerate`)
    return response.data
  }

  // File endpoints
  async listProjectFiles(projectId: string) {
    const response = await this.client.get(`/projects/${projectId}/files`)
    return response.data
  }

  async getFileContent(projectId: string, path: string) {
    const response = await this.client.get(`/projects/${projectId}/files/content`, { params: { path } })
    return response.data
  }

  async saveFileContent(projectId: string, path: string, content: string) {
    const response = await this.client.put(`/projects/${projectId}/files`, { path, content })
    return response.data
  }

  // Task endpoints
  async listProjectTasks(projectId: string, status?: string) {
    const response = await this.client.get(`/tasks/project/${projectId}`, { params: { status } })
    return response.data
  }

  async getTask(taskId: string) {
    const response = await this.client.get(`/tasks/${taskId}`)
    return response.data
  }

  async getProjectLogs(projectId: string, params?: { level?: string; limit?: number }) {
    const response = await this.client.get(`/tasks/project/${projectId}/logs`, { params })
    return response.data
  }

  async retryTask(taskId: string) {
    const response = await this.client.post(`/tasks/${taskId}/retry`)
    return response.data
  }

  async getQueueStats() {
    const response = await this.client.get('/tasks/queue/stats')
    return response.data
  }

  // Provider endpoints
  async listProviders() {
    const response = await this.client.get('/providers')
    return response.data
  }

  async getProvider(providerId: string) {
    const response = await this.client.get(`/providers/${providerId}`)
    return response.data
  }

  async createProvider(data: { name: string; type: string; config: Record<string, any> }) {
    // Backend expects 'provider' field, not 'type'
    const { type, ...rest } = data
    const response = await this.client.post('/providers', { ...rest, provider: type })
    return response.data
  }

  async updateProvider(providerId: string, data: { name?: string; config?: Record<string, any>; is_active?: boolean }) {
    const response = await this.client.patch(`/providers/${providerId}`, data)
    return response.data
  }

  async deleteProvider(providerId: string) {
    await this.client.delete(`/providers/${providerId}`)
  }

  async testProvider(providerId: string) {
    const response = await this.client.post(`/providers/${providerId}/test`)
    return response.data
  }

  // Provider status endpoints
  async getAllProviderStatuses() {
    const response = await this.client.get('/providers/status/all')
    return response.data
  }

  async getSupportedProviders() {
    const response = await this.client.get('/providers/supported/list')
    return response.data
  }

  // API Key endpoints
  async listApiKeys() {
    const response = await this.client.get('/providers/keys/')
    return response.data
  }

  async createApiKey(data: { provider: string; name: string; api_key: string }) {
    const response = await this.client.post('/providers/keys/', data)
    return response.data
  }

  async deleteApiKey(keyId: string) {
    await this.client.delete(`/providers/keys/${keyId}`)
  }

  // WebSocket endpoints
  getWebSocketUrl(projectId: string): string {
    const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/api/v1'
    const token = this.getAccessToken()
    return `${wsUrl}/ws/project/${projectId}?token=${token}`
  }

  async getWebSocketStats() {
    const response = await this.client.get('/ws/stats')
    return response.data
  }
}

export const api = new APIClient()