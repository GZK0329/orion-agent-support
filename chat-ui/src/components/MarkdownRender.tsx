import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface Props {
  content: string
}

export default function MarkdownRender({ content }: Props) {
  return (
    <div className="prose prose-sm max-w-none
      prose-p:my-1.5 prose-p:leading-7 prose-p:text-[15px] prose-p:text-gray-800
      prose-headings:my-3 prose-headings:font-semibold
      prose-ul:my-1.5 prose-ol:my-1.5
      prose-li:my-0.5
      prose-code:bg-[#f3f4ff] prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded-md prose-code:text-[13px] prose-code:font-normal prose-code:text-primary-600
      prose-pre:bg-[#f8f9ff] prose-pre:border prose-pre:border-[#e8eaff] prose-pre:rounded-xl prose-pre:my-3
      prose-pre:text-gray-800
      prose-table:text-[14px]
      prose-th:bg-[#f5f6ff] prose-th:px-3 prose-th:py-2
      prose-td:px-3 prose-td:py-2
      prose-strong:font-semibold
    ">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {content}
      </ReactMarkdown>
    </div>
  )
}
