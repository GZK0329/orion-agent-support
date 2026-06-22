import type { ChatRequest, ChatResponse } from '../types/chat'

// ---- 同步调用（备用） ----

export async function sendMessage(req: ChatRequest): Promise<ChatResponse> {
  const resp = await fetch('/chat/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}))
    throw new Error(err.detail || `请求失败 (${resp.status})`)
  }
  return resp.json()
}

// ---- 流式调用 ----

export interface StreamCallbacks {
  onToken: (token: string) => void
  onDone: () => void
  onError: (err: Error) => void
}

export async function sendMessageStream(
  req: ChatRequest,
  { onToken, onDone, onError }: StreamCallbacks,
): Promise<void> {
  try {
    const resp = await fetch('/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    })
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.detail || `请求失败 (${resp.status})`)
    }

    const reader = resp.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed.startsWith('data: ')) continue
        try {
          const data = JSON.parse(trimmed.slice(6))
          if (data.token) onToken(data.token)
          else if (data.done) onDone()
          else if (data.error) onError(new Error(data.error))
        } catch { /* malformed sse line, skip */ }
      }
    }
  } catch (err) {
    onError(err instanceof Error ? err : new Error(String(err)))
  }
}

// ---- 历史对话 API ----

// ---- 反馈 API ----

export async function submitFeedback(body: {
  session_id: string
  question: string
  answer: string
  feedback: 'like' | 'dislike'
  comment?: string
}): Promise<void> {
  await fetch('/feedback/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

// ---- 历史对话 ----

export interface SessionItem {
  session_id: string
  title: string
  message_count: number
  created_at: number
}

export interface HistoryMessage {
  type: string
  content: string
}

export async function fetchSessions(clientId?: string): Promise<SessionItem[]> {
  const params = clientId ? `?client_id=${encodeURIComponent(clientId)}` : ''
  const resp = await fetch(`/history/${params}`)
  if (!resp.ok) return []
  return resp.json()
}

export async function fetchSessionMessages(sessionId: string): Promise<HistoryMessage[]> {
  const resp = await fetch(`/history/${sessionId}`)
  if (!resp.ok) return []
  return resp.json()
}

export async function deleteSession(sessionId: string, clientId?: string): Promise<boolean> {
  const params = clientId ? `?client_id=${encodeURIComponent(clientId)}` : ''
  const resp = await fetch(`/history/${sessionId}${params}`, { method: 'DELETE' })
  return resp.ok
}
