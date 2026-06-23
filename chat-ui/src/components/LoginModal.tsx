import { useState } from 'react'
import { Terminal, AlertCircle, Loader2 } from 'lucide-react'
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
      <div className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="fixed left-1/2 top-1/2 z-50 w-80 max-w-[90vw] -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-[#1c1f2e] bg-[#0d0f1a] p-6 shadow-2xl">
        <h2 className="text-base font-semibold text-[#e3e5ed] mb-1">
          <span className="gradient-text">#</span> 管理员登录
        </h2>
        <p className="flex items-center gap-1 text-xs text-[#5c6070] font-mono mb-4">
          <Terminal size={13} />
          管理员身份验证
        </p>
        <form onSubmit={handleSubmit}>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="输入管理员密码"
            autoFocus
            className="w-full rounded-xl border border-[#1c1f2e] bg-[#07080e] px-3 py-2.5 text-sm text-[#c5c8d4] outline-none transition-colors placeholder:text-[#5c6070] focus:border-[#667eea]/40 font-mono"
          />
          {error && <p className="mt-2 flex items-center gap-1 text-xs text-red-400 font-mono"><AlertCircle size={13} />{error}</p>}
          <div className="mt-4 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg px-4 py-2 text-sm text-[#5c6070] transition-colors hover:bg-[#1c1f2e]"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={loading}
              className="rounded-lg px-4 py-2 text-sm text-white gradient-accent transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {loading ? <><Loader2 size={15} className="animate-spin" /> 登录中</> : '登录'}
            </button>
          </div>
        </form>
      </div>
    </>
  )
}
