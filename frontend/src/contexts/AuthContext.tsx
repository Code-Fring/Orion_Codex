import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { api } from '../services/api'
import type { User } from '../types'

interface AuthContextType {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, name: string) => Promise<void>
  logout: () => void
  logoutWithServer: () => Promise<void>
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const initAuth = async () => {
      const token = api.getAccessToken()
      if (token) {
        try {
          await refreshUser()
        } catch {
          api.clearTokens()
        }
      }
      setIsLoading(false)
    }
    initAuth()
  }, [])

  const refreshUser = async () => {
    try {
      const userData = await api.getCurrentUser()
      setUser(userData)
    } catch {
      setUser(null)
      throw new Error('Failed to refresh user')
    }
  }

  const login = async (email: string, password: string) => {
    const { access_token, refresh_token, user: userData } = await api.login(email, password)
    api.setTokens(access_token, refresh_token)
    setUser(userData)
  }

  const register = async (email: string, password: string, name: string) => {
    const { access_token, refresh_token, user: userData } = await api.register(email, password, name)
    api.setTokens(access_token, refresh_token)
    setUser(userData)
  }

  const logout = () => {
    api.clearTokens()
    setUser(null)
  }

  const logoutWithServer = async () => {
    try {
      await api.logout()
    } catch {
      // Ignore errors
    } finally {
      api.clearTokens()
      setUser(null)
    }
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
        logoutWithServer,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}