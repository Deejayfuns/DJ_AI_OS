import { useEffect, useState } from 'react'
import { Search, Filter, FileText, ChevronDown, ChevronUp } from 'lucide-react'
import { api } from '../api/client.js'
import DataTable from '../components/DataTable.jsx'
import Badge from '../components/Badge.jsx'

const ACTION_HINTS = [
  'license.issued',
  'license.revoked',
  'license.activated',
  'subscription.cancelled',
  'webhook.received',
  'user.created',
]

export default function AuditLog() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [actionFilter, setActionFilter] = useState('')
  const [actorFilter, setActorFilter] = useState('')
  const [targetFilter, setTargetFilter] = useState('')
  const [expanded, setExpanded] = useState(null)

  const fetchLogs = async () => {
    setLoading(true)
    try {
      const params = {}
      if (actionFilter) params.action = actionFilter
      if (actorFilter) params.actor = actorFilter
      if (targetFilter) params.target_type = targetFilter
      const data = await api.audit({ ...params, limit: 200 })
      setLogs(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLogs()
  }, [])

  const columns = [
    { id: 'action', header: 'Action', accessorKey: 'action', cell: (info) => <Badge variant="accent">{info.getValue()}</Badge> },
    { id: 'actor', header: 'Actor', accessorKey: 'actor' },
    { id: 'target_type', header: 'Target', accessorKey: 'target_type', cell: (info) => info.getValue() ? `${info.getValue()}:${info.row.original.target_id?.slice(0, 8)}` : '—' },
    { id: 'ip', header: 'IP', accessorKey: 'ip_address' },
    { id: 'created_at', header: 'Time', accessorKey: 'created_at', cell: (info) => new Date(info.getValue()).toLocaleString() },
  ]

  const toggleExpand = (id) => {
    setExpanded(expanded === id ? null : id)
  }

  if (loading) return <div className="flex items-center justify-center h-64 text-muted">Yükleniyor...</div>
  if (error) return <div className="text-danger">Hata: {error}</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Audit Log</h1>
      </div>

      <div className="bg-card rounded-xl p-4 border border-white/10 flex flex-wrap gap-4">
        <div className="relative flex-1 min-w-48">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" size={18} />
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-panel border border-white/10 rounded-lg text-text focus:outline-none focus:border-accent"
          >
            <option value="">Tüm Aksiyonlar</option>
            {ACTION_HINTS.map(a => <option key={a} value={a}>{a}</option>)}
          </select>
        </div>
        <input
          type="text"
          placeholder="Actor (user_id)"
          value={actorFilter}
          onChange={(e) => setActorFilter(e.target.value)}
          className="px-3 py-2 bg-panel border border-white/10 rounded-lg text-text focus:outline-none focus:border-accent min-w-48"
        />
        <input
          type="text"
          placeholder="Target type"
          value={targetFilter}
          onChange={(e) => setTargetFilter(e.target.value)}
          className="px-3 py-2 bg-panel border border-white/10 rounded-lg text-text focus:outline-none focus:border-accent min-w-48"
        />
        <button
          onClick={fetchLogs}
          className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent-hover"
        >
          Filtrele
        </button>
      </div>

      {logs.length === 0 ? (
        <div className="bg-card rounded-xl p-8 border border-white/10 text-center text-muted">
          <FileText className="mx-auto mb-2" size={32} />
          Audit log bulunamadı
        </div>
      ) : (
        <div className="space-y-2">
          {logs.map((log) => (
            <div key={log.id} className="bg-card rounded-xl border border-white/10 overflow-hidden">
              <button
                onClick={() => toggleExpand(log.id)}
                className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors"
              >
                <div className="flex items-center gap-3 text-left">
                  <Badge variant="accent">{log.action}</Badge>
                  <span className="text-sm text-muted">{log.actor || 'system'}</span>
                  <span className="text-sm">{log.target_type ? `${log.target_type}:${log.target_id?.slice(0, 8)}` : '—'}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-muted">{new Date(log.created_at).toLocaleString()}</span>
                  {expanded === log.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </div>
              </button>
              {expanded === log.id && (
                <div className="px-4 pb-4 border-t border-white/5">
                  <pre className="text-xs text-muted overflow-x-auto bg-panel p-3 rounded-lg mt-3">
                    {JSON.stringify({
                      id: log.id,
                      action: log.action,
                      actor: log.actor,
                      target_type: log.target_type,
                      target_id: log.target_id,
                      ip_address: log.ip_address,
                      details: log.details ? JSON.parse(log.details) : null,
                      created_at: log.created_at,
                    }, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
