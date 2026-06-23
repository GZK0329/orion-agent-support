import { useState, useEffect, useRef } from 'react'
import { Upload, RefreshCw, Trash2, Info } from 'lucide-react'
import { fetchDocuments, uploadDocument, deleteDocument, reindexDocuments } from '../api/documents'
import type { FileItem } from '../api/documents'

interface Props {
  open: boolean
  onClose: () => void
  adminToken: string
}

export default function DocManager({ open, onClose, adminToken }: Props) {
  const [files, setFiles] = useState<FileItem[]>([])
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [msg, setMsg] = useState('')
  const [reindexing, setReindexing] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const load = async () => {
    const list = await fetchDocuments(adminToken)
    setFiles(list)
  }

  useEffect(() => {
    if (open) load()
  }, [open])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setProgress(0)
    setMsg('')
    try {
      const text = await uploadDocument(file, adminToken, setProgress)
      setMsg(text)
      await load()
    } catch (err) {
      setMsg(`失败：${err instanceof Error ? err.message : ''}`)
    } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  const handleReindex = async () => {
    setReindexing(true)
    setMsg('')
    try {
      const text = await reindexDocuments(adminToken)
      setMsg(text)
      await load()
    } catch (err) {
      setMsg(`重建失败：${err instanceof Error ? err.message : ''}`)
    } finally {
      setReindexing(false)
    }
  }

  const handleDelete = async (f: FileItem) => {
    const ok = await deleteDocument(f.filename, adminToken)
    if (ok) {
      setMsg(`已删除 ${f.filename}`)
      await load()
    } else {
      setMsg('删除失败')
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={onClose}>
      <div className="mx-4 w-full max-w-lg rounded-2xl border border-[#1c1f2e] bg-[#0d0f1a] shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-[#1c1f2e] px-5 py-4">
          <h2 className="text-base font-semibold text-[#e3e5ed]">
            <span className="gradient-text">#</span> 知识库文档管理
          </h2>
          <button onClick={onClose} className="text-[#5c6070] hover:text-[#9ca0b0]">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
              <path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z" />
            </svg>
          </button>
        </div>

        <div className="px-5 py-4">
          <label className="flex cursor-pointer items-center justify-center gap-2 rounded-xl border-2 border-dashed border-[#1c1f2e] px-4 py-6 text-sm text-[#5c6070] transition-colors hover:border-[#667eea]/30 hover:text-[#667eea]">
            <Upload size={20} />
            上传文件（支持 .txt .md .pdf 格式）
            <input ref={inputRef} type="file" accept=".txt,.md,.pdf" className="hidden" onChange={handleUpload} />
          </label>
          {uploading && (
            <div className="mt-3">
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-[#1c1f2e]">
                <div className="h-full rounded-full gradient-accent transition-all" style={{ width: `${progress}%` }} />
              </div>
              <p className="mt-1 text-xs text-[#5c6070] font-mono">上传中... {progress}%</p>
            </div>
          )}
          {msg && <p className="mt-2 flex items-center gap-1 text-sm text-[#9ca0b0] font-mono"><Info size={14} />{msg}</p>}
        </div>

        <div className="border-t border-[#1c1f2e] px-5 py-3">
          <button
            onClick={handleReindex}
            disabled={reindexing}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-[#1c1f2e] px-4 py-2.5 text-sm text-[#5c6070] transition-colors hover:bg-[#1c1f2e] disabled:opacity-50 font-mono"
          >
            <RefreshCw size={16} className={reindexing ? 'animate-spin' : ''} />
            重建索引
          </button>
        </div>

        <div className="max-h-60 overflow-y-auto border-t border-[#1c1f2e] px-5 py-3">
          {files.length === 0 && <p className="text-center text-sm text-[#5c6070] font-mono">暂无文档</p>}
          {files.map((f) => (
            <div key={f.filename} className="group flex items-center justify-between rounded-lg px-2 py-2 hover:bg-[#1c1f2e]/50">
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm text-[#c5c8d4] font-mono">{f.filename}</p>
                <p className="text-xs text-[#5c6070] font-mono">{(f.size / 1024).toFixed(1)} KB</p>
              </div>
              <button onClick={() => handleDelete(f)} className="ml-2 shrink-0 flex items-center gap-0.5 text-xs text-[#5c6070] opacity-0 transition-opacity group-hover:opacity-100 hover:text-red-400 font-mono">
                <Trash2 size={12} /> 删除
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
