import type { Message } from '../types/chat'
import MarkdownRender from './MarkdownRender'

interface Props {
  message: Message
}

function BotAvatar() {
  return (
    <div className="avatar-glow flex h-8 w-8 shrink-0 items-center justify-center rounded-full doubao-gradient text-[12px] font-bold text-white">
      AI
    </div>
  )
}

export default function ChatBubble({ message }: Props) {
  const isUser = message.role === 'user'

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

  return (
    <div className="animate-fade-in-up flex gap-3 py-1.5">
      <BotAvatar />
      <div className="min-w-0 flex-1 pt-1">
        <p className="mb-1 text-[13px] font-medium text-gray-500">智能助手</p>
        <MarkdownRender content={message.content} />
      </div>
    </div>
  )
}
