import { useState, useRef, useEffect, useCallback } from 'react'
import ChatBubble from './components/ChatBubble'
import ChatInput from './components/ChatInput'
import { sendMessageStream, fetchSessions, deleteSession as apiDeleteSession } from './api/chat'
import type { Message } from './types/chat'

// ---- 工具 ----

const SESSION_KEY = 'chat_session_id'
const CONV_KEY = 'chat_conversations'

function getSessionId(): string {
  const sid = localStorage.getItem(SESSION_KEY) || crypto.randomUUID()
  localStorage.setItem(SESSION_KEY, sid)
  return sid
}
function resetSession(): string {
  const sid = crypto.randomUUID()
  localStorage.setItem(SESSION_KEY, sid)
  return sid
}

function loadMessages(sid: string): Message[] {
  try {
    const raw = localStorage.getItem(`chat_msgs_${sid}`)
    if (raw) return JSON.parse(raw)
  } catch { /* */ }
  return []
}
function saveMessages(sid: string, msgs: Message[]) {
  try { localStorage.setItem(`chat_msgs_${sid}`, JSON.stringify(msgs)) } catch { /* */ }
}

interface ConvInfo {
  id: string
  sessionId: string
  title: string
  createdAt: number
  msgCount: number
}
function loadConvos(): ConvInfo[] {
  try {
    const raw = localStorage.getItem(CONV_KEY)
    if (raw) return JSON.parse(raw)
  } catch { /* */ }
  return []
}
function saveConvos(list: ConvInfo[]) {
  try { localStorage.setItem(CONV_KEY, JSON.stringify(list)) } catch { /* */ }
}

function pickTitle(msgs: Message[]): string {
  const u = msgs.find((m) => m.role === 'user')
  if (!u) return '新对话'
  const t = u.content.trim()
  return t.length > 28 ? t.slice(0, 28) + '…' : t
}

// ---- 组件 ----

