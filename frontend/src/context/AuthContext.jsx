import { createContext, useContext, useState, useEffect } from 'react'
import api from '../api/axios'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(localStorage.getItem('token'))
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (token) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`
      // Verifica token valido
      api.get('/api/v1/dashboard/summary/')
        .then(() => {
          setUser({ authenticated: true })
        })
        .catch(() => {
          logout()
        })
        .finally(() => {
          setLoading(false)
        })
    } else {
      setLoading(false)
    }
  }, [token])

  const login = async (username, password) => {
    try {
      const response = await api.post('/api/v1/auth/token/', {
        username,
        password
      })
      const { access, refresh } = response.data
      localStorage.setItem('token', access)
      localStorage.setItem('refreshToken', refresh)
      setToken(access)
      api.defaults.headers.common['Authorization'] = `Bearer ${access}`
      setUser({ authenticated: true, username })
      return { success: true }
    } catch (error) {
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Errore di autenticazione' 
      }
    }
  }

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('refreshToken')
    setToken(null)
    setUser(null)
    delete api.defaults.headers.common['Authorization']
  }

  const refreshToken = async () => {
    try {
      const refresh = localStorage.getItem('refreshToken')
      if (!refresh) throw new Error('No refresh token')
      
      const response = await api.post('/api/v1/auth/token/refresh/', {
        refresh
      })
      const { access } = response.data
      localStorage.setItem('token', access)
      setToken(access)
      api.defaults.headers.common['Authorization'] = `Bearer ${access}`
      return true
    } catch {
      logout()
      return false
    }
  }

  return (
    <AuthContext.Provider value={{ user, token, login, logout, refreshToken, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
