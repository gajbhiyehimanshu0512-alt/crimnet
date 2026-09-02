import { useState, createContext, useContext, useEffect } from 'react'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(() => localStorage.getItem('crimnet_token'))

  useEffect(() => {
    if (token) {
      // Validate token by calling /api/auth/me
      fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then(r => r.ok ? r.json() : Promise.reject())
        .then(data => setUser(data))
        .catch(() => { localStorage.removeItem('crimnet_token'); setToken(null); setUser(null) })
    }
  }, [token])

  const login = async (username, password) => {
    const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Login failed' }))
      throw new Error(err.detail || 'Login failed')
    }
    const data = await res.json()
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
