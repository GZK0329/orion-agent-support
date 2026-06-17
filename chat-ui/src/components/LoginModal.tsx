import { useState } from 'react'
import { adminLogin } from '../api/auth'

interface LoginModalProps {
  open: boolean
  onClose: () => void
  onLogin: (token: string) => void
}

export default function LoginModal({ open, onClose, onLogin }: LoginModalProps) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  if (!open) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const token = await adminLogin(password)
      onLogin(token)
      setPassword('')
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/20" onClick={onClose} />
      <div className="fixed left-1/2 top-1/2 z-50 w-80 max-w-[90vw] -translate-x-1/2 -translate-y-1/2 rounded-2xl bg-white p-6 shadow-xl">
        <h2 className="text-base font-semibold text-[#1f1f1f] mb-4">管理员登录</h2>
        <form onSubmit={handleSubmit}>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="请输入管理员密码"
            autoFocus
            className="w-full rounded-xl border border-[#eeeef0] px-3 py-2.5 text-sm outline-none transition-colors focus:border-[#a5b4fc]"
          />
          {error && <p className="mt-2 text-xs text-red-500">{error}</p>}
          <div className="mt-4 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg px-4 py-2 text-sm text-[#666] transition-colors hover:bg-[#f5f5f5]"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={loading}
              className="rounded-lg px-4 py-2 text-sm text-white doubao-gradient transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {loading ? '登录中…' : '登录'}
            </button>
          </div>
        </form>
      </div>
    </>
  )
}
