/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_WS_URL: string
  readonly VITE_APP_VERSION: string
  readonly VITE_DEBUG: string
  readonly VITE_APP_NAME: string
  readonly VITE_SENTRY_DSN?: string
  readonly VITE_ENABLE_ANALYTICS?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

// Vite plugin types
declare module 'virtual:*' {
  export * from '*'
}

// Worker types for production
interface Worker {
  postMessage(message: any, transfer?: Transferable[]): void
  terminate(): void
  addEventListener(type: string, listener: EventListenerOrEventListenerObject, options?: boolean | AddEventListenerOptions): void
  removeEventListener(type: string, listener: EventListenerOrEventListenerObject, options?: boolean | AddEventListenerOptions): void
}

declare var Worker: {
  prototype: Worker
  new(scriptURL: string | URL, options?: WorkerOptions): Worker
}

// Global types for Monaco Editor
declare global {
  interface Window {
    monaco?: any
    require?: any
  }
}