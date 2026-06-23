import { useState, useRef, useEffect, type KeyboardEvent } from 'react'

interface Props {
  onSend: (text: string) => void
  disabled: boolean
}

export default function ChatInput({ onSend, disabled }: Props) {
  const [text, setText] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (!disabled && textareaRef.current) {
      textareaRef.current.focus()
    }
  }, [disabled])

  const handleSend = () => {
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setText('')
  }

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const canSend = text.trim().length > 0 && !disabled

  return (
    <div className="mx-auto w-full max-w-3xl px-3 sm:px-4 pb-2 pt-2">
      <div className="input-glow flex items-end gap-2 rounded-2xl border border-[#1c1f2e] bg-[#0d0f1a] px-3 sm:px-4 py-2.5 transition-all">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入问题，查询调度接口文档..."
          rows={1}
          disabled={disabled}
          className="max-h-28 flex-1 resize-none bg-transparent text-[15px] leading-7 text-[#c5c8d4] outline-none placeholder:text-[#5c6070] disabled:opacity-50 font-mono"
        />
        <button
          onClick={handleSend}
          disabled={!canSend}
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg gradient-accent text-white transition-all hover:shadow-lg hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-20"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="currentColor"
            className="h-4 w-4"
          >
            <path d="M3.478 2.404a.75.75 0 0 0-.926.941l2.432 7.905H13.5a.75.75 0 0 1 0 1.5H4.984l-2.432 7.905a.75.75 0 0 0 .926.94 60.519 60.519 0 0 0 18.445-8.986.75.75 0 0 0 0-1.218A60.517 60.517 0 0 0 3.478 2.404Z" />
          </svg>
        </button>
      </div>
      <p className="mt-2 text-center text-[11px] sm:text-[12px] text-[#5c6070] font-mono">
        Enter 发送 · Shift+Enter 换行
      </p>
    </div>
  )
}
