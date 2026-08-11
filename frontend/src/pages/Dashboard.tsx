import React, { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useProject } from '../contexts/ProjectContext'
import { Plus, FolderGit2, AlertCircle, RefreshCw, Trash2, MoreVertical, Loader2 } from 'lucide-react'
import { cn, formatRelativeTime, getStatusColor, truncate } from '../utils/cn'

export default function Dashboard() {
  const { projects, isLoading, fetchProjects, deleteProject, regenerateProject } = useProject()
  const [deletingId, setDeletingId] = React.useState<string | null>(null)
  const [regeneratingId, setRegeneratingId] = React.useState<string | null>(null)

  useEffect(() => {
    fetchProjects()
  }, [fetchProjects])

  const handleDelete = async (projectId: string) => {
    if (!window.confirm('Are you sure you want to delete this project? This cannot be undone.')) return
    setDeletingId(projectId)
    try {
      await deleteProject(projectId)
    } finally {
      setDeletingId(null)
    }
  }

  const handleRegenerate = async (projectId: string) => {
    setRegeneratingId(projectId)
    try {
      await regenerateProject(projectId)
    } finally {
      setRegeneratingId(null)
    }
  }

  if (isLoading && projects.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" aria-label="Loading projects" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white">Dashboard</h1>
          <p className="text-slate-400 mt-1">Manage your software projects</p>
        </div>
        <Link
          to="/projects/new"
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg transition-colors"
        >
          <Plus className="w-5 h-5" aria-hidden="true" />
          New Project
        </Link>
      </div>

      {/* Projects Grid */}
      {projects.length === 0 ? (
        <div className="text-center py-16">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-slate-800 mb-4">
            <FolderGit2 className="w-8 h-8 text-slate-500" aria-hidden="true" />
          </div>
          <h2 className="text-xl font-semibold text-white mb-2">No projects yet</h2>
          <p className="text-slate-400 mb-6 max-w-md mx-auto">
            Start building your first autonomous software project with Orion Codex.
          </p>
          <Link
            to="/projects/new"
            className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg transition-colors"
          >
            <Plus className="w-5 h-5" aria-hidden="true" />
            Create Project
          </Link>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {projects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              onDelete={handleDelete}
              onRegenerate={handleRegenerate}
              isDeleting={deletingId === project.id}
              isRegenerating={regeneratingId === project.id}
            />
          ))}
        </div>
      )}
    </div>
  )
}

interface ProjectCardProps {
  project: {
    id: string
    name: string
    description?: string
    prompt: string
    status: string
    progress: number
    created_at: string
    updated_at: string
    completed_at?: string
    error_message?: string
  }
  onDelete: (id: string) => void
  onRegenerate: (id: string) => void
  isDeleting: boolean
  isRegenerating: boolean
}

function ProjectCard({ project, onDelete, onRegenerate, isDeleting, isRegenerating }: ProjectCardProps) {
  const [showMenu, setShowMenu] = React.useState(false)

  const statusColors = getStatusColor(project.status)

  return (
    <div className="bg-slate-900/50 backdrop-blur-sm border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-colors relative">
      {/* Status badge */}
      <div className="flex items-start justify-between mb-4">
        <span className={cn('px-2.5 py-1 text-xs font-medium rounded-full border', statusColors)}>
          {project.status.charAt(0).toUpperCase() + project.status.slice(1)}
        </span>
        <div className="relative">
          <button
            onClick={(e) => { e.stopPropagation(); setShowMenu(!showMenu) }}
            className="p-1.5 text-slate-500 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
            aria-label="More options"
            aria-expanded={showMenu}
          >
            <MoreVertical className="w-5 h-5" aria-hidden="true" />
          </button>
          {showMenu && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setShowMenu(false)} />
              <div className="absolute right-0 top-full mt-1 w-40 bg-slate-900 border border-slate-800 rounded-lg shadow-lg py-1 z-20">
                <button
                  onClick={() => { setShowMenu(false); onRegenerate(project.id) }}
                  disabled={isRegenerating}
                  className="w-full flex items-center gap-2 px-4 py-2 text-slate-300 hover:text-white hover:bg-slate-800 text-left disabled:opacity-50"
                >
                  <RefreshCw className="w-4 h-4" aria-hidden="true" />
                  Regenerate
                </button>
                <button
                  onClick={() => { setShowMenu(false); onDelete(project.id) }}
                  disabled={isDeleting}
                  className="w-full flex items-center gap-2 px-4 py-2 text-red-400 hover:text-red-300 hover:bg-slate-800 text-left disabled:opacity-50"
                >
                  <Trash2 className="w-4 h-4" aria-hidden="true" />
                  Delete
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Project info */}
      <Link to={`/projects/${project.id}`} className="block">
        <h3 className="font-semibold text-white mb-1 truncate">{project.name}</h3>
        {project.description && (
          <p className="text-slate-400 text-sm mb-3 line-clamp-2">{project.description}</p>
        )}
        <p className="text-slate-500 text-xs mb-4 line-clamp-2">{truncate(project.prompt, 100)}</p>
      </Link>

      {/* Progress bar for active projects */}
      {['pending', 'planning', 'building', 'testing', 'review', 'deployment'].includes(project.status) && (
        <div className="mb-4">
          <div className="flex justify-between text-xs mb-1">
            <span className="text-slate-400">Progress</span>
            <span className="text-white">{project.progress}%</span>
          </div>
          <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 transition-all duration-300"
              style={{ width: `${project.progress}%` }}
              role="progressbar"
              aria-valuenow={project.progress}
              aria-valuemin={0}
              aria-valuemax={100}
            />
          </div>
        </div>
      )}

      {/* Error message */}
      {project.error_message && (
        <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
            <p className="text-red-400 text-sm">{truncate(project.error_message, 150)}</p>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between text-xs text-slate-500 pt-4 border-t border-slate-800">
        <span>Updated {formatRelativeTime(project.updated_at)}</span>
        {project.completed_at && (
          <span className="text-green-400">Completed {formatRelativeTime(project.completed_at)}</span>
        )}
      </div>
    </div>
  )
}