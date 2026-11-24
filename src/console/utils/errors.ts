import { MockApiError } from '@/console/api/mock'

export interface ConsoleErrorState {
  message: string
  requestId: string
}

export function toErrorState(error: unknown, fallback = '加载失败，请稍后重试'): ConsoleErrorState {
  if (error instanceof MockApiError) {
    return { message: error.message, requestId: error.requestId }
  }
  if (error instanceof Error && error.message) {
    return { message: error.message, requestId: '' }
  }
  return { message: fallback, requestId: '' }
}
