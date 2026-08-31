import { useEffect, useState } from 'react'
import { Users, KeyRound, CreditCard, TrendingUp, FileText, DollarSign, AlertTriangle } from 'lucide-react'
import { api } from '../api/client.js'
import StatsCard from '../components/StatsCard.jsx'
import Badge from '../components/Badge.jsx'
import DataTable from '../components/DataTable.jsx'

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await api.stats()
        setStats(data)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    fetchStats()
  }, [])

  if (loading) {
    return <div className="flex items-center justify-center h-64 text-muted">Yükleniyor...</div>
  }

  if (error) {
    return <div className="text-danger">Hata: {error}</div>
  }

  const recentAudit = stats?.recent_audit || []
  const planDist = stats?.plan_distribution || {}

  const auditColumns = [
    { id: 'action', header: 'Action', accessorKey: 'action' },
    { id: 'actor', header: 'Actor', accessorKey: 'actor' },
    { id: 'target', header: 'Target', accessorKey: 'target_type', cell: (info) => `${info.getValue()}:${info.row.original.target_id?.slice(0, 8)}` },
    { id: 'time', header: 'Time', accessorKey: 'created_at', cell: (info) => new Date(info.getValue()).toLocaleString() },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <span className="text-sm text-muted">Admin Panel</span>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <StatsCard
          title="Total Users"
          value={stats?.total_users || 0}
          icon={Users}
          subtitle={`${stats?.active_users || 0} active`}
        />
        <StatsCard
          title="Active Licenses"
          value={stats?.active_licenses || 0}
          icon={KeyRound}
          subtitle={`of ${stats?.total_licenses || 0} total`}
        />
        <StatsCard
          title="Active Subscriptions"
          value={stats?.active_subscriptions || 0}
          icon={CreditCard}
          subtitle={`of ${stats?.total_subscriptions || 0} total`}
        />
        <StatsCard
          title="MRR (USD)"
          value={`$${(stats?.mrr_usd || 0).toFixed(2)}`}
          icon={DollarSign}
          accent="success"
        />
        <StatsCard
          title="Plan Distribution"
          value={Object.keys(planDist).length}
          icon={TrendingUp}
          accent="warning"
        />
        <StatsCard
          title="Recent Activity"
          value={recentAudit.length}
          icon={FileText}
          accent="muted"
        />
      </div>

      {/* Plan Distribution + Recent Audit */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Plan Distribution */}
        <div className="bg-card rounded-xl p-5 border border-white/10">
          <h2 className="text-lg font-semibold mb-4">Plan Dağılımı</h2>
          {Object.entries(planDist).length === 0 ? (
            <p className="text-muted text-center py-8">Veri yok</p>
          ) : (
            <div className="space-y-3">
              {Object.entries(planDist).map(([plan, count]) => (
                <div key={plan} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Badge.PlanBadge plan={plan} />
                    <span className="text-sm">{plan}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div
                      className="h-2 bg-accent/10 rounded-full flex-1 max-w-48"
                      style={{ width: '100%' }}
                    >
                      <div
                        className="h-full bg-accent rounded-full"
                        style={{ width: `${(count / Math.max(...Object.values(planDist))) * 100}%` }}
                      />
                    </div>
                    <span className="text-sm font-medium w-12 text-right">{count}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Audit */}
        <div className="bg-card rounded-xl p-5 border border-white/10">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Son Audit Log'lar</h2>
            <a href="/audit" className="text-xs text-accent hover:underline">Tümünü gör</a>
          </div>
          <DataTable
            columns={auditColumns}
            data={recentAudit}
            onRowClick={(row) => console.log(row)}
            emptyMessage="Audit log yok"
          />
        </div>
      </div>
    </div>
  )
}