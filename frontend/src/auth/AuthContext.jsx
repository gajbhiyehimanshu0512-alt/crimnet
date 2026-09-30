import { useState, createContext, useContext, useEffect } from 'react'
import { api, API_BASE } from '../api/client'

const AuthContext = createContext(null)

// "Login failed" tells nobody anything. Spell out which link in the chain
// broke so the operator can fix it instead of guessing.
function describeLoginError(e) {
  const target = API_BASE || window.location.origin
  const detail = e.response?.data?.detail
  if (detail) {
    return Array.isArray(detail) ? detail.map((d) => d.msg || d).join(', ') : String(detail)
  }
  if (e.response) {
    const status = e.response.status
    if (status === 429) return 'Too many attempts — wait a minute, then try again.'
    // A gateway/HTML body (typical of an undeployed Render service) has no
    // `detail`, so the status is the only useful clue.
    if (status >= 500) return `API error ${status} from ${target} — the backend may still be starting or not deployed.`
    return `API responded ${status} at ${target}`
  }
  if (e.code === 'ECONNABORTED') {
    return `Timed out contacting ${target} — a cold Render instance can take ~40s.`
  }
  return `Cannot reach the API at ${target}`
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(() => localStorage.getItem('crimnet_token'))

  useEffect(() => {
    if (token) {
      // Validate token through the shared client so VITE_API_URL applies.
      // A raw fetch('/api/...') would hit *this* origin on Vercel and get
      // index.html back from the SPA rewrite.
      api.get('/api/auth/me')
        .then((res) => setUser(res.data))
        .catch(() => { localStorage.removeItem('crimnet_token'); setToken(null); setUser(null) })
    }
  }, [token])

  const login = async (username, password) => {
    let data
    try {
      const res = await api.post('/api/auth/login', { username, password })
      data = res.data
    } catch (e) {
      throw new Error(describeLoginError(e))
    }
    localStorage.setItem('crimnet_token', data.access_token)
    setToken(data.access_token)
    setUser({ username: data.username, role: data.role })
  }

  const logout = () => {
    localStorage.removeItem('crimnet_token')
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
