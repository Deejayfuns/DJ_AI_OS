import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Search, KeyRound, Ban, Plus, ChevronLeft, Monitor, RotateCcw, ArrowUpRight, Settings, Download } from 'lucide-react'
import { api } from '../api/client.js'
import DataTable from '../components/DataTable.jsx'
import Badge, { PlanBadge, StatusBadge } from '../components/Badge.jsx'

const PLANS = ['PRO', 'DJ_ARCHIVE', 'STUDIO', 'ENTERPRISE']

export default function Licenses() {
  const navigate = useNavigate()
  const [licenses, setLicenses] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [showIssue, setShowIssue] = useState(false)
  const [issueEmail, setIssueEmail] = useState('')
  const [issuePlan, setIssuePlan] = useState('PRO')
  const [issueMonths, setIssueMonths] = useState(12)
  const [issueMachineId, setIssueMachineId] = useState('')
  const [issueExpiry, setIssueExpiry] = useState('')
  const [issueUpdatesUntil, setIssueUpdatesUntil] = useState('')
  const [issueMaxTracks, setIssueMaxTracks] = useState('')
  const [issueLoading, setIssueLoading] = useState(false)
  const [issueError, setIssueError] = useState(null)
  const [issueUserId, setIssueUserId] = useState(null)
  const [issueUserEmail, setIssueUserEmail] = useState(null)
  const [issueUserFound, setIssueUserFound] = useState(false)

  const fetchLicenses = async () => {
    setLoading(true)
    try {
      const data = await api.licenses({ user_email: search || undefined, limit: 100 })
      setLicenses(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLicenses()
  }, [])

  const columns = [
    { id: 'key', header: 'Key', accessorKey: 'key' },
    { id: 'plan', header: 'Plan', accessorKey: 'plan', cell: (info) => <PlanBadge plan={info.getValue()} /> },
    { id: 'user_email', header: 'User', accessorKey: 'user_email' },
    { id: 'issued_at', header: 'Issued', accessorKey: 'issued_at', cell: (info) => new Date(info.getValue()).toLocaleDateString() },
    { id: 'expires_at', header: 'Expires', accessorKey: 'expires_at', cell: (info) => new Date(info.getValue()).toLocaleDateString() },
    { id: 'active', header: 'Status', accessorKey: 'is_active', cell: (info) => <StatusBadge status={info.getValue() ? 'active' : 'cancelled'} /> },
  ]

  const handleRowClick = (lic) => {
    navigate(`/licenses/${lic.id}`)
  }

  const handleUserLookup = async (e) => {
    e.preventDefault()
    if (!issueEmail.trim()) return
    try {
      const users = await api.users({ search: issueEmail, limit: 1 })
      if (users.length === 0) {
        setIssueUserFound(false)
        setIssueUserId(null)
        setIssueUserEmail(null)
      } else {
        const user = users[0]
        setIssueUserId(user.id)
        setIssueUserEmail(user.email)
        setIssueUserFound(true)
      }
    } catch (err) {
      setIssueError(err.message)
      setIssueUserFound(false)
    }
  }

  const handleIssue = async (e) => {
    e.preventDefault()
    if (!issueUserId) {
      setIssueError('Önce geçerli bir email ile kullanıcı bulun')
      return
    }
    setIssueLoading(true)
    setIssueError(null)
    try {
      const res = await api.issueLicense({
        user_id: issueUserId,
        plan: issuePlan,
        months: issueMonths,
        machine_id: issueMachineId || undefined,
        expiry: issueExpiry || undefined,
        updates_until: issueUpdatesUntil || undefined,
        max_tracks: issueMaxTracks ? parseInt(issueMaxTracks) : undefined,
      })
      if (res.ok && res.license) {
        await api.downloadLicense(res.license.id)
      }
      setShowIssue(false)
      setIssueEmail('')
      setIssueUserId(null)
      setIssueUserEmail(null)
      setIssueUserFound(false)
      setIssueMachineId('')
      setIssueExpiry('')
      setIssueUpdatesUntil('')
      setIssueMaxTracks('')
      fetchLicenses()
    } catch (err) {
      setIssueError(err.message)
    } finally {
      setIssueLoading(false)
    }
  }

  const handleRevoke = async (lic) => {
    if (!confirm(`Revoke license ${lic.key}?`)) return
    try {
      await api.revokeLicense({ license_id: lic.id })
      fetchLicenses()
    } catch (err) {
      alert(err.message)
    }
  }

  if (loading) return <div className="flex items-center justify-center h-64 text-muted">Yükleniyor...</div>
  if (error) return <div className="text-danger">Hata: {error}</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Lisanslar</h1>
        <button
          onClick={() => setShowIssue(true)}
          className="flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent-hover transition-colors"
        >
          <Plus size={16} /> Yeni Lisans
        </button>
      </div>

      <div className="bg-card rounded-xl p-4 border border-white/10 flex gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" size={18} />
          <input
            type="text"
            placeholder="User email ile filtrele..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-panel border border-white/10 rounded-lg text-text focus:outline-none focus:border-accent"
          />
        </div>
        <button
          onClick={fetchLicenses}
          className="px-4 py-2 bg-panel border border-white/10 rounded-lg hover:bg-white/5"
        >
          Ara
        </button>
      </div>

      {showIssue && (
        <div className="bg-card rounded-xl p-5 border border-white/10">
          <h2 className="text-lg font-semibold mb-4">Yeni Lisans Ver</h2>
          <form onSubmit={handleIssue} className="space-y-4">
            {/* User Lookup by Email */}
            <div>
              <label className="block text-sm text-muted mb-2">Müşteri Email</label>
              <div className="flex gap-2">
                <input
                  type="email"
                  value={issueEmail}
                  onChange={(e) => { setIssueEmail(e.target.value); setIssueUserFound(false); setIssueUserId(null); }}
                  placeholder="ozertest@example.com"
                  required
                  className="flex-1 px-3 py-2 bg-panel border border-white/10 rounded-lg text-text focus:outline-none focus:border-accent"
                />
                <button
                  type="button"
                  onClick={handleUserLookup}
                  className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent-hover flex items-center"
                >
                  Bul
                </button>
              </div>
              {issueUserFound && (
                <p className="text-success text-sm mt-1">Kullanıcı bulundu: {issueUserEmail} ({issueUserId.slice(0, 8)}...)</p>
              )}
              {!issueUserFound && issueEmail && (
                <p className="text-warning text-sm mt-1">Kullanıcı bulunamadı - önce müşteri oluşturun</p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-muted mb-2">Plan</label>
                <select
                  value={issuePlan}
                  onChange={(e) => setIssuePlan(e.target.value)}
                  className="w-full px-3 py-2 bg-panel border border-white/10 rounded-lg text-text focus:outline-none focus:border-accent"
                >
                  {PLANS.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm text-muted mb-2">Süre (ay)</label>
                <input
                  type="number"
                  min="1"
                  max="60"
                  value={issueMonths}
                  onChange={(e) => setIssueMonths(parseInt(e.target.value))}
                  className="w-full px-3 py-2 bg-panel border border-white/10 rounded-lg text-text focus:outline-none focus:border-accent"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-muted mb-2">Machine ID (opsiyonel)</label>
                <input
                  type="text"
                  value={issueMachineId}
                  onChange={(e) => setIssueMachineId(e.target.value)}
                  placeholder="Cihaz kimliği (SHA256 hex)"
                  className="w-full px-3 py-2 bg-panel border border-white/10 rounded-lg text-text focus:outline-none focus:border-accent"
                />
              </div>
              <div>
                <label className="block text-sm text-muted mb-2">Bitiş Tarihi (YYYY-MM-DD, opsiyonel)</label>
                <input
                  type="date"
                  value={issueExpiry}
                  onChange={(e) => setIssueExpiry(e.target.value)}
                  className="w-full px-3 py-2 bg-panel border border-white/10 rounded-lg text-text focus:outline-none focus:border-accent"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-muted mb-2">Güncelleme Sonu (YYYY-MM-DD, opsiyonel)</label>
                <input
                  type="date"
                  value={issueUpdatesUntil}
                  onChange={(e) => setIssueUpdatesUntil(e.target.value)}
                  className="w-full px-3 py-2 bg-panel border border-white/10 rounded-lg text-text focus:outline-none focus:border-accent"
                />
              </div>
              <div>
                <label className="block text-sm text-muted mb-2">Max Tracks (opsiyonel)</label>
                <input
                  type="number"
                  min="1"
                  max="100000"
                  value={issueMaxTracks}
                  onChange={(e) => setIssueMaxTracks(e.target.value)}
                  placeholder="Plan varsayılanı"
                  className="w-full px-3 py-2 bg-panel border border-white/10 rounded-lg text-text focus:outline-none focus:border-accent"
                />
              </div>
            </div>
            {issueError && <p className="text-danger text-sm">{issueError}</p>}
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={issueLoading || !issueUserId}
                className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent-hover disabled:opacity-50"
              >
                {issueLoading ? 'Veriliyor...' : 'Lisans Ver ve İndir'}
              </button>
              <button
                type="button"
                onClick={() => { setShowIssue(false); setIssueEmail(''); setIssueUserId(null); setIssueUserFound(false); setIssueMachineId(''); setIssueExpiry(''); setIssueUpdatesUntil(''); setIssueMaxTracks(''); }}
                className="px-4 py-2 bg-panel border border-white/10 rounded-lg hover:bg-white/5"
              >
                İptal
              </button>
            </div>
          </form>
        </div>
      )}

      <DataTable
        columns={columns}
        data={licenses}
        onRowClick={handleRowClick}
        emptyMessage="Lisans bulunamadı"
        actions={(row) => (
          <button
            onClick={(e) => { e.stopPropagation(); handleRevoke(row) }}
            className="px-2 py-1 text-danger hover:bg-danger/10 rounded"
          >
            <Ban size={16} />
          </button>
        )}
      />
    </div>
  )
}

function LicenseDetail({ licenseId }) {
  const navigate = useNavigate()
  const [lic, setLic] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchDetail = async () => {
      setLoading(true)
      try {
        const data = await api.license(licenseId)
        setLic(data)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    fetchDetail()
  }, [licenseId])

  if (loading) return <div className="flex items-center justify-center h-64 text-muted">Yükleniyor...</div>
  if (error) return <div className="text-danger">Hata: {error}</div>
  if (!lic) return <div className="text-danger">Lisans bulunamadı</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button onClick={() => navigate('/licenses')} className="p-2 hover:bg-white/5 rounded-lg transition-colors">
          <ChevronLeft size={20} />
        </button>
        <div>
          <h1 className="text-2xl font-bold font-mono">{lic.key}</h1>
          <p className="text-sm text-muted">{lic.user_email}</p>
        </div>
        <div className="ml-auto">
          <StatusBadge status={lic.is_active ? 'active' : 'cancelled'} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Details */}
        <div className="bg-card rounded-xl p-5 border border-white/10">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <KeyRound size={18} /> Lisans Detayları
          </h2>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-muted">Plan</span>
              <PlanBadge plan={lic.plan} />
            </div>
            <div className="flex justify-between">
              <span className="text-muted">Max Tracks</span>
              <span>{lic.max_tracks}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted">Issued At</span>
              <span>{new Date(lic.issued_at).toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted">Expires At</span>
              <span>{new Date(lic.expires_at).toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted">Updates Until</span>
              <span>{lic.updates_until ? new Date(lic.updates_until).toLocaleString() : '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted">Signature Nonce</span>
              <span className="font-mono text-xs">{lic.signature_nonce?.slice(0, 16)}...</span>
            </div>
          </div>

          <div className="mt-4 flex gap-2">
            <button
              onClick={async () => {
                try {
                  await api.downloadLicense(lic.id)
                } catch (err) {
                  alert(err.message)
                }
              }}
              className="flex-1 py-2 bg-accent text-white hover:bg-accent-hover rounded-lg flex items-center justify-center gap-2"
            >
              <Download size={16} /> Lisans Dosyasını İndir
            </button>
            <button
              onClick={async () => {
                if (!confirm(`Revoke license ${lic.key}?`)) return
                try {
                  await api.revokeLicense({ license_id: lic.id })
                  navigate('/licenses')
                } catch (err) {
                  alert(err.message)
                }
              }}
              className="flex-1 py-2 bg-danger/20 text-danger hover:bg-danger/30 rounded-lg"
            >
              Lisansı İptal Et
            </button>
          </div>
        </div>

        {/* Machines */}
        <div className="bg-card rounded-xl p-5 border border-white/10">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Monitor size={18} /> Aktif Cihazlar ({lic.machine_activations?.length || 0})
          </h2>
          {!lic.machine_activations || lic.machine_activations.length === 0 ? (
            <p className="text-muted text-center py-8">Cihaz yok</p>
          ) : (
            <div className="space-y-2">
              {lic.machine_activations.map(m => (
                <div key={m.id} className="flex items-center justify-between p-3 bg-panel rounded-lg">
                  <div>
                    <p className="font-mono text-sm">{m.machine_id}</p>
                    <p className="text-xs text-muted">Aktivasyon: {new Date(m.activated_at).toLocaleString()}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge status={m.is_active ? 'active' : 'cancelled'} />
                    {m.is_active && (
                      <button
                        onClick={async (e) => {
                          e.stopPropagation()
                          if (!confirm(`Deactivate machine ${m.machine_id}?`)) return
                          try {
                            await api.deactivateMachine(lic.id, m.machine_id)
                            const updated = await api.license(licenseId)
                            setLic(updated)
                          } catch (err) {
                            alert(err.message)
                          }
                        }}
                        className="px-2 py-1 text-warning hover:bg-warning/10 rounded text-xs"
                        title="Deactivate machine"
                      >
                        <Monitor size={14} className="opacity-50" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* License Actions */}
        <div className="bg-card rounded-xl p-5 border border-white/10">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Settings size={18} /> Lisans İşlemleri
          </h2>
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 bg-panel rounded-lg">
              <div>
                <p className="font-medium">Lisans Yenile</p>
                <p className="text-xs text-muted">Süre uzat + güncelleme penceresi yenile</p>
              </div>
              <button
                onClick={async () => {
                  const months = prompt('Kaç ay uzatılsın? (varsayılan: 12)', '12')
                  if (!months) return
                  try {
                    const res = await api.renewLicense(lic.id, parseInt(months))
                    setLic(res.license)
                  } catch (err) {
                    alert(err.message)
                  }
                }}
                className="px-3 py-1.5 bg-accent text-white rounded-lg hover:bg-accent-hover transition-colors text-sm"
              >
                <RotateCcw size={14} className="mr-1" /> Yenile
              </button>
            </div>
            <div className="flex items-center justify-between p-3 bg-panel rounded-lg">
              <div>
                <p className="font-medium">Plan Değiştir</p>
                <p className="text-xs text-muted">Farklı plana yükselt/düşür</p>
              </div>
              <button
                onClick={async () => {
                  const newPlan = prompt(`Yeni plan (mevcut: ${lic.plan}):`, 'PRO')
                  if (!newPlan || !PLANS.includes(newPlan)) return
                  try {
                    const res = await api.changeLicensePlan(lic.id, newPlan)
                    setLic(res.license)
                  } catch (err) {
                    alert(err.message)
                  }
                }}
                className="px-3 py-1.5 bg-accent text-white rounded-lg hover:bg-accent-hover transition-colors text-sm"
              >
                <ArrowUpRight size={14} className="mr-1" /> Plan Değiştir
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export { LicenseDetail }
