// src/utils/sse-client.js

/**
 * 增强型 SSE 客户端
 * - 自动重连（指数退避）
 * - 心跳检测
 * - 断线状态管理
 */
export class SSEClient {
  constructor(url, options = {}) {
    this.url = url
    this.options = {
      maxRetries: 10,
      baseDelay: 1000,
      maxDelay: 30000,
      heartbeatTimeout: 15000,
      ...options
    }

    this.eventSource = null
    this.retryCount = 0
    this.heartbeatTimer = null
    this._destroyed = false

    // 回调
    this.onMessage = null    // (data: any) => void
    this.onError = null      // (error: Event) => void
    this.onStateChange = null // (state: 'connecting' | 'open' | 'closed' | 'reconnecting') => void
  }

  connect() {
    if (this._destroyed) return
    this._setState('connecting')

    this.eventSource = new EventSource(this.url)

    this.eventSource.onopen = () => {
      this.retryCount = 0
      this._setState('open')
      this._resetHeartbeat()
    }

    this.eventSource.onmessage = (event) => {
      this._resetHeartbeat()
      try {
        const data = JSON.parse(event.data)
        this.onMessage?.(data)
      } catch (e) {
        console.warn('SSE 数据解析失败:', e)
      }
    }

    this.eventSource.onerror = () => {
      this.eventSource.close()
      this._clearHeartbeat()

      if (this._destroyed) {
        this._setState('closed')
        return
      }

      this._reconnect()
    }
  }

  _reconnect() {
    if (this.retryCount >= this.options.maxRetries) {
      this._setState('closed')
      this.onError?.(new Error('超过最大重试次数'))
      return
    }

    this._setState('reconnecting')

    // 指数退避
    const delay = Math.min(
      this.options.baseDelay * Math.pow(2, this.retryCount),
      this.options.maxDelay
    )

    this.retryCount++
    console.log(`SSE ${this.retryCount}次重连，等待 ${delay}ms`)

    setTimeout(() => this.connect(), delay)
  }

  _resetHeartbeat() {
    this._clearHeartbeat()
    this.heartbeatTimer = setTimeout(() => {
      console.warn('SSE 心跳超时，重连...')
      this.eventSource?.close()
      this._reconnect()
    }, this.options.heartbeatTimeout)
  }

  _clearHeartbeat() {
    if (this.heartbeatTimer) {
      clearTimeout(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  _setState(state) {
    this.onStateChange?.(state)
  }

  destroy() {
    this._destroyed = true
    this._clearHeartbeat()
    this.eventSource?.close()
    this._setState('closed')
  }
}
