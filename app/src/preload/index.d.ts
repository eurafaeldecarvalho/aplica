import type { AplicaApi } from './index'

declare global {
  interface Window {
    aplica: AplicaApi
  }
}

export {}
