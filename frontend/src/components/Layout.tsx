import React from 'react'
import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useProject } from '../contexts/ProjectContext'
import { 
  LayoutDashboard, 
  PlusCircle, 
  Settings, 
  LogOut, 
  Menu, 
  ChevronLeft,
  FolderGit2,
  Code,
} from 'lucide-react'
import { cn } from '../utils/cn'

function Sidebar() {
  const location = useLocation()
  const { projects } = useProject()
  const [isCollapsed, setIsCollapsed] = React.useState(false)
  const [isMobileOpen, setIsMobileOpen] = React.useState(false)

  const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/projects/new', label: 'New Project', icon: PlusCircle },
  ]

  return (
    <>
      {/* Mobile sidebar overlay */}
      {isMobileOpen && (
        <div 
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setIsMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed lg:static z-50 h-full bg-slate-900 border-r border-slate-800 transition-all duration-300 flex flex-col',
          isCollapsed ? 'w-16' : 'w-64',
          isMobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
        aria-label="Sidebar navigation"
      >
        {/* Logo & Toggle */}
        <div className="flex items-center justify-between h-16 px-4 border-b border-slate-800">
          <Link to="/dashboard" className={cn('flex items-center gap-2', isCollapsed && 'justify-center')}>
            <Code className="w-8 h-8 text-blue-500" aria-hidden="true" />
            {!isCollapsed && <span className="font-bold text-lg text-white">Orion Codex</span>}
          </Link>
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className={cn(
              'p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors',
              isCollapsed && 'mx-auto'
            )}
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-expanded={!isCollapsed}
          >
            <ChevronLeft className={cn('w-5 h-5 transition-transform', isCollapsed && 'rotate-180')} aria-hidden="true" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto" aria-label="Main navigation">
          {navItems.map(({ path, label, icon: Icon }) => (
            <Link
              key={path}
              to={path}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 transition-colors',
                location.pathname === path && 'bg-slate-800 text-white',
                isCollapsed && 'justify-center'
              )}
              title={isCollapsed ? label : undefined}
              aria-current={location.pathname === path ? 'page' : undefined}
            >
              <Icon className="w-5 h-5 flex-shrink-0" aria-hidden="true" />
              {!isCollapsed && <span>{label}</span>}
            </Link>
          ))}

          {/* Projects list */}
          {!isCollapsed && projects.length > 0 && (
            <div className="pt-4 mt-4 border-t border-slate-800">
              <h3 className="px-3 text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                Recent Projects
              </h3>
              {projects.slice(0, 5).map((project) => (
                <Link
                  key={project.id}
                  to={`/projects/${project.id}`}
                  className={cn(
                    'flex items-center gap-3 px-3 py-2 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 transition-colors truncate',
                    location.pathname === `/projects/${project.id}` && 'bg-slate-800 text-white'
                  )}
                  title={project.name}
                >
                  <FolderGit2 className="w-5 h-5 flex-shrink-0" aria-hidden="true" />
                  <span className="truncate">{project.name}</span>
                </Link>
              ))}
              {projects.length > 5 && (
                <Link
                  to="/dashboard"
                  className="flex items-center gap-3 px-3 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                >
                  <FolderGit2 className="w-5 h-5 flex-shrink-0" aria-hidden="true" />
                  <span>View all projects</span>
                </Link>
              )}
            </div>
          )}
        </nav>

        {/* Bottom section */}
        <div className="p-4 border-t border-slate-800">
          <Link
            to="/settings"
            className={cn(
              'flex items-center gap-3 px-3 py-2.5 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 transition-colors',
              location.pathname === '/settings' && 'bg-slate-800 text-white',
              isCollapsed && 'justify-center'
            )}
            title={isCollapsed ? 'Settings' : undefined}
          >
            <Settings className="w-5 h-5 flex-shrink-0" aria-hidden="true" />
            {!isCollapsed && <span>Settings</span>}
          </Link>
        </div>
      </aside>
    </>
  )
}

function Header() {
  const { user, logoutWithServer } = useAuth()
  const [showDropdown, setShowDropdown] = React.useState(false)

  return (
    <header className="sticky top-0 z-30 h-16 bg-slate-950/80 backdrop-blur-sm border-b border-slate-800">
      <div className="h-full px-4 lg:px-6 flex items-center justify-between">
        {/* Mobile menu button */}
        <button
          className="lg:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
          aria-label="Open menu"
          onClick={() => document.dispatchEvent(new CustomEvent('toggle-mobile-sidebar'))}
        >
          <Menu className="w-6 h-6" aria-hidden="true" />
        </button>

        {/* Page title */}
        <div className="flex-1 lg:flex-none" />

        {/* User menu */}
        <div className="relative">
          <button
            onClick={() => setShowDropdown(!showDropdown)}
            className="flex items-center gap-3 p-2 rounded-lg hover:bg-slate-800 transition-colors"
            aria-expanded={showDropdown}
            aria-haspopup="true"
          >
            <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white font-medium">
              {user?.name?.[0].toUpperCase() || 'U'}
            </div>
            <div className="hidden md:block text-left">
              <p className="text-sm font-medium text-white">{user?.name || 'User'}</p>
              <p className="text-xs text-slate-400">{user?.email}</p>
            </div>
          </button>

          {showDropdown && (
            <>
              <div 
                className="fixed inset-0 z-10" 
                onClick={() => setShowDropdown(false)} 
                aria-hidden="true"
              />
              <div className="absolute right-0 mt-2 w-48 bg-slate-900 border border-slate-800 rounded-lg shadow-lg py-1 z-20">
                <Link
                  to="/settings"
                  className="flex items-center gap-2 px-4 py-2 text-slate-300 hover:text-white hover:bg-slate-800"
                  onClick={() => setShowDropdown(false)}
                >
                  <Settings className="w-4 h-4" aria-hidden="true" />
                  Settings
                </Link>
                <hr className="my-1 border-slate-800" />
                <button
                  onClick={() => { logoutWithServer(); setShowDropdown(false); }}
                  className="flex items-center gap-2 w-full px-4 py-2 text-slate-300 hover:text-white hover:bg-slate-800 text-left"
                >
                  <LogOut className="w-4 h-4" aria-hidden="true" />
                  Sign out
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  )
}

export default function Layout() {
  const { isLoading, fetchProjects } = useProject()
  const { isAuthenticated } = useAuth()

  React.useEffect(() => {
    if (isAuthenticated) {
      fetchProjects()
    }
  }, [isAuthenticated, fetchProjects])

  // Handle mobile sidebar toggle
  React.useEffect(() => {
    const handleToggle = () => {
      // This will be handled by Sidebar's internal state
    }
    window.addEventListener('toggle-mobile-sidebar', handleToggle)
    return () => window.removeEventListener('toggle-mobile-sidebar', handleToggle)
  }, [])

  return (
    <div className="min-h-screen bg-slate-950 text-white flex">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 lg:ml-0">
        <Header />
        <main className="flex-1 p-4 lg:p-6 overflow-auto">
          {isLoading && (
            <div className="flex items-center justify-center h-64">
              <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" aria-label="Loading" />
            </div>
          )}
          <Outlet />
        </main>
      </div>
    </div>
  )
}