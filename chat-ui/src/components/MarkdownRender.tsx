import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface Props {
  content: string
}

export default function MarkdownRender({ content }: Props) {
  return (
    <div className="prose prose-sm max-w-none
      prose-p:my-1.5 prose-p:leading-7 prose-p:text-[15px] prose-p:text-[#c5c8d4]
      prose-headings:my-3 prose-headings:font-semibold prose-headings:text-[#e3e5ed]
      prose-ul:my-1.5 prose-ol:my-1.5
      prose-li:my-0.5 prose-li:text-[#c5c8d4]
      prose-code:bg-[#667eea]/10 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded-md prose-code:text-[13px] prose-code:font-mono prose-code:text-[#a5b4fc]
      prose-pre:bg-[#07080e] prose-pre:border prose-pre:border-[#1c1f2e] prose-pre:rounded-xl prose-pre:my-3
      prose-pre:text-[#c5c8d4]
      prose-table:text-[14px] prose-table:text-[#c5c8d4]
      prose-th:bg-[#667eea]/5 prose-th:px-3 prose-th:py-2 prose-th:text-[#e3e5ed] prose-th:border prose-th:border-[#1c1f2e]
      prose-td:px-3 prose-td:py-2 prose-td:border prose-td:border-[#1c1f2e]
      prose-strong:font-semibold prose-strong:text-[#e3e5ed]
      prose-a:text-[#667eea] prose-a:no-underline hover:prose-a:underline
      prose-hr:border-[#1c1f2e]
      prose-blockquote:border-[#667eea]/30 prose-blockquote:text-[#7c8090]
    ">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {content}
      </ReactMarkdown>
    </div>
  )
}
