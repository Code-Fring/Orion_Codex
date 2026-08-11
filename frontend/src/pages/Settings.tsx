import React, { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../services/api'
import {
  User,
  Key,
  Server,
  Save,
  Loader2,
  AlertCircle,
  CheckCircle,
  Trash2,
  Plus,
  Eye,
  EyeOff,
  TestTube,
  Zap,
  Shield,
  Bell,
  Palette,
  Globe,
  Database,
  Terminal,
  Settings as SettingsIcon,
} from 'lucide-react'
import { cn } from '../utils/cn'

interface ProviderConfig {
  id: string
  name: string
  type: string
  config: Record<string, any>
  is_active: boolean
  created_at: string
  updated_at: string
}

interface APIKey {
  id: string
  provider: string
  name: string
  is_active: boolean
  created_at: string
  last_used?: string
}

interface ProviderStatus {
  provider: string
  connected: boolean
  models: Array<{
    id: string
    name: string
    capabilities: string[]
    max_tokens: number
    context_window: number
  }>
}

export default function Settings() {
  const { user } = useAuth()

  // Profile state
  const [profile, setProfile] = useState({
    name: user?.name || '',
    email: user?.email || '',
  })
  const [profileLoading, setProfileLoading] = useState(false)
  const [profileError, setProfileError] = useState<string | null>(null)
  const [profileSuccess, setProfileSuccess] = useState<string | null>(null)

  // Password state
  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  })
  const [passwordLoading, setPasswordLoading] = useState(false)
  const [passwordError, setPasswordError] = useState<string | null>(null)
  const [passwordSuccess, setPasswordSuccess] = useState<string | null>(null)
  const [showCurrentPassword, setShowCurrentPassword] = useState(false)
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  // Providers state
  const [providers, setProviders] = useState<ProviderConfig[]>([])
  const [providerLoading, setProviderLoading] = useState(false)
  const [providerStatuses, setProviderStatuses] = useState<Record<string, ProviderStatus>>({})
  const [testingProvider, setTestingProvider] = useState<string | null>(null)
  const [showProviderModal, setShowProviderModal] = useState(false)
  const [editingProvider, setEditingProvider] = useState<ProviderConfig | null>(null)
  const [newProvider, setNewProvider] = useState({
    name: '',
    type: 'openai',
    config: {},
  })
  const [providerTypes] = useState([
    { value: 'openai', label: 'OpenAI', icon: Zap },
    { value: 'anthropic', label: 'Anthropic', icon: Shield },
    { value: 'google', label: 'Google', icon: Globe },
    { value: 'openrouter', label: 'OpenRouter', icon: Database },
    { value: 'omniroute', label: 'OmniRoute', icon: Database },
    { value: 'lmstudio', label: 'LM Studio (Local)', icon: Terminal },
    { value: 'deepseek', label: 'DeepSeek', icon: Zap },
    { value: 'groq', label: 'Groq', icon: Zap },
    { value: 'nvidia', label: 'NVIDIA', icon: Zap },
  ])

  // API Keys state
  const [apiKeys, setApiKeys] = useState<APIKey[]>([])
  const [apiKeyLoading, setApiKeyLoading] = useState(false)
  const [showApiKeyModal, setShowApiKeyModal] = useState(false)
  const [newApiKey, setNewApiKey] = useState({
    provider: 'openai',
    name: '',
    api_key: '',
  })
  const [showApiKeyValue, setShowApiKeyValue] = useState(false)

  // Active tab
  const [activeTab, setActiveTab] = useState<'profile' | 'providers' | 'api-keys' | 'appearance' | 'notifications'>('profile')

  // Load providers on mount
  useEffect(() => {
    loadProviders()
    loadProviderStatuses()
    loadApiKeys()
  }, [])

  const loadProviders = async () => {
    setProviderLoading(true)
    try {
      const data = await api.listProviders()
      setProviders(data)
    } catch (err: any) {
      console.error('Failed to load providers:', err)
    } finally {
      setProviderLoading(false)
    }
  }

  const loadProviderStatuses = async () => {
    try {
      const data = await api.getAllProviderStatuses()
      const statusMap: Record<string, ProviderStatus> = {}
      data.forEach((status: ProviderStatus) => {
        statusMap[status.provider] = status
      })
      setProviderStatuses(statusMap)
    } catch (err) {
      console.error('Failed to load provider statuses:', err)
    }
  }

  const loadApiKeys = async () => {
    setApiKeyLoading(true)
    try {
      const data = await api.listApiKeys()
      setApiKeys(data)
    } catch (err) {
      console.error('Failed to load API keys:', err)
    } finally {
      setApiKeyLoading(false)
    }
  }

  const handleProfileSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setProfileLoading(true)
    setProfileError(null)
    setProfileSuccess(null)
    try {
      // In a real app, this would call an API to update profile
      await new Promise(resolve => setTimeout(resolve, 1000))
      setProfileSuccess('Profile updated successfully!')
    } catch (err: any) {
      setProfileError(err.response?.data?.detail || 'Failed to update profile')
    } finally {
      setProfileLoading(false)
    }
  }

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setPasswordError(null)
    setPasswordSuccess(null)

    if (passwordData.new_password !== passwordData.confirm_password) {
      setPasswordError('New passwords do not match')
      return
    }

    if (passwordData.new_password.length < 8) {
      setPasswordError('Password must be at least 8 characters')
      return
    }

    setPasswordLoading(true)
    try {
      // In a real app, this would call an API to change password
      await new Promise(resolve => setTimeout(resolve, 1000))
      setPasswordData({ current_password: '', new_password: '', confirm_password: '' })
      setPasswordSuccess('Password changed successfully!')
    } catch (err: any) {
      setPasswordError(err.response?.data?.detail || 'Failed to change password')
    } finally {
      setPasswordLoading(false)
    }
  }

  const handleCreateProvider = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await api.createProvider(newProvider)
      setShowProviderModal(false)
      setNewProvider({ name: '', type: 'openai', config: {} })
      loadProviders()
      loadProviderStatuses()
    } catch (err: any) {
      console.error('Create provider error:', err)
      const message = err.response?.data?.detail ?? err.response?.data?.message ?? err.message ?? 'Failed to create provider'
      alert(message)
    }
  }

  const handleUpdateProvider = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingProvider) return
    try {
      await api.updateProvider(editingProvider.id, {
        name: editingProvider.name,
        config: editingProvider.config,
        is_active: editingProvider.is_active,
      })
      setEditingProvider(null)
      loadProviders()
      loadProviderStatuses()
    } catch (err: any) {
      console.error('Update provider error:', err)
      const message = err.response?.data?.detail ?? err.response?.data?.message ?? err.message ?? 'Failed to update provider'
      alert(message)
    }
  }

  const handleDeleteProvider = async (providerId: string) => {
    if (!window.confirm('Are you sure you want to delete this provider configuration?')) return
    try {
      await api.deleteProvider(providerId)
      loadProviders()
      loadProviderStatuses()
    } catch (err: any) {
      console.error('Delete provider error:', err)
      const message = err.response?.data?.detail ?? err.response?.data?.message ?? err.message ?? 'Failed to delete provider'
      alert(message)
    }
  }

  const handleTestProvider = async (providerId: string, providerType: string) => {
    setTestingProvider(providerId)
    try {
      const status = await api.testProvider(providerType)
      setProviderStatuses(prev => ({ ...prev, [providerId]: status }))
    } catch (err: any) {
      setProviderStatuses(prev => ({ ...prev, [providerId]: { provider: providerType, connected: false, models: [] } }))
    } finally {
      setTestingProvider(null)
    }
  }

  const handleCreateApiKey = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await api.createApiKey(newApiKey)
      setShowApiKeyModal(false)
      setNewApiKey({ provider: 'openai', name: '', api_key: '' })
      loadApiKeys()
    } catch (err: any) {
      console.error('Create API key error:', err)
      const message = err.response?.data?.detail ?? err.response?.data?.message ?? err.message ?? 'Failed to create API key'
      alert(message)
    }
  }

  const handleDeleteApiKey = async (keyId: string) => {
    if (!window.confirm('Are you sure you want to delete this API key?')) return
    try {
      await api.deleteApiKey(keyId)
      loadApiKeys()
    } catch (err: any) {
      console.error('Delete API key error:', err)
      const message = err.response?.data?.detail ?? err.response?.data?.message ?? err.message ?? 'Failed to delete API key'
      alert(message)
    }
  }

  const providerConfigFields: Record<string, Array<{ key: string; label: string; type: string; placeholder: string }>> = {
    openai: [
      { key: 'api_key', label: 'API Key', type: 'password', placeholder: 'sk-...' },
      { key: 'base_url', label: 'Base URL (optional)', type: 'text', placeholder: 'https://api.openai.com/v1' },
      { key: 'organization', label: 'Organization ID (optional)', type: 'text', placeholder: 'org-...' },
    ],
    anthropic: [
      { key: 'api_key', label: 'API Key', type: 'password', placeholder: 'sk-ant-...' },
      { key: 'base_url', label: 'Base URL (optional)', type: 'text', placeholder: 'https://api.anthropic.com' },
    ],
    google: [
      { key: 'api_key', label: 'API Key', type: 'password', placeholder: 'AIza...' },
      { key: 'base_url', label: 'Base URL (optional)', type: 'text', placeholder: 'https://generativelanguage.googleapis.com/v1beta' },
    ],
    openrouter: [
      { key: 'api_key', label: 'API Key', type: 'password', placeholder: 'sk-or-v1-...' },
      { key: 'base_url', label: 'Base URL (optional)', type: 'text', placeholder: 'https://openrouter.ai/api/v1' },
      { key: 'http_referer', label: 'HTTP Referer (optional)', type: 'text', placeholder: 'https://your-app.com' },
      { key: 'x_title', label: 'X-Title (optional)', type: 'text', placeholder: 'Your App Name' },
    ],
    omniroute: [
      { key: 'api_key', label: 'API Key', type: 'password', placeholder: 'sk-or-...' },
      { key: 'base_url', label: 'Base URL (optional)', type: 'text', placeholder: 'https://api.omniroute.ai/v1' },
      { key: 'http_referer', label: 'HTTP Referer (optional)', type: 'text', placeholder: 'https://your-app.com' },
      { key: 'x_title', label: 'X-Title (optional)', type: 'text', placeholder: 'Your App Name' },
    ],
    lmstudio: [
      { key: 'base_url', label: 'Base URL', type: 'text', placeholder: 'http://localhost:1234/v1' },
    ],
    deepseek: [
      { key: 'api_key', label: 'API Key', type: 'password', placeholder: 'sk-...' },
      { key: 'base_url', label: 'Base URL (optional)', type: 'text', placeholder: 'https://api.deepseek.com/v1' },
    ],
    groq: [
      { key: 'api_key', label: 'API Key', type: 'password', placeholder: 'gsk_...' },
      { key: 'base_url', label: 'Base URL (optional)', type: 'text', placeholder: 'https://api.groq.com/openai/v1' },
    ],
    nvidia: [
      { key: 'api_key', label: 'API Key', type: 'password', placeholder: 'nvapi-...' },
      { key: 'base_url', label: 'Base URL (optional)', type: 'text', placeholder: 'https://integrate.api.nvidia.com/v1' },
    ],
  }

  const tabs = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'providers', label: 'AI Providers', icon: Server },
    { id: 'api-keys', label: 'API Keys', icon: Key },
    { id: 'appearance', label: 'Appearance', icon: Palette },
    { id: 'notifications', label: 'Notifications', icon: Bell },
  ]

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white">Settings</h1>
          <p className="text-slate-400">Manage your account, AI providers, and preferences</p>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-1 bg-slate-800 rounded-lg p-1 border border-slate-700 overflow-x-auto">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id as typeof activeTab)}
            className={cn(
              'flex items-center gap-2 px-4 py-2.5 rounded-md text-sm font-medium transition-colors whitespace-nowrap',
              activeTab === id ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'
            )}
          >
            <Icon className="w-4 h-4" aria-hidden="true" />
            {label}
          </button>
        ))}
      </div>

      {/* Profile Tab */}
      {activeTab === 'profile' && (
        <div className="space-y-6">
          {/* Profile Info */}
          <div className="bg-slate-900/50 backdrop-blur-sm border border-slate-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
              <User className="w-5 h-5 text-blue-500" aria-hidden="true" />
              Profile Information
            </h2>
            <form onSubmit={handleProfileSubmit} className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label htmlFor="name" className="block text-sm font-medium text-slate-300 mb-1.5">
                    Display Name
                  </label>
                  <input
                    id="name"
                    type="text"
                    value={profile.name}
                    onChange={(e) => setProfile(prev => ({ ...prev, name: e.target.value }))}
                    className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                    disabled={profileLoading}
                  />
                </div>
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-slate-300 mb-1.5">
                    Email Address
                  </label>
                  <input
                    id="email"
                    type="email"
                    value={profile.email}
                    onChange={(e) => setProfile(prev => ({ ...prev, email: e.target.value }))}
                    className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                    disabled={profileLoading}
                  />
                </div>
              </div>
              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={profileLoading}
                  className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
                >
                  {profileLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="w-4 h-4" aria-hidden="true" />
                      Save Changes
                    </>
                  )}
                </button>
              </div>
              {profileError && (
                <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4" aria-hidden="true" />
                  {profileError}
                </div>
              )}
              {profileSuccess && (
                <div className="p-3 bg-green-500/10 border border-green-500/20 rounded-lg text-green-400 flex items-center gap-2">
                  <CheckCircle className="w-4 h-4" aria-hidden="true" />
                  {profileSuccess}
                </div>
              )}
            </form>
          </div>

          {/* Change Password */}
          <div className="bg-slate-900/50 backdrop-blur-sm border border-slate-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
              <Shield className="w-5 h-5 text-blue-500" aria-hidden="true" />
              Change Password
            </h2>
            <form onSubmit={handlePasswordSubmit} className="space-y-4">
              <div>
                <label htmlFor="current_password" className="block text-sm font-medium text-slate-300 mb-1.5">
                  Current Password
                </label>
                <div className="relative">
                  <input
                    id="current_password"
                    type={showCurrentPassword ? 'text' : 'password'}
                    value={passwordData.current_password}
                    onChange={(e) => setPasswordData(prev => ({ ...prev, current_password: e.target.value }))}
                    className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all pr-12"
                    disabled={passwordLoading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
                    aria-label={showCurrentPassword ? 'Hide password' : 'Show password'}
                  >
                    {showCurrentPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>
              <div>
                <label htmlFor="new_password" className="block text-sm font-medium text-slate-300 mb-1.5">
                  New Password
                </label>
                <div className="relative">
                  <input
                    id="new_password"
                    type={showNewPassword ? 'text' : 'password'}
                    value={passwordData.new_password}
                    onChange={(e) => setPasswordData(prev => ({ ...prev, new_password: e.target.value }))}
                    className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all pr-12"
                    disabled={passwordLoading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
                    aria-label={showNewPassword ? 'Hide password' : 'Show password'}
                  >
                    {showNewPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>
              <div>
                <label htmlFor="confirm_password" className="block text-sm font-medium text-slate-300 mb-1.5">
                  Confirm New Password
                </label>
                <div className="relative">
                  <input
                    id="confirm_password"
                    type={showConfirmPassword ? 'text' : 'password'}
                    value={passwordData.confirm_password}
                    onChange={(e) => setPasswordData(prev => ({ ...prev, confirm_password: e.target.value }))}
                    className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all pr-12"
                    disabled={passwordLoading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
                    aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                  >
                    {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>
              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={passwordLoading}
                  className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
                >
                  {passwordLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                      Changing...
                    </>
                  ) : (
                    'Change Password'
                  )}
                </button>
              </div>
              {passwordError && (
                <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4" aria-hidden="true" />
                  {passwordError}
                </div>
              )}
              {passwordSuccess && (
                <div className="p-3 bg-green-500/10 border border-green-500/20 rounded-lg text-green-400 flex items-center gap-2">
                  <CheckCircle className="w-4 h-4" aria-hidden="true" />
                  {passwordSuccess}
                </div>
              )}
            </form>
          </div>

          {/* Danger Zone */}
          <div className="bg-slate-900/50 backdrop-blur-sm border border-red-500/20 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-red-500" aria-hidden="true" />
              Danger Zone
            </h2>
            <p className="text-slate-400 mb-4">
              Once you delete your account, there is no going back. Please be certain.
            </p>
            <button
              onClick={() => {
                if (window.confirm('Are you absolutely sure you want to delete your account? This cannot be undone.')) {
                  alert('Account deletion would be implemented here')
                }
              }}
              className="px-6 py-3 bg-red-600 hover:bg-red-500 text-white font-medium rounded-lg transition-colors flex items-center gap-2"
            >
              <Trash2 className="w-4 h-4" aria-hidden="true" />
              Delete Account
            </button>
          </div>
        </div>
      )}

      {/* Providers Tab */}
      {activeTab === 'providers' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Server className="w-5 h-5 text-blue-500" aria-hidden="true" />
              AI Providers
            </h2>
            <button
              onClick={() => {
                setEditingProvider(null)
                setNewProvider({ name: '', type: 'openai', config: {} })
                setShowProviderModal(true)
              }}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg transition-colors flex items-center gap-2"
            >
              <Plus className="w-4 h-4" aria-hidden="true" />
              Add Provider
            </button>
          </div>

          {providerLoading ? (
            <div className="flex items-center justify-center h-64">
              <Loader2 className="w-8 h-8 text-blue-500 animate-spin" aria-label="Loading providers" />
            </div>
          ) : providers.length === 0 ? (
            <div className="text-center py-16 bg-slate-900/50 backdrop-blur-sm border border-slate-800 rounded-xl">
              <Server className="w-12 h-12 text-slate-500 mx-auto mb-4" aria-hidden="true" />
              <h3 className="text-lg font-semibold text-white mb-2">No AI providers configured</h3>
              <p className="text-slate-400 mb-6 max-w-md mx-auto">
                Add an AI provider to enable code generation capabilities.
              </p>
              <button
                onClick={() => {
                  setEditingProvider(null)
                  setNewProvider({ name: '', type: 'openai', config: {} })
                  setShowProviderModal(true)
                }}
                className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg transition-colors flex items-center gap-2 mx-auto"
              >
                <Plus className="w-4 h-4" aria-hidden="true" />
                Add Provider
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {providers.map((provider) => {
                const status = providerStatuses[provider.id]
                const Icon = providerTypes.find(t => t.value === provider.type)?.icon || Server
                return (
                  <div key={provider.id} className="bg-slate-900/50 backdrop-blur-sm border border-slate-800 rounded-xl p-5">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-center gap-4 flex-1 min-w-0">
                        <div className={cn('p-3 rounded-lg flex-shrink-0', provider.is_active ? 'bg-blue-500/20' : 'bg-slate-800')}>
                          <Icon className={cn('w-6 h-6', provider.is_active ? 'text-blue-400' : 'text-slate-500')} aria-hidden="true" />
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-3">
                            <h3 className="font-semibold text-white truncate">{provider.name}</h3>
                            <span className={cn('px-2 py-0.5 text-xs font-medium rounded-full', provider.is_active ? 'bg-green-500/20 text-green-400' : 'bg-slate-700 text-slate-400')}>
                              {provider.is_active ? 'Active' : 'Inactive'}
                            </span>
                          </div>
                          <p className="text-slate-400 text-sm mt-1 capitalize">{provider.type}</p>
                          {status && (
                            <div className="flex items-center gap-2 mt-2">
                              <span className={cn('w-2 h-2 rounded-full', status.connected ? 'bg-green-400' : 'bg-red-400')} />
                              <span className="text-xs text-slate-400">
                                {status.connected ? `Connected (${status.models.length} models)` : 'Disconnected'}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <button
                          onClick={() => handleTestProvider(provider.id, provider.type)}
                          disabled={testingProvider === provider.id}
                          className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors disabled:opacity-50"
                          aria-label="Test connection"
                        >
                          {testingProvider === provider.id ? (
                            <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                          ) : (
                            <TestTube className="w-4 h-4" aria-hidden="true" />
                          )}
                        </button>
                        <button
                          onClick={() => {
                            setEditingProvider(provider)
                            setShowProviderModal(true)
                          }}
                          className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
                          aria-label="Edit provider"
                        >
                          <SettingsIcon className="w-4 h-4" aria-hidden="true" />
                        </button>
                        <button
                          onClick={() => handleDeleteProvider(provider.id)}
                          className="p-2 text-slate-400 hover:text-red-400 hover:bg-slate-800 rounded-lg transition-colors"
                          aria-label="Delete provider"
                        >
                          <Trash2 className="w-4 h-4" aria-hidden="true" />
                        </button>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* API Keys Tab */}
      {activeTab === 'api-keys' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Key className="w-5 h-5 text-blue-500" aria-hidden="true" />
              API Keys
            </h2>
            <button
              onClick={() => {
                setNewApiKey({ provider: 'openai', name: '', api_key: '' })
                setShowApiKeyModal(true)
              }}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg transition-colors flex items-center gap-2"
            >
              <Plus className="w-4 h-4" aria-hidden="true" />
              Add API Key
            </button>
          </div>

          <div className="bg-slate-900/50 backdrop-blur-sm border border-slate-800 rounded-xl p-5">
            <p className="text-slate-400 text-sm mb-4">
              Store your API keys securely. Keys are encrypted and never displayed in full after creation.
            </p>
            {apiKeyLoading ? (
              <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 text-blue-500 animate-spin" aria-label="Loading API keys" />
              </div>
            ) : apiKeys.length === 0 ? (
              <div className="text-center py-12">
                <Key className="w-12 h-12 text-slate-500 mx-auto mb-4" aria-hidden="true" />
                <h3 className="text-lg font-semibold text-white mb-2">No API keys stored</h3>
                <p className="text-slate-400 mb-6 max-w-md mx-auto">
                  Add API keys for your AI providers to enable code generation.
                </p>
                <button
                  onClick={() => {
                    setNewApiKey({ provider: 'openai', name: '', api_key: '' })
                    setShowApiKeyModal(true)
                  }}
                  className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg transition-colors flex items-center gap-2 mx-auto"
                >
                  <Plus className="w-4 h-4" aria-hidden="true" />
                  Add API Key
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {apiKeys.map((key) => (
                  <div key={key.id} className="flex items-center justify-between p-4 bg-slate-950 border border-slate-800 rounded-lg">
                    <div className="flex items-center gap-4">
                      <div className="p-2 bg-blue-500/20 rounded-lg">
                        <Key className="w-5 h-5 text-blue-400" aria-hidden="true" />
                      </div>
                      <div>
                        <h4 className="font-medium text-white">{key.name}</h4>
                        <p className="text-slate-400 text-sm capitalize">{key.provider}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={cn('px-2 py-0.5 text-xs font-medium rounded-full', key.is_active ? 'bg-green-500/20 text-green-400' : 'bg-slate-700 text-slate-400')}>
                        {key.is_active ? 'Active' : 'Inactive'}
                      </span>
                      {key.last_used && (
                        <span className="text-xs text-slate-500">Last used: {key.last_used}</span>
                      )}
                      <button
                        onClick={() => handleDeleteApiKey(key.id)}
                        className="p-2 text-slate-400 hover:text-red-400 hover:bg-slate-800 rounded-lg transition-colors"
                        aria-label="Delete API key"
                      >
                        <Trash2 className="w-4 h-4" aria-hidden="true" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Appearance Tab */}
      {activeTab === 'appearance' && (
        <div className="space-y-6">
          <div className="bg-slate-900/50 backdrop-blur-sm border border-slate-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
              <Palette className="w-5 h-5 text-blue-500" aria-hidden="true" />
              Appearance
            </h2>
            <div className="space-y-6">
              <div>
                <h3 className="text-sm font-medium text-white mb-4">Theme</h3>
                <div className="grid gap-4 sm:grid-cols-3">
                  {['dark', 'light', 'system'].map((theme) => (
                    <button
                      key={theme}
                      className={cn(
                        'p-4 border-2 rounded-lg transition-colors text-left',
                        'border-slate-700 bg-slate-950 hover:border-slate-600'
                      )}
                    >
                      <div className="flex items-center gap-3">
                        <div className={cn(
                          'w-10 h-10 rounded-lg border',
                          theme === 'dark' && 'bg-slate-900 border-slate-700',
                          theme === 'light' && 'bg-white border-slate-300',
                          theme === 'system' && 'bg-gradient-to-r from-slate-900 to-white border-slate-700'
                        )} />
                        <span className="font-medium text-white capitalize">{theme}</span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <h3 className="text-sm font-medium text-white mb-4">Accent Color</h3>
                <div className="flex gap-3 flex-wrap">
                  {['blue', 'purple', 'green', 'orange', 'red', 'pink'].map((color) => (
                    <button
                      key={color}
                      className={cn(
                        'w-10 h-10 rounded-lg border-2 transition-transform hover:scale-110',
                        `bg-${color}-500`
                      )}
                      aria-label={`${color} accent`}
                    />
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Notifications Tab */}
      {activeTab === 'notifications' && (
        <div className="space-y-6">
          <div className="bg-slate-900/50 backdrop-blur-sm border border-slate-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
              <Bell className="w-5 h-5 text-blue-500" aria-hidden="true" />
              Notifications
            </h2>
            <div className="space-y-4">
              {[
                { id: 'email', label: 'Email Notifications', description: 'Receive email updates about project status' },
                { id: 'generation_complete', label: 'Generation Complete', description: 'Notify when project generation finishes' },
                { id: 'generation_failed', label: 'Generation Failed', description: 'Notify when project generation fails' },
                { id: 'weekly_digest', label: 'Weekly Digest', description: 'Receive weekly summary of your projects' },
              ].map((notification) => (
                <div key={notification.id} className="flex items-center justify-between p-4 bg-slate-950 border border-slate-800 rounded-lg">
                  <div>
                    <p className="font-medium text-white">{notification.label}</p>
                    <p className="text-slate-400 text-sm">{notification.description}</p>
                  </div>
                  <button
                    className="relative w-12 h-6 bg-slate-700 rounded-full transition-colors"
                    aria-label={`Toggle ${notification.label}`}
                  >
                    <span className="absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Provider Modal */}
      {showProviderModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={() => { setShowProviderModal(false); setEditingProvider(null); }}>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-white mb-6">{editingProvider ? 'Edit Provider' : 'Add Provider'}</h3>
            <form onSubmit={editingProvider ? handleUpdateProvider : handleCreateProvider} className="space-y-4">
              <div>
                <label htmlFor="provider-name" className="block text-sm font-medium text-slate-300 mb-1.5">
                  Provider Name
                </label>
                <input
                  id="provider-name"
                  type="text"
                  value={editingProvider?.name || newProvider.name}
                  onChange={(e) => {
                    if (editingProvider) {
                      setEditingProvider(prev => prev ? { ...prev, name: e.target.value } : null)
                    } else {
                      setNewProvider(prev => ({ ...prev, name: e.target.value }))
                    }
                  }}
                  className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                  placeholder="e.g., My OpenAI"
                  required
                />
              </div>
              <div>
                <label htmlFor="provider-type" className="block text-sm font-medium text-slate-300 mb-1.5">
                  Provider Type
                </label>
                <select
                  id="provider-type"
                  value={editingProvider?.type || newProvider.type}
                  onChange={(e) => {
                    if (editingProvider) {
                      setEditingProvider(prev => prev ? { ...prev, type: e.target.value, config: {} } : null)
                    } else {
                      setNewProvider(prev => ({ ...prev, type: e.target.value, config: {} }))
                    }
                  }}
                  className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                >
                  {providerTypes.map(({ value, label }) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Configuration</label>
                <div className="space-y-3">
                  {(providerConfigFields[editingProvider?.type || newProvider.type] || []).map((field) => (
                    <div key={field.key}>
                      <label htmlFor={`provider-${field.key}`} className="block text-sm font-medium text-slate-300 mb-1">
                        {field.label}
                      </label>
                      <input
                        id={`provider-${field.key}`}
                        type={field.type}
                        value={((editingProvider?.config || newProvider.config) as Record<string, string>)[field.key] || ''}
                        onChange={(e) => {
                          const config = editingProvider?.config || newProvider.config
                          const newConfig = { ...config, [field.key]: e.target.value }
                          if (editingProvider) {
                            setEditingProvider(prev => prev ? { ...prev, config: newConfig } : null)
                          } else {
                            setNewProvider(prev => ({ ...prev, config: newConfig }))
                          }
                        }}
                        placeholder={field.placeholder}
                        className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                      />
                    </div>
                  ))}
                </div>
              </div>
              {!editingProvider && (
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="provider-active"
                    defaultChecked={true}
                    onChange={(e) => setNewProvider(prev => ({ ...prev, config: { ...prev.config, is_active: e.target.checked } }))}
                    className="w-4 h-4 text-blue-600 border-slate-700 rounded focus:ring-blue-500"
                  />
                  <label htmlFor="provider-active" className="text-sm text-slate-300">Active</label>
                </div>
              )}
              <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => { setShowProviderModal(false); setEditingProvider(null); }}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white font-medium rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg transition-colors flex items-center gap-2"
                >
                  <Save className="w-4 h-4" aria-hidden="true" />
                  {editingProvider ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* API Key Modal */}
      {showApiKeyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={() => setShowApiKeyModal(false)}>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-white mb-6">Add API Key</h3>
            <form onSubmit={handleCreateApiKey} className="space-y-4">
              <div>
                <label htmlFor="api-key-provider" className="block text-sm font-medium text-slate-300 mb-1.5">
                  Provider
                </label>
                <select
                  id="api-key-provider"
                  value={newApiKey.provider}
                  onChange={(e) => setNewApiKey(prev => ({ ...prev, provider: e.target.value }))}
                  className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                >
                  {providerTypes.map(({ value, label }) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="api-key-name" className="block text-sm font-medium text-slate-300 mb-1.5">
                  Key Name
                </label>
                <input
                  id="api-key-name"
                  type="text"
                  value={newApiKey.name}
                  onChange={(e) => setNewApiKey(prev => ({ ...prev, name: e.target.value }))}
                  className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                  placeholder="e.g., Production OpenAI Key"
                  required
                />
              </div>
              <div>
                <label htmlFor="api-key-value" className="block text-sm font-medium text-slate-300 mb-1.5 flex items-center justify-between">
                  API Key
                  <button
                    type="button"
                    onClick={() => setShowApiKeyValue(!showApiKeyValue)}
                    className="text-xs text-slate-400 hover:text-white"
                  >
                    {showApiKeyValue ? 'Hide' : 'Show'}
                  </button>
                </label>
                <input
                  id="api-key-value"
                  type={showApiKeyValue ? 'text' : 'password'}
                  value={newApiKey.api_key}
                  onChange={(e) => setNewApiKey(prev => ({ ...prev, api_key: e.target.value }))}
                  className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all font-mono text-sm"
                  placeholder="sk-... or gsk_... etc."
                  required
                />
              </div>
              <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowApiKeyModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white font-medium rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg transition-colors flex items-center gap-2"
                >
                  <Save className="w-4 h-4" aria-hidden="true" />
                  Add API Key
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}