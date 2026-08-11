import { createContext, useContext, useState, useCallback, ReactNode } from 'react'
import { api } from '../services/api'
import type { Project, Task, GenerationLog } from '../types'

interface ProjectContextType {
  projects: Project[]
  currentProject: Project | null
  tasks: Task[]
  logs: GenerationLog[]
  isLoading: boolean
  error: string | null
  fetchProjects: () => Promise<void>
  fetchProject: (projectId: string) => Promise<void>
  createProject: (data: { name: string; description?: string; prompt: string; tech_stack_preferences?: Record<string, any> }) => Promise<Project>
  updateProject: (projectId: string, data: { name?: string; description?: string; status?: string }) => Promise<void>
  deleteProject: (projectId: string) => Promise<void>
  regenerateProject: (projectId: string) => Promise<void>
  fetchProjectTasks: (projectId: string) => Promise<void>
  fetchProjectLogs: (projectId: string) => Promise<void>
  clearCurrentProject: () => void
  clearError: () => void
}

const ProjectContext = createContext<ProjectContextType | undefined>(undefined)

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [projects, setProjects] = useState<Project[]>([])
  const [currentProject, setCurrentProject] = useState<Project | null>(null)
  const [tasks, setTasks] = useState<Task[]>([])
  const [logs, setLogs] = useState<GenerationLog[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const clearError = useCallback(() => setError(null), [])

  const fetchProjects = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await api.listProjects()
      setProjects(data.projects || data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch projects')
    } finally {
      setIsLoading(false)
    }
  }, [])

  const fetchProject = useCallback(async (projectId: string) => {
    setIsLoading(true)
    setError(null)
    try {
      const project = await api.getProject(projectId)
      setCurrentProject(project)
      return project
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch project')
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  const createProject = useCallback(async (data: { name: string; description?: string; prompt: string; tech_stack_preferences?: Record<string, any> }) => {
    setIsLoading(true)
    setError(null)
    try {
      const project = await api.createProject(data)
      setProjects(prev => [project, ...prev])
      return project
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create project')
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  const updateProject = useCallback(async (projectId: string, data: { name?: string; description?: string; status?: string }) => {
    setError(null)
    try {
      const project = await api.updateProject(projectId, data)
      setProjects(prev => prev.map(p => p.id === projectId ? project : p))
      if (currentProject?.id === projectId) {
        setCurrentProject(project)
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update project')
      throw err
    }
  }, [currentProject])

  const deleteProject = useCallback(async (projectId: string) => {
    setError(null)
    try {
      await api.deleteProject(projectId)
      setProjects(prev => prev.filter(p => p.id !== projectId))
      if (currentProject?.id === projectId) {
        setCurrentProject(null)
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete project')
      throw err
    }
  }, [currentProject])

  const regenerateProject = useCallback(async (projectId: string) => {
    setError(null)
    try {
      const project = await api.regenerateProject(projectId)
      setProjects(prev => prev.map(p => p.id === projectId ? project : p))
      if (currentProject?.id === projectId) {
        setCurrentProject(project)
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to regenerate project')
      throw err
    }
  }, [currentProject])

  const fetchProjectTasks = useCallback(async (projectId: string) => {
    setError(null)
    try {
      const data = await api.listProjectTasks(projectId)
      setTasks(data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch tasks')
    }
  }, [])

  const fetchProjectLogs = useCallback(async (projectId: string) => {
    setError(null)
    try {
      const data = await api.getProjectLogs(projectId)
      setLogs(data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch logs')
    }
  }, [])

  const clearCurrentProject = useCallback(() => {
    setCurrentProject(null)
    setTasks([])
    setLogs([])
  }, [])

  return (
    <ProjectContext.Provider
      value={{
        projects,
        currentProject,
        tasks,
        logs,
        isLoading,
        error,
        fetchProjects,
        fetchProject,
        createProject,
        updateProject,
        deleteProject,
        regenerateProject,
        fetchProjectTasks,
        fetchProjectLogs,
        clearCurrentProject,
        clearError,
      }}
    >
      {children}
    </ProjectContext.Provider>
  )
}

export function useProject() {
  const context = useContext(ProjectContext)
  if (!context) {
    throw new Error('useProject must be used within a ProjectProvider')
  }
  return context
}