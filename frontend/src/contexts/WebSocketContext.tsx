import { createContext, useContext, useEffect, useRef, useState, ReactNode, useCallback } from 'react'
import { api } from '../services/api'
import type { Task, GenerationLog } from '../types'

interface WebSocketMessage {
  type: 'task_update' | 'log' | 'progress' | 'project_status' | 'connected' | 'pong' | 'error'
  project_id: string
  data: any
}

interface WebSocketContextType {
  connect: (projectId: string) => void
  disconnect: () => void
  isConnected: boolean
  lastMessage: WebSocketMessage | null
  onTaskUpdate: (callback: (task: Task) => void) => () => void
  onLog: (callback: (log: GenerationLog) => void) => () => void
  onProgress: (callback: (progress: number, status: string) => void) => () => void
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined)

export function WebSocketProvider({ children }: { children: ReactNode }) {
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const projectIdRef = useRef<string | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 5

  const taskUpdateCallbacks = useRef<Set<(task: Task) => void>>(new Set())
  const logCallbacks = useRef<Set<(log: GenerationLog) => void>>(new Set())
  const progressCallbacks = useRef<Set<(progress: number, status: string) => void>>(new Set())

  const connect = useCallback((projectId: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      if (projectIdRef.current === projectId) return
      disconnect()
    }

    projectIdRef.current = projectId
    const wsUrl = api.getWebSocketUrl(projectId)

    try {
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('WebSocket connected')
        setIsConnected(true)
        reconnectAttempts.current = 0
      }

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          setLastMessage(message)

          switch (message.type) {
            case 'task_update':
              taskUpdateCallbacks.current.forEach(cb => cb(message.data))
              break
            case 'log':
              logCallbacks.current.forEach(cb => cb(message.data))
              break
            case 'progress':
              progressCallbacks.current.forEach(cb => cb(message.data.progress, message.data.status))
              break
            case 'project_status':
              progressCallbacks.current.forEach(cb => cb(message.data.progress, message.data.status))
              break
          }
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err)
        }
      }

      ws.onclose = () => {
        console.log('WebSocket disconnected')
        setIsConnected(false)
        wsRef.current = null

        // Attempt to reconnect
        if (reconnectAttempts.current < maxReconnectAttempts && projectIdRef.current) {
          reconnectAttempts.current++
          const delay = Math.min(1000 * 2 ** reconnectAttempts.current, 30000)
          reconnectTimeoutRef.current = setTimeout(() => {
            if (projectIdRef.current) {
              connect(projectIdRef.current)
            }
          }, delay)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }
    } catch (err) {
      console.error('Failed to create WebSocket:', err)
    }
  }, [])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    projectIdRef.current = null
    setIsConnected(false)
  }, [])

  const onTaskUpdate = useCallback((callback: (task: Task) => void) => {
    taskUpdateCallbacks.current.add(callback)
    return () => taskUpdateCallbacks.current.delete(callback)
  }, [])

  const onLog = useCallback((callback: (log: GenerationLog) => void) => {
    logCallbacks.current.add(callback)
    return () => logCallbacks.current.delete(callback)
  }, [])

  const onProgress = useCallback((callback: (progress: number, status: string) => void) => {
    progressCallbacks.current.add(callback)
    return () => progressCallbacks.current.delete(callback)
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect()
    }
  }, [disconnect])

  return (
    <WebSocketContext.Provider
      value={{
        connect,
        disconnect,
        isConnected,
        lastMessage,
        onTaskUpdate,
        onLog,
        onProgress,
      }}
    >
      {children}
    </WebSocketContext.Provider>
  )
}

export function useWebSocket() {
  const context = useContext(WebSocketContext)
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider')
  }
  return context
}