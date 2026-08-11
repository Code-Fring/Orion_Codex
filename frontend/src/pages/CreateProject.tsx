import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useProject } from '../contexts/ProjectContext'
import { ArrowLeft, Loader2, Sparkles } from 'lucide-react'
import { cn } from '../utils/cn'

export default function CreateProject() {
  const { createProject } = useProject()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [prompt, setPrompt] = useState('')
  const [techStack, setTechStack] = useState({
    frontend: '',
    backend: '',
    database: '',
    deployment: '',
  })
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'basic' | 'tech'>('basic')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!name.trim()) {
      setError('Project name is required')
      return
    }

    if (!prompt.trim()) {
      setError('Project prompt is required')
      return
    }

    setIsLoading(true)

    try {
      const project = await createProject({
        name: name.trim(),
        description: description.trim() || undefined,
        prompt: prompt.trim(),
        tech_stack_preferences: Object.fromEntries(
          Object.entries(techStack).filter(([_, v]) => v)
        ),
      })
      navigate(`/projects/${project.id}`)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create project')
    } finally {
      setIsLoading(false)
    }
  }

  const techOptions = {
    frontend: ['React', 'Vue', 'Svelte', 'Next.js', 'Nuxt', 'Remix', 'Astro', 'Vanilla JS'],
    backend: ['Node.js', 'Python (FastAPI)', 'Python (Django)', 'Go', 'Rust', 'Java', 'C# (.NET)', 'Bun'],
    database: ['PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'SQLite', 'Supabase', 'PlanetScale', 'Firebase'],
    deployment: ['Docker', 'Kubernetes', 'Vercel', 'Netlify', 'AWS', 'GCP', 'Azure', 'Railway'],
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate(-1)}
          className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
          aria-label="Go back"
        >
          <ArrowLeft className="w-5 h-5" aria-hidden="true" />
        </button>
        <div>
          <h1 className="text-3xl font-bold text-white">Create New Project</h1>
          <p className="text-slate-400">Describe what you want to build and let Orion Codex generate it</p>
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Tab Navigation */}
        <div className="flex gap-1 bg-slate-800 rounded-lg p-1">
          <button
            type="button"
            onClick={() => setActiveTab('basic')}
            className={cn(
              'flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors',
              activeTab === 'basic' ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'
            )}
          >
            <Sparkles className="w-4 h-4 inline mr-1" aria-hidden="true" />
            Basic Info
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('tech')}
            className={cn(
              'flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors',
              activeTab === 'tech' ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'
            )}
          >
            Tech Stack
          </button>
        </div>

        {error && (
          <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400">
            {error}
          </div>
        )}

        {/* Basic Info Tab */}
        {activeTab === 'basic' && (
          <div className="space-y-5" role="tabpanel" aria-label="Basic Information">
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-slate-300 mb-1.5">
                Project Name <span className="text-red-400">*</span>
              </label>
              <input
                id="name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                placeholder="e.g., Task Manager App"
                required
                disabled={isLoading}
              />
            </div>

            <div>
              <label htmlFor="description" className="block text-sm font-medium text-slate-300 mb-1.5">
                Description (optional)
              </label>
              <textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
                className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all resize-none"
                placeholder="Brief description of your project..."
                disabled={isLoading}
              />
            </div>

            <div>
              <label htmlFor="prompt" className="block text-sm font-medium text-slate-300 mb-1.5">
                Project Prompt <span className="text-red-400">*</span>
              </label>
              <textarea
                id="prompt"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                rows={8}
                className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all resize-none font-mono text-sm"
                placeholder="Describe what you want to build in detail. For example:
'A full-stack task management application with user authentication, project boards, task assignments, due dates, comments, and real-time notifications. Use React for frontend, Node.js/Express for backend, PostgreSQL for database, and deploy with Docker.'"
                required
                disabled={isLoading}
              />
              <p className="mt-1 text-xs text-slate-500">
                Be as detailed as possible. Include features, user flows, data models, and any specific requirements.
              </p>
            </div>
          </div>
        )}

        {/* Tech Stack Tab */}
        {activeTab === 'tech' && (
          <div className="space-y-5" role="tabpanel" aria-label="Technology Stack">
            <p className="text-slate-400 text-sm">
              Optionally specify your preferred technology stack. Leave blank for AI to choose optimal technologies.
            </p>
            {Object.entries(techOptions).map(([category, options]) => (
              <div key={category} className="space-y-3">
                <label className="block text-sm font-medium text-slate-300 capitalize">
                  {category.replace(/([A-Z])/g, ' $1').trim()}
                </label>
                <select
                  value={techStack[category as keyof typeof techStack]}
                  onChange={(e) => setTechStack(prev => ({ ...prev, [category]: e.target.value }))}
                  className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                  disabled={isLoading}
                >
                  <option value="">Auto-select (recommended)</option>
                  {options.map(opt => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              </div>
            ))}
          </div>
        )}

        {/* Submit */}
        <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="px-6 py-3 bg-slate-800 hover:bg-slate-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50"
            disabled={isLoading}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" aria-hidden="true" />
                Creating...
              </>
            ) : (
              'Create Project'
            )}
          </button>
        </div>
      </form>
    </div>
  )
}