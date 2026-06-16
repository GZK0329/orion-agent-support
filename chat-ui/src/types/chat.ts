export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  createdAt: number
}

export interface ChatRequest {
  question: string
  session_id: string
}

export interface ChatResponse {
  answer: string
  session_id: string
}
