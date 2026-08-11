import React, { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useProject } from '../contexts/ProjectContext'
import { useAuth } from '../contexts/AuthContext'
import { useWebSocket } from '../contexts/WebSocketContext'
import { api } from '../services/api'
import {
  ArrowLeft,
  RefreshCw,
  Trash2,
  FolderGit2,
  Code,
  Terminal,
  FileText,
  ChevronDown,
  AlertCircle,
  CheckCircle,
  Clock,
  Loader2,
  XCircle,
  Copy,
  Eye,
  GitBranch,
  Layers,
  Zap,
  Hammer,
  TestTube,
  Ship,
  Wifi,
  WifiOff,
} from 'lucide-react'
import { cn, formatRelativeTime, getStatusColor, formatDate } from '../utils/cn'
import { FileExplorer } from '../components/FileExplorer'
import { toast } from 'react-hot-toast'

export default function ProjectDetail() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const { 
    currentProject, 
    tasks, 
    logs, 
    isLoading, 
    fetchProject, 
    fetchProjectTasks, 
    fetchProjectLogs,
    deleteProject,
    regenerateProject,
    clearCurrentProject,
  } = useProject()
  const { isAuthenticated } = useAuth()
  const { connect, disconnect, isConnected, onTaskUpdate, onLog, onProgress } = useWebSocket()

  const [activeTab, setActiveTab] = useState<'overview' | 'tasks' | 'logs' | 'files'>('overview')
  const [deleting, setDeleting] = useState(false)
  const [regenerating, setRegenerating] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [logFilter, setLogFilter] = useState<string>('all')
  const [expandedTaskId, setExpandedTaskId] = useState<string | null>(null)

  // WebSocket connection
  useEffect(() => {
    if (projectId && isAuthenticated) {
      connect(projectId)
    }
    return () => disconnect()
  }, [projectId, isAuthenticated, connect, disconnect])

  // Subscribe to real-time updates
  useEffect(() => {
    if (!projectId) return

    const unsubTaskUpdate = onTaskUpdate((task) => {
      // Update task in local state
      console.log('Task updated:', task)
      fetchProjectTasks(projectId)
    })

    const unsubLog = onLog((log) => {
      console.log('New log:', log)
      fetchProjectLogs(projectId)
    })

    const unsubProgress = onProgress((progress, status) => {
      console.log('Progress update:', progress, status)
      // The project context will be updated via the task/log updates
    })

    return () => {
      unsubTaskUpdate()
      unsubLog()
      unsubProgress()
    }
  }, [projectId, onTaskUpdate, onLog, onProgress, fetchProjectTasks, fetchProjectLogs])

  useEffect(() => {
    if (projectId && isAuthenticated) {
      clearCurrentProject()
      fetchProject(projectId)
      fetchProjectTasks(projectId)
      fetchProjectLogs(projectId)
    }
  }, [projectId, isAuthenticated, fetchProject, fetchProjectTasks, fetchProjectLogs, clearCurrentProject])

  const handleDelete = async () => {
    if (!projectId) return
    if (!window.confirm('Are you sure you want to delete this project? This cannot be undone.')) return
    setDeleting(true)
    try {
      await deleteProject(projectId)
      navigate('/dashboard')
    } catch (err) {
      console.error('Failed to delete project:', err)
    } finally {
      setDeleting(false)
      setShowDeleteConfirm(false)
    }
  }

  const handleRegenerate = async () => {
    if (!projectId) return
    setRegenerating(true)
    try {
      await regenerateProject(projectId)
      fetchProject(projectId)
      fetchProjectTasks(projectId)
      fetchProjectLogs(projectId)
    } catch (err) {
      console.error('Failed to regenerate project:', err)
    } finally {
      setRegenerating(false)
    }
  }

  const handleViewFiles = () => {
    setActiveTab('files')
  }

  const handleRetryTask = async (taskId: string) => {
    try {
      await api.retryTask(taskId)
      fetchProjectTasks(projectId!)
      toast.success('Task retry initiated')
    } catch (err) {
      console.error('Failed to retry task:', err)
      toast.error('Failed to retry task')
    }
  }

  if (isLoading && !currentProject) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" aria-label="Loading project" />
      </div>
    )
  }

  if (!currentProject && !isLoading) {
    return (
      <div className="text-center py-16">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-slate-800 mb-4">
          <AlertCircle className="w-8 h-8 text-slate-500" aria-hidden="true" />
        </div>
        <h2 className="text-xl font-semibold text-white mb-2">Project not found</h2>
        <p className="text-slate-400 mb-6 max-w-md mx-auto">
          The project you're looking for doesn't exist or you don't have access to it.
        </p>
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5" aria-hidden="true" />
          Back to Dashboard
        </Link>
      </div>
    )
  }

  const project = currentProject!
  const statusColors = getStatusColor(project.status)
  const statusIcons: Record<string, React.ReactNode> = {
    pending: <Clock className="w-4 h-4" />,
    planning: <Layers className="w-4 h-4" />,
    building: <Hammer className="w-4 h-4" />,
    testing: <TestTube className="w-4 h-4" />,
    review: <Eye className="w-4 h-4" />,
    deployment: <Ship className="w-4 h-4" />,
    completed: <CheckCircle className="w-4 h-4" />,
    failed: <XCircle className="w-4 h-4" />,
  }

  const statusLabels: Record<string, string> = {
    pending: 'Pending',
    planning: 'Planning',
    building: 'Building',
    testing: 'Testing',
    review: 'Review',
    deployment: 'Deploying',
    completed: 'Completed',
    failed: 'Failed',
  }

  const filteredLogs = logs.filter(log => 
    logFilter === 'all' || log.level.toLowerCase() === logFilter.toLowerCase()
  )

  const logLevels = ['all', 'info', 'warn', 'error', 'debug']

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(-1)}
            className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
            aria-label="Go back"
          >
            <ArrowLeft className="w-5 h-5" aria-hidden="true" />
          </button>
          <div>
            <h1 className="text-3xl font-bold text-white truncate max-w-2xl">{project.name}</h1>
            <p className="text-slate-400 mt-1">{project.description || 'No description provided'}</p>
          </div>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          {/* WebSocket Connection Status */}
          <span className={cn('px-2 py-1 text-xs font-medium rounded-full flex items-center gap-1.5', 
            isConnected ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
          )}>
            {isConnected ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
            {isConnected ? 'Live' : 'Disconnected'}
          </span>
          <span className={cn('px-3 py-1.5 text-sm font-medium rounded-full border flex items-center gap-2', statusColors)}>
            {statusIcons[project.status] || <Clock className="w-4 h-4" />}
            {statusLabels[project.status] || project.status}
          </span>
          {['pending', 'planning', 'building', 'testing', 'review', 'deployment'].includes(project.status) && (
            <button
              onClick={handleRegenerate}
              disabled={regenerating}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {regenerating ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                  Regenerating...
                </>
              ) : (
                <>
                  <RefreshCw className="w-4 h-4" aria-hidden="true" />
                  Regenerate
                </>
              )}
            </button>
          )}
          <button
            onClick={() => setShowDeleteConfirm(true)}
            disabled={deleting}
            className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white font-medium rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            <Trash2 className="w-4 h-4" aria-hidden="true" />
            Delete
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {project.error_message && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
            <div className="flex-1">
              <h3 className="text-red-400 font-medium mb-1">Generation Failed</h3>
              <p className="text-red-300 text-sm">{project.error_message}</p>
            </div>
            <button
              onClick={handleRegenerate}
              disabled={regenerating}
              className="px-3 py-1.5 bg-red-600 hover:bg-red-500 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              <RefreshCw className="w-3 h-3" aria-hidden="true" />
              Retry
            </button>
          </div>
        </div>
      )}

      {/* Progress Bar for Active Projects */}
      {['pending', 'planning', 'building', 'testing', 'review', 'deployment'].includes(project.status) && (
        <div className="bg-slate-900/50 backdrop-blur-sm border border-slate-800 rounded-xl p-5">
          <div className="flex justify-between text-sm mb-2">
            <span className="text-slate-400">Overall Progress</span>
            <span className="text-white font-medium">{project.progress}%</span>
          </div>
          <div className="h-3 bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 transition-all duration-500 ease-out"
              style={{ width: `${project.progress}%` }}
              role="progressbar"
              aria-valuenow={project.progress}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Project generation progress"
            />
          </div>
          <p className="text-xs text-slate-500 mt-2">
            Current stage: {statusLabels[project.status] || project.status}
          </p>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="flex gap-1 bg-slate-800 rounded-lg p-1 border border-slate-700">
        <button
          onClick={() => setActiveTab('overview')}
          className={cn(
            'flex-1 py-2.5 px-4 rounded-md text-sm font-medium transition-colors flex items-center justify-center gap-2',
            activeTab === 'overview' ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'
          )}
        >
          <FileText className="w-4 h-4" aria-hidden="true" />
          Overview
        </button>
        <button
          onClick={() => setActiveTab('tasks')}
          className={cn(
            'flex-1 py-2.5 px-4 rounded-md text-sm font-medium transition-colors flex items-center justify-center gap-2',
            activeTab === 'tasks' ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'
          )}
        >
          <Layers className="w-4 h-4" aria-hidden="true" />
          Tasks
          {tasks.length > 0 && (
            <span className={cn('px-2 py-0.5 text-xs rounded-full', activeTab === 'tasks' ? 'bg-slate-600 text-white' : 'bg-slate-600 text-slate-300')}>
              {tasks.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab('logs')}
          className={cn(
            'flex-1 py-2.5 px-4 rounded-md text-sm font-medium transition-colors flex items-center justify-center gap-2',
            activeTab === 'logs' ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'
          )}
        >
          <Terminal className="w-4 h-4" aria-hidden="true" />
          Logs
          {logs.length > 0 && (
            <span className={cn('px-2 py-0.5 text-xs rounded-full', activeTab === 'logs' ? 'bg-slate-600 text-white' : 'bg-slate-600 text-slate-300')}>
              {logs.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab('files')}
          className={cn(
            'flex-1 py-2.5 px-4 rounded-md text-sm font-medium transition-colors flex items-center justify-center gap-2',
            activeTab === 'files' ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'
          )}
        >
          <Code className="w-4 h-4" aria-hidden="true" />
          Files
        </button>
      </div>

      {/* Tab Panels */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Project Info Card */}
          <div className="bg-slate-900/50 backdrop-blur-sm border border-slate-800 rounded-xl p-5">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <FileText className="w-5 h-5 text-blue-500" aria-hidden="true" />
              Project Information
            </h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <InfoItem label="Project ID" value={project.id} copyable />
              <InfoItem label="Status" value={statusLabels[project.status] || project.status} />
              <InfoItem label="Progress" value={`${project.progress}%`} />
              <InfoItem label="Created" value={formatDate(project.created_at)} />
              <InfoItem label="Updated" value={formatDate(project.updated_at)} />
              <InfoItem 
                label="Completed" 
                value={project.completed_at ? formatDate(project.completed_at) : '—'} 
              />
            </div>
          </div>

          {/* Tech Stack */}
          {project.tech_stack && Object.keys(project.tech_stack).length > 0 && (
            <div className="bg-slate-900/50 backdrop-blur-sm border border-slate-800 rounded-xl p-5">
              <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Layers className="w-5 h-5 text-blue-500" aria-hidden="true" />
                Technology Stack
              </h2>
              <div className="flex flex-wrap gap-2">
                {Object.entries(project.tech_stack).map(([category, tech]) => (
                  tech && (
                    <span 
                      key={category} 
                      className="px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-300"
                    >
                      <span className="font-medium text-slate-400 capitalize">{category.replace(/([A-Z])/g, ' $1').trim()}: </span>
                      {typeof tech === 'object' ? JSON.stringify(tech) : tech}
                    </span>
                  )
                ))}
              </div>
            </div>
          )}

          {/* Architecture */}
          {project.architecture && Object.keys(project.architecture).length > 0 && (
            <div className="bg-slate-900/50 backdrop-blur-sm border border-slate-800 rounded-xl p-5">
              <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <GitBranch className="w-5 h-5 text-blue-500" aria-hidden="true" />
                Architecture
              </h2>
              <pre className="bg-slate-950 border border-slate-800 rounded-lg p-4 overflow-x-auto text-sm text-slate-300 max-h-96">
                {JSON.stringify(project.architecture, null, 2)}
              </pre>
            </div>
          )}

          {/* Original Prompt */}
          <div className="bg-slate-900/50 backdrop-blur-sm border border-slate-800 rounded-xl p-5">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Zap className="w-5 h-5 text-blue-500" aria-hidden="true" />
              Original Prompt
            </h2>
            <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 text-slate-300 font-mono text-sm whitespace-pre-wrap">
              {project.prompt}
            </div>
          </div>

          {/* Generated Path */}
          {project.generated_path && (
            <div className="bg-slate-900/50 backdrop-blur-sm border border-slate-800 rounded-xl p-5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-3 bg-blue-500/20 rounded-lg">
                    <Code className="w-6 h-6 text-blue-400" aria-hidden="true" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white">Project Generated</h3>
                    <p className="text-slate-400 text-sm truncate max-w-md">{project.generated_path}</p>
                  </div>
                </div>
                <button
                  onClick={handleViewFiles}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg transition-colors flex items-center gap-2"
                >
                  <FolderGit2 className="w-4 h-4" aria-hidden="true" />
                  Browse Files
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'tasks' && (
        <div className="bg-slate-900/50 backdrop-blur-sm border border-slate-800 rounded-xl overflow-hidden">
          {tasks.length === 0 ? (
            <div className="p-12 text-center">
              <Layers className="w-12 h-12 text-slate-500 mx-auto mb-4" aria-hidden="true" />
              <h3 className="text-lg font-semibold text-white mb-2">No tasks yet</h3>
              <p className="text-slate-400">Tasks will appear here once the generation pipeline starts.</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-800">
              {tasks.map((task) => (
                <TaskRow
                  key={task.id}
                  task={task}
                  expanded={expandedTaskId === task.id}
                  onToggle={() => setExpandedTaskId(expandedTaskId === task.id ? null : task.id)}
                  onRetry={() => handleRetryTask(task.id)}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'logs' && (
        <div className="bg-slate-900/50 backdrop-blur-sm border border-slate-800 rounded-xl overflow-hidden">
          <div className="p-4 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Terminal className="w-5 h-5 text-blue-500" aria-hidden="true" />
              Generation Logs
            </h2>
            <div className="flex items-center gap-3">
              <label htmlFor="log-filter" className="text-sm text-slate-400">Filter:</label>
              <select
                id="log-filter"
                value={logFilter}
                onChange={(e) => setLogFilter(e.target.value)}
                className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {logLevels.map(level => (
                  <option key={level} value={level}>
                    {level === 'all' ? 'All Levels' : level.charAt(0).toUpperCase() + level.slice(1)}
                  </option>
                ))}
              </select>
              <span className="px-2 py-1 bg-slate-800 border border-slate-700 rounded-lg text-xs text-slate-400">
                {filteredLogs.length} entries
              </span>
            </div>
          </div>
          {filteredLogs.length === 0 ? (
            <div className="p-12 text-center">
              <Terminal className="w-12 h-12 text-slate-500 mx-auto mb-4" aria-hidden="true" />
              <h3 className="text-lg font-semibold text-white mb-2">No logs yet</h3>
              <p className="text-slate-400">Generation logs will appear here once the pipeline starts.</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-800 max-h-[600px] overflow-y-auto">
              {filteredLogs.map((log) => (
                <LogRow key={log.id} log={log} />
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'files' && (
        <div className="bg-slate-900/50 backdrop-blur-sm border border-slate-800 rounded-xl overflow-hidden h-[calc(100vh-320px)] min-h-[500px]">
          <FileExplorer
            projectId={projectId!}
          />
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={() => setShowDeleteConfirm(false)}>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-white mb-2">Delete Project</h3>
            <p className="text-slate-400 mb-6">
              Are you sure you want to delete "{project.name}"? This action cannot be undone and will permanently remove all project data, tasks, and logs.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white font-medium rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white font-medium rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {deleting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                    Deleting...
                  </>
                ) : (
                  'Delete Project'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

interface InfoItemProps {
  label: string
  value: string
  copyable?: boolean
}

function InfoItem({ label, value, copyable }: InfoItemProps) {
  const [copied, setCopied] = useState(false)
  return (
    <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
      <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">{label}</p>
      <div className="flex items-center gap-2">
        <p className="text-white font-mono text-sm truncate flex-1">{value}</p>
        {copyable && (
          <button
            onClick={() => {
              navigator.clipboard.writeText(value)
              setCopied(true)
              setTimeout(() => setCopied(false), 2000)
            }}
            className="p-1.5 text-slate-500 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
            aria-label={copied ? 'Copied!' : 'Copy to clipboard'}
            title={copied ? 'Copied!' : 'Copy to clipboard'}
          >
            {copied ? <CheckCircle className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
          </button>
        )}
      </div>
    </div>
  )
}

interface TaskRowProps {
  task: {
    id: string
    project_id: string
    name: string
    description?: string
    status: string
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
  expanded: boolean
  onToggle: () => void
  onRetry: (taskId: string) => void
}

function TaskRow({ task, expanded, onToggle, onRetry }: TaskRowProps) {
  const statusColors = getStatusColor(task.status)
  const statusIcons: Record<string, React.ReactNode> = {
    pending: <Clock className="w-4 h-4" />,
    running: <Loader2 className="w-4 h-4 animate-spin" />,
    completed: <CheckCircle className="w-4 h-4" />,
    failed: <XCircle className="w-4 h-4" />,
  }

  return (
    <div className="bg-slate-950/50">
      <button
        onClick={onToggle}
        className="w-full p-4 flex items-center gap-4 hover:bg-slate-900 transition-colors text-left"
        aria-expanded={expanded}
      >
        <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0', statusColors)}>
          {statusIcons[task.status] || <Clock className="w-4 h-4" />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3">
            <h4 className="font-medium text-white truncate">{task.name}</h4>
            <span className={cn('px-2 py-0.5 text-xs font-medium rounded-full border', statusColors)}>
              {task.status.charAt(0).toUpperCase() + task.status.slice(1)}
            </span>
            {task.agent_type && (
              <span className="px-2 py-0.5 text-xs text-slate-400 bg-slate-800 rounded-full">
                {task.agent_type}
              </span>
            )}
          </div>
          {task.description && (
            <p className="text-slate-400 text-sm mt-1 truncate">{task.description}</p>
          )}
        </div>
        <div className="flex items-center gap-2 text-slate-500">
          <span className="text-xs">Step {task.step_order}</span>
          <ChevronDown className={cn('w-4 h-4 transition-transform', expanded && 'rotate-180')} aria-hidden="true" />
        </div>
      </button>
      {expanded && (
        <div className="p-4 border-t border-slate-800 bg-slate-950 space-y-4">
          {task.error_message && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
              <div className="flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
                <div className="flex-1">
                  <p className="text-red-400 text-sm font-medium mb-1">Error</p>
                  <p className="text-red-300 text-sm font-mono">{task.error_message}</p>
                </div>
                {task.status === 'failed' && (
                  <button
                    onClick={() => onRetry(task.id)}
                    className="px-3 py-1.5 bg-red-600 hover:bg-red-500 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2"
                  >
                    <RefreshCw className="w-3 h-3" aria-hidden="true" />
                    Retry
                  </button>
                )}
              </div>
            </div>
          )}
          <div className="grid gap-4 sm:grid-cols-2">
            <DetailItem label="Task ID" value={task.id} copyable />
            <DetailItem label="Agent Type" value={task.agent_type || '—'} />
            <DetailItem label="Started" value={task.started_at ? formatRelativeTime(task.started_at) : '—'} />
            <DetailItem label="Completed" value={task.completed_at ? formatRelativeTime(task.completed_at) : '—'} />
          </div>
          {task.input_data && Object.keys(task.input_data).length > 0 && (
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">Input Data</p>
              <pre className="bg-slate-950 border border-slate-800 rounded-lg p-3 overflow-x-auto text-xs text-slate-300 max-h-48">
                {JSON.stringify(task.input_data, null, 2)}
              </pre>
            </div>
          )}
          {task.output_data && Object.keys(task.output_data).length > 0 && (
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">Output Data</p>
              <pre className="bg-slate-950 border border-slate-800 rounded-lg p-3 overflow-x-auto text-xs text-slate-300 max-h-48">
                {JSON.stringify(task.output_data, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

interface DetailItemProps {
  label: string
  value: string
  copyable?: boolean
}

function DetailItem({ label, value, copyable }: DetailItemProps) {
  const [copied, setCopied] = useState(false)
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-3">
      <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">{label}</p>
      <div className="flex items-center gap-2">
        <p className="text-white font-mono text-sm truncate flex-1">{value}</p>
        {copyable && (
          <button
            onClick={() => {
              navigator.clipboard.writeText(value)
              setCopied(true)
              setTimeout(() => setCopied(false), 2000)
            }}
            className="p-1 text-slate-500 hover:text-white hover:bg-slate-800 rounded transition-colors"
            aria-label={copied ? 'Copied!' : 'Copy to clipboard'}
            title={copied ? 'Copied!' : 'Copy to clipboard'}
          >
            {copied ? <CheckCircle className="w-3 h-3 text-green-400" /> : <Copy className="w-3 h-3" />}
          </button>
        )}
      </div>
    </div>
  )
}

interface LogRowProps {
  log: {
    id: string
    project_id: string
    level: string
    message: string
    context?: Record<string, any>
    created_at: string
  }
}

function LogRow({ log }: LogRowProps) {
  const levelColors: Record<string, string> = {
    info: 'text-blue-400 bg-blue-500/20',
    warn: 'text-yellow-400 bg-yellow-500/20',
    error: 'text-red-400 bg-red-500/20',
    debug: 'text-slate-400 bg-slate-500/20',
  }
  const levelColor = levelColors[log.level.toLowerCase()] || 'text-slate-400 bg-slate-500/20'

  return (
    <div className="p-4 hover:bg-slate-900/50 transition-colors">
      <div className="flex items-start gap-3">
        <div className="flex flex-col items-center gap-1">
          <span className={cn('px-2 py-0.5 text-xs font-mono rounded', levelColor)}>
            {log.level.toUpperCase()}
          </span>
          <span className="text-xs text-slate-500 font-mono">{formatRelativeTime(log.created_at)}</span>
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-slate-300 text-sm font-mono">{log.message}</p>
          {log.context && Object.keys(log.context).length > 0 && (
            <details className="mt-2">
              <summary className="text-xs text-slate-500 cursor-pointer hover:text-slate-400">
                Show context
              </summary>
              <pre className="mt-2 bg-slate-950 border border-slate-800 rounded-lg p-2 overflow-x-auto text-xs text-slate-300 max-h-32">
                {JSON.stringify(log.context, null, 2)}
              </pre>
            </details>
          )}
        </div>
      </div>
    </div>
  )
}