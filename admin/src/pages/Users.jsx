import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Search, User, KeyRound, CreditCard, Shield, ChevronLeft, MoreVertical, Ban, UserCheck } from 'lucide-react'
import { api } from '../api/client.js'
import DataTable from '../components/DataTable.jsx'
import Badge, { PlanBadge, StatusBadge } from '../components/Badge.jsx'

export default function Users() {
  const navigate = useNavigate()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const limit = 20

  const fetchUsers = async () => {
    setLoading(true)
    try {
      const data = await api.users({ search, limit, offset: (page - 1) * limit })
      setUsers(data.items || data)
      setTotal(data.total || data.length)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchUsers()
  }, [search, page])

  const columns = [
    { id: 'email', header: 'Email', accessorKey: 'email' },
    { id: 'name', header: 'Name', accessorKey: 'name' },
    { id: 'plan', header: 'Plan', accessorKey: 'plan', cell: (info) => info.getValue() ? <PlanBadge plan={info.getValue()} /> : <span className="text-muted">—</span> },
    { id: 'created_at', header: 'Created', accessorKey: 'created_at', cell: (info) => new Date(info.getValue()).toLocaleDateString() },
    { id: 'active', header: 'Status', accessorKey: 'is_active', cell: (info) => <StatusBadge status={info.getValue() ? 'active' : 'cancelled'} /> },
  ]

  const handleRowClick = (user) => {
    navigate(`/users/${user.id}`)
  }

  const toggleActive = async (user) => {
    try {
      await api.setUserActive(user.id, !user.is_active)
      fetchUsers()
    } catch (err) {
      alert(err.message)
    }
  }

  if (loading) return <div className="flex items-center justify-center h-64 text-muted">Yükleniyor...</div>
  if (error) return <div className="text-danger">Hata: {error}</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Kullanıcılar</h1>
      </div>

      <div className="bg-card rounded-xl p-4 border border-white/10 flex gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" size={18} />
          <input
            type="text"
            placeholder="Email veya isim ile ara..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            className="w-full pl-10 pr-4 py-2 bg-panel border border-white/10 rounded-lg text-text focus:outline-none focus:border-accent"
          />
        </div>
      </div>

      <DataTable
        columns={columns}
        data={users}
        onRowClick={handleRowClick}
        emptyMessage="Kullanıcı bulunamadı"
      />

      {total > limit && (
        <div className="flex items-center justify-between text-sm text-muted">
          <span>Sayfa {page} / {Math.ceil(total / limit)}</span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1 bg-panel border border-white/10 rounded-lg hover:bg-white/5 disabled:opacity-50"
            >
              Önceki
            </button>
            <button
              onClick={() => setPage(p => Math.min(Math.ceil(total / limit), p + 1))}
              disabled={page >= Math.ceil(total / limit)}
              className="px-3 py-1 bg-panel border border-white/10 rounded-lg hover:bg-white/5 disabled:opacity-50"
            >
              Sonraki
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function UserDetail({ userId }) {
  const navigate = useNavigate()
  const [user, setUser] = useState(null)
  const [licenses, setLicenses] = useState([])
  const [subscription, setSubscription] = useState(null)
  const [machines, setMachines] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchDetail = async () => {
      setLoading(true)
      try {
        const [userData, licensesData, subData, machinesData] = await Promise.all([
          api.user(userId),
          api.userLicenses(userId),
          api.userSubscription(userId),
          api.userMachines(userId),
        ])
        setUser(userData)
        setLicenses(licensesData)
        setSubscription(subData)
        setMachines(machinesData)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    fetchDetail()
  }, [userId])

  if (loading) return <div className="flex items-center justify-center h-64 text-muted">Yükleniyor...</div>
  if (error) return <div className="text-danger">Hata: {error}</div>
  if (!user) return <div className="text-danger">Kullanıcı bulunamadı</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button onClick={() => navigate('/users')} className="p-2 hover:bg-white/5 rounded-lg transition-colors">
          <ChevronLeft size={20} />
        </button>
        <div>
          <h1 className="text-2xl font-bold">{user.email}</h1>
          <p className="text-sm text-muted">{user.name || 'İsimsiz'}</p>
        </div>
        <div className="flex items-center gap-2 ml-auto">
          <StatusBadge status={user.is_active ? 'active' : 'cancelled'} />
          {user.is_admin && <Shield className="text-accent" size={16} />}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Licenses */}
        <div className="bg-card rounded-xl p-5 border border-white/10">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <KeyRound size={18} /> Lisanslar ({licenses.length})
          </h2>
          {licenses.length === 0 ? (
            <p className="text-muted text-center py-8">Lisans yok</p>
          ) : (
            <div className="space-y-2">
              {licenses.map(lic => (
                <div key={lic.id} className="flex items-center justify-between p-3 bg-panel rounded-lg">
                  <div className="flex items-center gap-3">
                    <PlanBadge plan={lic.plan} />
                    <div>
                      <p className="font-mono text-sm">{lic.key}</p>
                      <p className="text-xs text-muted">Bitiş: {lic.expires_at ? new Date(lic.expires_at).toLocaleDateString() : 'Süresiz'}</p>
                    </div>
                  </div>
                  <StatusBadge status={lic.is_active ? 'active' : 'cancelled'} />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Subscription */}
        <div className="bg-card rounded-xl p-5 border border-white/10">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <CreditCard size={18} /> Abonelik
          </h2>
          {subscription ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <PlanBadge plan={subscription.plan} />
                <StatusBadge status={subscription.status} />
              </div>
              <div className="text-sm text-muted space-y-1">
                <p>Stripe Customer: <span className="font-mono">{subscription.stripe_customer_id?.slice(0, 20)}...</span></p>
                <p>Period: {subscription.current_period_start ? new Date(subscription.current_period_start).toLocaleDateString() : '—'} → {subscription.current_period_end ? new Date(subscription.current_period_end).toLocaleDateString() : '—'}</p>
                {subscription.cancel_at && <p className="text-warning">İptal tarihi: {new Date(subscription.cancel_at).toLocaleDateString()}</p>}
              </div>
            </div>
          ) : (
            <p className="text-muted text-center py-8">Abonelik yok</p>
          )}
        </div>

        {/* Machines */}
        <div className="bg-card rounded-xl p-5 border border-white/10">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <User size={18} /> Cihazlar ({machines.length})
          </h2>
          {machines.length === 0 ? (
            <p className="text-muted text-center py-8">Cihaz yok</p>
          ) : (
            <div className="space-y-2">
              {machines.map(m => (
                <div key={m.id} className="flex items-center justify-between p-3 bg-panel rounded-lg">
                  <div>
                    <p className="font-mono text-sm">{m.machine_id}</p>
                    <p className="text-xs text-muted">Aktivasyon: {new Date(m.activated_at).toLocaleString()}</p>
                  </div>
                  <StatusBadge status={m.is_active ? 'active' : 'cancelled'} />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="bg-card rounded-xl p-5 border border-white/10 flex items-center justify-between">
        <div>
          <h3 className="font-semibold">Hesap İşlemleri</h3>
          <p className="text-sm text-muted">Kullanıcıyı aktif/pasif yap</p>
        </div>
        <button
          onClick={() => toggleActive(user)}
          className={`px-4 py-2 rounded-lg font-medium ${user.is_active ? 'bg-danger/20 text-danger hover:bg-danger/30' : 'bg-success/20 text-success hover:bg-success/30'}`}
        >
          {user.is_active ? 'Pasif Yap' : 'Aktif Yap'}
        </button>
      </div>
    </div>
  )
}

export { UserDetail }