export default function App() {
  const [sessionId, setSessionId] = useState(getSessionId)
  const [messages, setMessages] = useState<Message[]>(() => {
    const msgs = loadMessages(sessionId)
    return msgs.length > 0 ? msgs : []
  })
  const [loading, setLoading] = useState(false)
  const [histOpen, setHistOpen] = useState(false)
  const [convos, setConvos] = useState<ConvInfo[]>(loadConvos)
  const scrollRef = useRef<HTMLDivElement>(null)

  // 首次挂载：从后端同步会话列表（补充 localStorage 里没有的数据）
  useEffect(() => {
    fetchSessions().then((list) => {
      if (list.length === 0) return
      setConvos((prev) => {
        const merged = [...prev]
        for (const s of list) {
          if (!merged.find((c) => c.sessionId === s.session_id)) {
            merged.push({
              id: s.session_id,
              sessionId: s.session_id,
              title: s.title,
              createdAt: s.created_at,
              msgCount: s.message_count,
            })
          }
        }
        merged.sort((a, b) => b.createdAt - a.createdAt)
        saveConvos(merged)
        return merged
      })
    }).catch(() => {})
  }, [])

  const persist = useCallback((sid: string, msgs: Message[]) => {
    saveMessages(sid, msgs)
  }, [])

  const scrollToBottom = useCallback(() => {
    setTimeout(() => {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
    }, 50)
  }, [])

  useEffect(scrollToBottom, [messages, loading])

  const enterSession = useCallback((sid: string) => {
    setSessionId(sid)
    setMessages(loadMessages(sid))
    setHistOpen(false)
  }, [])

  const handleSend = async (text: string) => {
    const userMsg: Message = {
      id: crypto.randomUUID(), role: 'user', content: text, createdAt: Date.now(),
    }
    const aiMsg: Message = {
      id: crypto.randomUUID(), role: 'assistant', content: '', createdAt: Date.now(),
    }
    const next = [...messages, userMsg, aiMsg]
    setMessages(next)
    persist(sessionId, next)
    setLoading(true)

    // 流式累积
    let fullAnswer = ''

    await sendMessageStream(
      { question: text, session_id: sessionId },
      {
        onToken: (token) => {
          fullAnswer += token
          setMessages((prev) => {
            const copy = [...prev]
            const last = copy[copy.length - 1]
            if (last && last.role === 'assistant') {
              copy[copy.length - 1] = { ...last, content: fullAnswer }
            }
            return copy
          })
        },
        onDone: () => {
          const done = [...messages, userMsg, { ...aiMsg, content: fullAnswer }]
          setMessages(done)
          persist(sessionId, done)
          setLoading(false)
        },
        onError: (err) => {
          const fallback = [
            ...messages, userMsg,
            { ...aiMsg, content: `抱歉，出错了：${err.message}` },
          ]
          setMessages(fallback)
          persist(sessionId, fallback)
          setLoading(false)
        },
      },
    )
  }

  const saveCurrentConv = useCallback(() => {
    if (messages.length === 0) return
    setConvos((prev) => {
      const list = prev.filter((c) => c.sessionId !== sessionId)
      const conv: ConvInfo = {
        id: sessionId, sessionId, title: pickTitle(messages),
        createdAt: Date.now(), msgCount: messages.length,
      }
      const next = [conv, ...list]
      saveConvos(next)
      return next
    })
  }, [messages, sessionId])

  const handleNewChat = () => {
    saveCurrentConv()
    const newSid = resetSession()
    enterSession(newSid)
  }

  const handleSelectConv = (conv: ConvInfo) => {
    saveCurrentConv()
    enterSession(conv.sessionId)
  }

  const handleDeleteConv = (e: React.MouseEvent, sid: string) => {
    e.stopPropagation()
    setConvos((prev) => {
      const list = prev.filter((c) => c.sessionId !== sid)
      saveConvos(list)
      return list
    })
    localStorage.removeItem(`chat_msgs_${sid}`)
    apiDeleteSession(sid).catch(() => {})
  }

  const hasMessages = messages.length > 0 && messages.some((m) => m.content)

  return (
    <div className="relative flex h-screen flex-col bg-[#fafafa]">
      {histOpen && <div className="fixed inset-0 z-20 bg-black/20" onClick={() => setHistOpen(false)} />}

      <aside className={`fixed left-0 top-0 z-30 flex h-full w-72 flex-col bg-white shadow-xl transition-transform duration-300 ${
        histOpen ? 'translate-x-0' : '-translate-x-full'
      }`}>
        <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
          <span className="text-sm font-semibold text-gray-800">历史对话</span>
          <button className="text-gray-400 hover:text-gray-600" onClick={() => setHistOpen(false)}>
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
              <path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z" />
            </svg>
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-3">
          {convos.length === 0 && (
            <p className="mt-8 text-center text-sm text-gray-400">暂无历史对话</p>
          )}
          {convos.map((conv) => (
            <div
              key={conv.sessionId}
              onClick={() => handleSelectConv(conv)}
              className={`group mb-1 cursor-pointer rounded-xl px-3 py-2.5 transition-colors hover:bg-gray-100 ${
                conv.sessionId === sessionId ? 'bg-gray-100' : ''
              }`}
            >
              <p className="truncate text-sm font-medium text-gray-800">{conv.title}</p>
              <p className="mt-0.5 text-xs text-gray-400">
                {new Date(conv.createdAt).toLocaleString('zh-CN', {
                  month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit',
                })} · {conv.msgCount} 条
              </p>
              <button
                onClick={(e) => handleDeleteConv(e, conv.sessionId)}
                className="mt-1 text-xs text-gray-400 opacity-0 transition-opacity group-hover:opacity-100 hover:text-red-500"
              >
                删除
              </button>
            </div>
          ))}
        </div>
      </aside>

      <header className="flex items-center justify-between border-b border-[#eeeef0] bg-white px-5 py-3">
        <div className="flex items-center gap-2.5">
          <button className="text-gray-500 hover:text-gray-700" onClick={() => setHistOpen(true)}>
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-5 w-5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
            </svg>
          </button>
          <div className="flex h-8 w-8 items-center justify-center rounded-xl doubao-gradient text-[12px] font-bold text-white shadow-sm">AI</div>
          <span className="text-[15px] font-semibold text-[#1f1f1f]">智能客服助手</span>
        </div>
        <button onClick={handleNewChat} className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm text-[#666] transition-colors hover:bg-[#f5f5f5]">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
            <path d="M10.362 1.093a.75.75 0 0 0-.724 0L2.523 5.018 10 9.143l7.477-4.125-7.115-3.925ZM18 6.443l-7.25 4v8.25l6.862-3.786A.75.75 0 0 0 18 14.25V6.443ZM9.25 18.693v-8.25l-7.25-4v7.807a.75.75 0 0 0 .388.657l6.862 3.786Z" />
          </svg>
          新对话
        </button>
      </header>

      <div ref={scrollRef} className="chat-scroll flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl px-5 py-3">
          {!hasMessages && !loading && (
            <div className="flex flex-col items-center justify-center py-24 text-gray-400">
              <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-2xl doubao-gradient text-lg font-bold text-white shadow-sm">AI</div>
              <p className="text-sm">有什么可以帮助您的？</p>
            </div>
          )}
          {messages.map((msg, i) => (
            <ChatBubble key={msg.id || i} message={msg} />
          ))}
          {loading && !messages.some((m) => m.role === 'assistant' && m.content) && (
            <div className="animate-fade-in flex gap-3 py-1.5">
              <div className="avatar-glow flex h-8 w-8 shrink-0 items-center justify-center rounded-full doubao-gradient text-[12px] font-bold text-white">AI</div>
              <div className="flex items-center gap-1.5 pt-2">
                <span className="inline-block h-2 w-2 rounded-full bg-[#a5b4fc] animate-pulse-dot" />
                <span className="inline-block h-2 w-2 rounded-full bg-[#a5b4fc] animate-pulse-dot" style={{ animationDelay: '0.15s' }} />
                <span className="inline-block h-2 w-2 rounded-full bg-[#a5b4fc] animate-pulse-dot" style={{ animationDelay: '0.3s' }} />
              </div>
            </div>
          )}
        </div>
      </div>

      <ChatInput onSend={handleSend} disabled={loading} />
    </div>
  )
}
