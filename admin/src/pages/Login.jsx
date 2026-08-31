import { useState } from 'react'
import { Shield } from 'lucide-react'
import { api, setToken } from '../api/client.js'

export default function Login({ onLogin }) {
  const [token, setTokenInput] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      // Verify token with server
      const res = await fetch('/admin/api/login', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })
      if (!res.ok) {
        throw new Error('INVALID_TOKEN')
      }
      setToken(token)
      onLogin(token)
    } catch (err) {
      setError(err.message === 'INVALID_TOKEN' ? 'Geçersiz admin token.' : err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg">
      <form onSubmit={handleSubmit} className="bg-card p-8 rounded-xl border border-white/10 w-96">
        <div className="flex flex-col items-center mb-6">
          <div className="w-14 h-14 rounded-xl bg-accent/20 flex items-center justify-center mb-3">
            <Shield className="text-accent" size={28} />
          </div>
          <h1 className="text-xl font-bold">DJ AI OS Admin</h1>
          <p className="text-sm text-muted mt-1">Lisans sunucusu yönetim paneli</p>
        </div>

        <label className="block text-sm text-muted mb-2">Admin Token</label>
        <input
          type="password"
          value={token}
          onChange={(e) => setTokenInput(e.target.value)}
          placeholder="ADMIN_TOKEN"
          className="w-full px-3 py-2 bg-panel border border-white/10 rounded-lg text-text focus:outline-none focus:border-accent"
          autoFocus
        />

        {error && <p className="text-danger text-sm mt-2">{error}</p>}

        <button
          type="submit"
          disabled={loading}
          className="w-full mt-4 py-2.5 bg-accent text-white rounded-lg hover:bg-accent-hover transition-colors disabled:opacity-50"
        >
          {loading ? 'Doğrulanıyor...' : 'GİRİŞ'}
        </button>
      </form>
    </div>
  )
}
