import { useState, useEffect, useRef } from 'react'
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
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/20" onClick={onClose}>
      <div className="mx-4 w-full max-w-lg rounded-2xl bg-white shadow-xl" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
          <h2 className="text-base font-semibold text-gray-800">知识库文档管理</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
              <path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z" />
            </svg>
          </button>
        </div>

        {/* Upload area */}
        <div className="px-5 py-4">
          <label className="flex cursor-pointer items-center justify-center gap-2 rounded-xl border-2 border-dashed border-gray-300 px-4 py-6 text-sm text-gray-500 transition-colors hover:border-primary-400 hover:text-primary-600">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
              <path d="M9.25 13.25a.75.75 0 0 0 1.5 0V4.636l2.955 3.129a.75.75 0 0 0 1.09-1.03l-4.25-4.5a.75.75 0 0 0-1.09 0l-4.25 4.5a.75.75 0 1 0 1.09 1.03L9.25 4.636V13.25Z" />
              <path d="M3.5 12.75a.75.75 0 0 0-1.5 0v2.5A2.75 2.75 0 0 0 4.75 18h10.5a2.75 2.75 0 0 0 2.75-2.75v-2.5a.75.75 0 0 0-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5Z" />
            </svg>
            点击上传文档（.txt / .md / .pdf）
            <input ref={inputRef} type="file" accept=".txt,.md,.pdf" className="hidden" onChange={handleUpload} />
          </label>
          {uploading && (
            <div className="mt-3">
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-200">
                <div className="h-full rounded-full doubao-gradient transition-all" style={{ width: `${progress}%` }} />
              </div>
              <p className="mt-1 text-xs text-gray-400">上传中 {progress}%</p>
            </div>
          )}
          {msg && <p className="mt-2 text-sm text-gray-600">{msg}</p>}
        </div>

        {/* Reindex */}
        <div className="border-t border-gray-100 px-5 py-3">
          <button
            onClick={handleReindex}
            disabled={reindexing}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-[#eeeef0] px-4 py-2.5 text-sm text-[#666] transition-colors hover:bg-[#f5f5f5] disabled:opacity-50"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className={`h-4 w-4 ${reindexing ? 'animate-spin' : ''}`}>
              <path fillRule="evenodd" d="M15.312 11.424a5.5 5.5 0 0 1-9.201 2.466l-.312-.311h2.433a.75.75 0 0 0 0-1.5H3.989a.75.75 0 0 0-.75.75v4.242a.75.75 0 0 0 1.5 0v-2.43l.31.31a7 7 0 0 0 11.712-3.138.75.75 0 0 0-1.449-.39Zm1.23-3.723a.75.75 0 0 0 .219-.53V2.929a.75.75 0 0 0-1.5 0V5.36l-.31-.31A7 7 0 0 0 3.239 8.188a.75.75 0 1 0 1.448.388A5.5 5.5 0 0 1 13.89 6.11l.311.31h-2.432a.75.75 0 0 0 0 1.5h4.243a.75.75 0 0 0 .53-.219Z" clipRule="evenodd" />
            </svg>
            {reindexing ? '向量化中…' : '重新向量化（基于当前文档重建知识库）'}
          </button>
        </div>

        {/* File list */}
        <div className="max-h-60 overflow-y-auto border-t border-gray-100 px-5 py-3">
          {files.length === 0 && <p className="text-center text-sm text-gray-400">暂无文档</p>}
          {files.map((f) => (
            <div key={f.filename} className="group flex items-center justify-between rounded-lg px-2 py-2 hover:bg-gray-50">
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm text-gray-700">{f.filename}</p>
                <p className="text-xs text-gray-400">{(f.size / 1024).toFixed(1)} KB</p>
              </div>
              <button onClick={() => handleDelete(f)} className="ml-2 shrink-0 text-xs text-gray-400 opacity-0 transition-opacity group-hover:opacity-100 hover:text-red-500">
                删除
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
