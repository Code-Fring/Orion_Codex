export interface User {
  id: string
  email: string
  name: string
  avatar_url?: string
  created_at: string
  updated_at: string
}

export interface Project {
  id: string
  name: string
  description?: string
  prompt: string
  status: ProjectStatus
  tech_stack: Record<string, any>
  architecture?: Record<string, any>
  generated_path?: string
  error_message?: string
  progress: number
  created_at: string
  updated_at: string
  completed_at?: string
}

export type ProjectStatus = 
  | 'pending'
  | 'planning'
  | 'building'
  | 'testing'
  | 'review'
  | 'deployment'
  | 'completed'
  | 'failed'

export interface Task {
  id: string
  project_id: string
  name: string
  description?: string
  status: TaskStatus
  step_order: number
  agent_type?: string
  input_data: Record<string, any>
  output_data?: Record<string, any>
  error_message?: string
  started_at?: string
  completed_at?: string
  created_at: string
  updated_at: string
}

export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface GenerationLog {
  id: string
  project_id: string
  level: string
  message: string
  context?: Record<string, any>
  created_at: string
}

export interface Provider {
  id: string
  name: string
  type: string
  config: Record<string, any>
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface APIError {
  detail: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}