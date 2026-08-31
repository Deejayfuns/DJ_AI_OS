import { Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar.jsx'
import Login from './pages/Login.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Users, { UserDetail } from './pages/Users.jsx'
import Licenses, { LicenseDetail } from './pages/Licenses.jsx'
import Subscriptions, { SubscriptionDetail } from './pages/Subscriptions.jsx'
import AuditLog from './pages/AuditLog.jsx'
import Customers, { CustomerDetail } from './pages/Customers.jsx'
import { getToken, clearToken } from './api/client.js'

export default function App() {
  const [token, setTokenState] = useState(getToken())
  const [authed, setAuthed] = useState(false)

  useEffect(() => {
    if (token) {
      setAuthed(true)
    }
  }, [token])

  const handleLogin = (t) => {
    setTokenState(t)
    setAuthed(true)
  }

  const handleLogout = () => {
    clearToken()
    setTokenState('')
    setAuthed(false)
  }

  if (!authed) {
    return <Login onLogin={handleLogin} />
  }

  return (
    <div className="flex h-screen bg-bg">
      <Sidebar onLogout={handleLogout} />
      <main className="flex-1 overflow-auto p-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/users" element={<Users />} />
          <Route path="/users/:userId" element={<UserDetail />} />
          <Route path="/licenses" element={<Licenses />} />
          <Route path="/licenses/:licenseId" element={<LicenseDetail />} />
          <Route path="/subscriptions" element={<Subscriptions />} />
          <Route path="/subscriptions/:subId" element={<SubscriptionDetail />} />
          <Route path="/audit" element={<AuditLog />} />
          <Route path="/customers" element={<Customers />} />
          <Route path="/customers/:customerId" element={<CustomerDetail />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}
