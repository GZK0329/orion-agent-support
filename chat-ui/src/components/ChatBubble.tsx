import { useRef, useState } from 'react'
import type { Message } from '../types/chat'
import MarkdownRender from './MarkdownRender'

interface Props {
  message: Message
  onFeedback?: (msgId: string, feedback: 'like' | 'dislike', comment?: string) => void
}

function BotAvatar() {
  return (
    <div className="avatar-glow flex h-8 w-8 shrink-0 items-center justify-center rounded-full doubao-gradient text-[12px] font-bold text-white">
      AI
    </div>
  )
}

function ThumbsUpIcon({ filled }: { filled: boolean }) {
  return <span className={`text-base leading-none ${filled ? '' : 'opacity-40'}`}>👍</span>
}

function ThumbsDownIcon({ filled }: { filled: boolean }) {
  return <span className={`text-base leading-none ${filled ? '' : 'opacity-40'}`}>👎</span>
}

export default function ChatBubble({ message, onFeedback }: Props) {
  const isUser = message.role === 'user'
  const [showComment, setShowComment] = useState(false)
  const [commentText, setCommentText] = useState('')
  const inputRef = useRef<HTMLTextAreaElement>(null)

  if (isUser) {
    return (
      <div className="animate-fade-in-up flex justify-end py-1.5">
        <div className="max-w-[78%] rounded-2xl rounded-tr-sm bg-[#f3f4ff] px-4 py-2.5 text-[15px] leading-7 text-gray-800">
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    )
  }

  // 流式输出前不显示空气泡
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
        <p className="mb-1 text-[13px] font-medium text-gray-500">智能助手</p>
        <MarkdownRender content={message.content} />
        <div className="mt-2 flex items-center gap-1">
          <button
            onClick={() => handleClick('like')}
            className={`rounded-md p-1.5 transition-colors ${
              fb === 'like'
                ? 'text-[#6366f1] bg-[#eef2ff]'
                : 'text-gray-400 hover:text-[#6366f1] hover:bg-[#f5f3ff]'
            }`}
            title="有用"
          >
            <ThumbsUpIcon filled={fb === 'like'} />
          </button>
          <button
            onClick={() => handleClick('dislike')}
            className={`rounded-md p-1.5 transition-colors ${
              fb === 'dislike'
                ? 'text-[#6366f1] bg-[#eef2ff]'
                : 'text-gray-400 hover:text-[#6366f1] hover:bg-[#f5f3ff]'
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
              placeholder="请说明不满意的原因（选填）"
              className="w-full resize-none rounded-lg border border-gray-200 bg-white px-3 py-2 text-[13px] text-gray-700 outline-none transition-colors placeholder:text-gray-300 focus:border-[#6366f1]"
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
                className="rounded-md px-3 py-1 text-[12px] text-gray-400 transition-colors hover:text-gray-600"
              >
                取消
              </button>
              <button
                onClick={submitDislike}
                className="rounded-md bg-[#6366f1] px-3 py-1 text-[12px] font-medium text-white transition-colors hover:bg-[#4f46e5]"
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
