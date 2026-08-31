import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { CreditCard, Ban, ChevronLeft, ExternalLink } from 'lucide-react'
import { api } from '../api/client.js'
import DataTable from '../components/DataTable.jsx'
import Badge, { PlanBadge, StatusBadge } from '../components/Badge.jsx'

export default function Subscriptions() {
  const navigate = useNavigate()
  const [subs, setSubs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [cancelId, setCancelId] = useState(null)
  const [cancelLoading, setCancelLoading] = useState(false)

  const fetchSubs = async () => {
    setLoading(true)
    try {
      const data = await api.subscriptions({ limit: 100 })
      setSubs(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSubs()
  }, [])

  const columns = [
    { id: 'user_email', header: 'User', accessorKey: 'user_email' },
    { id: 'plan', header: 'Plan', accessorKey: 'plan', cell: (info) => <PlanBadge plan={info.getValue()} /> },
    { id: 'status', header: 'Status', accessorKey: 'status', cell: (info) => <StatusBadge status={info.getValue()} /> },
    { id: 'stripe_customer', header: 'Stripe Customer', accessorKey: 'stripe_customer_id', cell: (info) => info.getValue() ? <span className="font-mono text-xs">{info.getValue().slice(0, 20)}...</span> : '—' },
    { id: 'period_end', header: 'Period End', accessorKey: 'current_period_end', cell: (info) => info.getValue() ? new Date(info.getValue()).toLocaleDateString() : '—' },
  ]

  const handleRowClick = (sub) => {
    navigate(`/subscriptions/${sub.id}`)
  }

  const handleCancel = async (sub) => {
    if (!confirm(`Cancel subscription for ${sub.user_email}?`)) return
    setCancelId(sub.id)
    setCancelLoading(true)
    try {
      await api.cancelSubscription({ subscription_id: sub.id })
      fetchSubs()
    } catch (err) {
      alert(err.message)
    } finally {
      setCancelLoading(false)
      setCancelId(null)
    }
  }

  if (loading) return <div className="flex items-center justify-center h-64 text-muted">Yükleniyor...</div>
  if (error) return <div className="text-danger">Hata: {error}</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Abonelikler</h1>
      </div>

      <DataTable
        columns={columns}
        data={subs}
        onRowClick={handleRowClick}
        emptyMessage="Abonelik bulunamadı"
        actions={(row) => (
          <button
            onClick={(e) => { e.stopPropagation(); handleCancel(row) }}
            disabled={cancelLoading && cancelId === row.id}
            className="px-2 py-1 text-danger hover:bg-danger/10 rounded disabled:opacity-50"
          >
            <Ban size={16} />
          </button>
        )}
      />
    </div>
  )
}

function SubscriptionDetail({ subId }) {
  const navigate = useNavigate()
  const [sub, setSub] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [cancelLoading, setCancelLoading] = useState(false)

  useEffect(() => {
    const fetchDetail = async () => {
      setLoading(true)
      try {
        const data = await api.subscription(subId)
        setSub(data)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    fetchDetail()
  }, [subId])

  const handleCancel = async () => {
    if (!confirm('Cancel this subscription?')) return
    setCancelLoading(true)
    try {
      await api.cancelSubscription({ subscription_id: sub.id })
      navigate('/subscriptions')
    } catch (err) {
      alert(err.message)
    } finally {
      setCancelLoading(false)
    }
  }

  if (loading) return <div className="flex items-center justify-center h-64 text-muted">Yükleniyor...</div>
  if (error) return <div className="text-danger">Hata: {error}</div>
  if (!sub) return <div className="text-danger">Abonelik bulunamadı</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button onClick={() => navigate('/subscriptions')} className="p-2 hover:bg-white/5 rounded-lg transition-colors">
          <ChevronLeft size={20} />
        </button>
        <div>
          <h1 className="text-2xl font-bold">{sub.user_email}</h1>
          <p className="text-sm text-muted">{sub.stripe_subscription_id}</p>
        </div>
        <div className="ml-auto">
          <StatusBadge status={sub.status} />
        </div>
      </div>

      <div className="bg-card rounded-xl p-5 border border-white/10">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <CreditCard size={18} /> Abonelik Detayları
        </h2>
        <div className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-muted">Plan</span>
            <PlanBadge plan={sub.plan} />
          </div>
          <div className="flex justify-between">
            <span className="text-muted">Stripe Customer</span>
            <span className="font-mono text-xs">{sub.stripe_customer_id || '—'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted">Stripe Subscription</span>
            <span className="font-mono text-xs">{sub.stripe_subscription_id || '—'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted">Stripe Price</span>
            <span className="font-mono text-xs">{sub.stripe_price_id || '—'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted">Current Period</span>
            <span>
              {sub.current_period_start ? new Date(sub.current_period_start).toLocaleDateString() : '—'} → {sub.current_period_end ? new Date(sub.current_period_end).toLocaleDateString() : '—'}
            </span>
          </div>
          {sub.cancel_at && (
            <div className="flex justify-between">
              <span className="text-muted">Cancel At</span>
              <span className="text-warning">{new Date(sub.cancel_at).toLocaleDateString()}</span>
            </div>
          )}
          <div className="flex justify-between">
            <span className="text-muted">Created</span>
            <span>{new Date(sub.created_at).toLocaleString()}</span>
          </div>
        </div>

        {sub.status !== 'cancelled' && (
          <button
            onClick={handleCancel}
            disabled={cancelLoading}
            className="mt-4 w-full py-2 bg-danger/20 text-danger hover:bg-danger/30 rounded-lg disabled:opacity-50"
          >
            {cancelLoading ? 'İptal ediliyor...' : 'Aboneliği İptal Et'}
          </button>
        )}
      </div>
    </div>
  )
}

export { SubscriptionDetail }
