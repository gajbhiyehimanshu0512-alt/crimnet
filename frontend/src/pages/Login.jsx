import { useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { Shield, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'

export default function Login() {
  const { login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await login(username, password)
      toast.success('Login successful')
    } catch (err) {
      toast.error(err.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-surface">
      <div className="card w-full max-w-sm space-y-6">
        <div className="flex flex-col items-center gap-3">
          <Shield className="text-accent" size={40} />
          <div className="text-center">
            <h1 className="text-xl font-bold text-white">CrimNet</h1>
            <p className="text-sm text-slate-400">Intelligence Platform Login</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs text-slate-400 mb-1">Username</label>
            <input
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="Enter username"
              className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-accent"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="Enter password"
              className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-accent"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !username || !password}
            className="w-full bg-accent hover:bg-red-700 disabled:opacity-50 text-white font-medium py-2.5 rounded-lg transition-colors flex items-center justify-center gap-2 text-sm"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : null}
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>

        <div className="text-xs text-slate-500 text-center">
          For authorized personnel only. All access is logged.
        </div>
      </div>
    </div>
  )
}
