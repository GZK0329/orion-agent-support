import { useRef, useState } from 'react'
import { Bot } from 'lucide-react'
import type { Message } from '../types/chat'
import MarkdownRender from './MarkdownRender'

interface Props {
  message: Message
  onFeedback?: (msgId: string, feedback: 'like' | 'dislike', comment?: string) => void
}

function BotAvatar() {
  return (
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg gradient-accent text-[12px] font-bold text-white glow-sm">
      AI
    </div>
  )
}

function ThumbsUpIcon({ filled }: { filled: boolean }) {
  return <span className={`text-base leading-none ${filled ? '' : 'opacity-30'}`}>👍</span>
}

function ThumbsDownIcon({ filled }: { filled: boolean }) {
  return <span className={`text-base leading-none ${filled ? '' : 'opacity-30'}`}>👎</span>
}

export default function ChatBubble({ message, onFeedback }: Props) {
  const isUser = message.role === 'user'
  const [showComment, setShowComment] = useState(false)
  const [commentText, setCommentText] = useState('')
  const inputRef = useRef<HTMLTextAreaElement>(null)

  if (isUser) {
    return (
      <div className="animate-fade-in-up flex justify-end py-1.5">
        <div className="max-w-[78%] rounded-2xl rounded-tr-sm bg-[#667eea]/10 border border-[#667eea]/20 px-4 py-2.5 text-[15px] leading-7 text-[#c5c8d4]">
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    )
  }

  if (!message.content) return null

  const fb = message.feedback

  const handleClick = (value: 'like' | 'dislike') => {
    if (fb === value) return
    if (value === 'like') {
      setShowComment(false)
      onFeedback?.(message.id, 'like')
    } else {
      setShowComment(true)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }

  const submitDislike = () => {
    setShowComment(false)
    onFeedback?.(message.id, 'dislike', commentText || undefined)
    setCommentText('')
  }

  const cancelDislike = () => {
    setShowComment(false)
    setCommentText('')
  }

  return (
    <div className="animate-fade-in-up flex gap-3 py-1.5">
      <BotAvatar />
      <div className="min-w-0 flex-1 pt-1">
        <p className="mb-1 flex items-center gap-1 text-[13px] font-mono text-[#667eea]">
          <Bot size={15} className="text-[#667eea]" />
          助手
        </p>
        <div className="prose prose-sm prose-invert prose-dark max-w-none">
          <MarkdownRender content={message.content} />
        </div>
        <div className="mt-2 flex items-center gap-1">
          <button
            onClick={() => handleClick('like')}
            className={`rounded-md p-1.5 transition-colors ${
              fb === 'like'
                ? 'text-[#667eea] bg-[#667eea]/15'
                : 'text-[#5c6070] hover:text-[#667eea] hover:bg-[#667eea]/10'
            }`}
            title="有用"
          >
            <ThumbsUpIcon filled={fb === 'like'} />
          </button>
          <button
            onClick={() => handleClick('dislike')}
            className={`rounded-md p-1.5 transition-colors ${
              fb === 'dislike'
                ? 'text-[#667eea] bg-[#667eea]/15'
                : 'text-[#5c6070] hover:text-[#667eea] hover:bg-[#667eea]/10'
            }`}
            title="没用"
          >
            <ThumbsDownIcon filled={fb === 'dislike'} />
          </button>
        </div>
        {showComment && (
          <div className="mt-2 flex flex-col gap-1.5">
            <textarea
              ref={inputRef}
              value={commentText}
              onChange={(e) => setCommentText(e.target.value.slice(0, 500))}
              placeholder="说明不满意的原因（选填）"
              className="w-full resize-none rounded-lg border border-[#1c1f2e] bg-[#0d0f1a] px-3 py-2 text-[13px] text-[#c5c8d4] outline-none transition-colors placeholder:text-[#5c6070] focus:border-[#667eea]/40"
              rows={2}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  submitDislike()
                }
              }}
            />
            <div className="flex items-center justify-end gap-2">
              <button
                onClick={cancelDislike}
                className="rounded-md px-3 py-1 text-[12px] text-[#5c6070] transition-colors hover:text-[#9ca0b0]"
              >
                取消
              </button>
              <button
                onClick={submitDislike}
                className="rounded-md bg-[#667eea] px-3 py-1 text-[12px] font-medium text-white transition-colors hover:bg-[#4f6bff]"
              >
                提交
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
