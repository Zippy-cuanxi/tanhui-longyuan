/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<Record<string, unknown>, Record<string, unknown>, unknown>
  export default component
}

declare module 'virtual:demo-snapshot' {
  const snapshot: Record<string, unknown>
  export default snapshot
}

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  readonly VITE_FILE_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
