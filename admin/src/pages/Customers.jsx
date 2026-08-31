import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Search, User, KeyRound, Monitor, ChevronLeft, Plus, Ban, RotateCcw, ArrowUpRight, Download, Settings, Building2
} from 'lucide-react'
import { api } from '../api/client.js'
import DataTable from '../components/DataTable.jsx'
import Badge, { PlanBadge, StatusBadge } from '../components/Badge.jsx'

const PLANS = ['PRO', 'DJ_ARCHIVE', 'STUDIO', 'ENTERPRISE']

export default function Customers() {
  const navigate = useNavigate()
  const [customers, setCustomers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const limit = 20

  const [showCreate, setShowCreate] = useState(false)
  const [createName, setCreateName] = useState('')
  const [createEmail, setCreateEmail] = useState('')
  const [createCompany, setCreateCompany] = useState('')
  const [createPlan, setCreatePlan] = useState('PRO')
  const [createMachineId, setCreateMachineId] = useState('')
  const [createExpiry, setCreateExpiry] = useState('')
  const [createUpdatesUntil, setCreateUpdatesUntil] = useState('')
  const [createMaxTracks, setCreateMaxTracks] = useState('')
  const [createLoading, setCreateLoading] = useState(false)
  const [createError, setCreateError] = useState(null)

  const fetchCustomers = async () => {
    setLoading(true)
    try {
      const data = await api.customers({ search, limit, offset: (page - 1) * limit })
      setCustomers(data.items || data)
      setTotal(data.total || data.length)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCustomers()
  }, [search, page])

  const columns = [
    { id: 'name', header: 'Customer', accessorKey: 'name' },
    { id: 'email', header: 'Email', accessorKey: 'email' },
    { id: 'company_name', header: 'Company', accessorKey: 'company_name', cell: (info) => info.getValue() || <span className="text-muted">—</span> },
    { id: 'plan', header: 'Plan', accessorKey: 'plan', cell: (info) => info.getValue() ? <PlanBadge plan={info.getValue()} /> : <span className="text-muted">—</span> },
    { id: 'machine', header: 'Machine', accessorKey: 'machine', cell: (info) => info.getValue() ? <span className="font-mono text-xs">{info.getValue().slice(0, 12)}...</span> : <span className="text-muted">—</span> },
    { id: 'status', header: 'Status', accessorKey: 'is_active', cell: (info) => <StatusBadge status={info.getValue() ? 'active' : 'cancelled'} /> },
    { id: 'expiry', header: 'Expiry', accessorKey: 'expiry', cell: (info) => info.getValue() ? new Date(info.getValue()).toLocaleDateString() : <span className="text-muted">—</span> },
    { id: 'updates', header: 'Updates', accessorKey: 'updates_until', cell: (info) => info.getValue() ? new Date(info.getValue()).toLocaleDateString() : <span className="text-muted">—</span> },
  ]

  const handleRowClick = (customer) => {
    navigate(`/customers/${customer.id}`)
  }

  const handleCreate = async (e) => {
    e.preventDefault()
    setCreateLoading(true)
    setCreateError(null)
    try {
      // 1. Create customer
      const customerRes = await api.createCustomer({
        name: createName,
        email: createEmail,
        company_name: createCompany || undefined,
      })
      const customerId = customerRes.customer.id

      // 2. Issue license if plan selected
      if (createPlan) {
        const licenseRes = await api.issueLicense({
          user_id: customerId,
          plan: createPlan,
          months: 12,
          machine_id: createMachineId || undefined,
          expiry: createExpiry || undefined,
          updates_until: createUpdatesUntil || undefined,
          max_tracks: createMaxTracks ? parseInt(createMaxTracks) : undefined,
        })

        // 3. Download license file
        if (licenseRes.ok && licenseRes.license) {
          await api.downloadLicense(licenseRes.license.id)
        }
      }

      setShowCreate(false)
      setCreateName('')
      setCreateEmail('')
      setCreateCompany('')
      setCreatePlan('PRO')
      setCreateMachineId('')
      setCreateExpiry('')
      setCreateUpdatesUntil('')
      setCreateMaxTracks('')
      fetchCustomers()
    } catch (err) {
      setCreateError(err.message)
    } finally {
      setCreateLoading(false)
    }
  }

  if (loading) return <div className="flex items-center justify-center h-64 text-muted">Yükleniyor...</div>
  if (error) return <div className="text-danger">Hata: {error}</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Müşteriler</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent-hover transition-colors"
        >
          <Plus size={16} /> Yeni Müşteri
        </button>
      </div>

      <div className="bg-card rounded-xl p-4 border border-white/10 flex gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" size={18} />
          <input
            type="text"
            placeholder="Email, isim veya şirket ile ara..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            className="w-full pl-10 pr-4 py-2 bg-panel border border-white/10 rounded-lg text-text focus:outline-none focus:border-accent"
          />
        </div>
      </div>

      {showCreate && (
        <div className="bg-card rounded-xl p-5 border border-white/10">
          <h2 className="text-lg font-semibold mb-4">Yeni Müşteri Oluştur + Lisans Ver</h2>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-muted mb-2">Ad Soyad</label>
                <input
                  type="text"
                  value={createName}
                  onChange={(e) => setCreateName(e.target.value)}
                  placeholder="Örn: Özer Test"
                  required
                  className="w-full px-3 py-2 bg-panel border border-white/10 rounded-lg text-text focus:outline-none focus:border-accent"
                />
              </div>
              <div>
                <label className="block text-sm text-muted mb-2">Email</label>
                <input
                  type="email"
                  value={createEmail}
                  onChange={(e) => setCreateEmail(e.target.value)}
                  placeholder="ozertest@example.com"
                  required
                  className="w-full px-3 py-2 bg-panel border border-white/10 rounded-lg text-text focus:outline-none focus:border-accent"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm text-muted mb-2">Şirket (opsiyonel)</label>
              <input
                type="text"
                value={createCompany}
                onChange={(e) => setCreateCompany(e.target.value)}
                placeholder="Şirket adı"
                className="w-full px-3 py-2 bg-panel border border-white/10 rounded-lg text-text focus:outline-none focus:border-accent"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-muted mb-2">Plan</label>
                <select
                  value={createPlan}
                  onChange={(e) => setCreatePlan(e.target.value)}
                  className="w-full px-3 py-2 bg-panel border border-white/10 rounded-lg text-text focus:outline-none focus:border-accent"
                >
                  {PLANS.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm text-muted mb-2">Machine ID (opsiyonel)</label>
                <input
                  type="text"
                  value={createMachineId}
                  onChange={(e) => setCreateMachineId(e.target.value)}
                  placeholder="Cihaz kimliği (SHA256 hex)"
                  className="w-full px-3 py-2 bg-panel border border-white/10 rounded-lg text-text focus:outline-none focus:border-accent"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-muted mb-2">Bitiş Tarihi (YYYY-MM-DD, opsiyonel)</label>
                <input
                  type="date"
                  value={createExpiry}
                  onChange={(e) => setCreateExpiry(e.target.value)}
                  className="w-full px-3 py-2 bg-panel border border-white/10 rounded-lg text-text focus:outline-none focus:border-accent"
                />
              </div>
              <div>
                <label className="block text-sm text-muted mb-2">Güncelleme Sonu (YYYY-MM-DD, opsiyonel)</label>
                <input
                  type="date"
                  value={createUpdatesUntil}
                  onChange={(e) => setCreateUpdatesUntil(e.target.value)}
                  className="w-full px-3 py-2 bg-panel border border-white/10 rounded-lg text-text focus:outline-none focus:border-accent"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm text-muted mb-2">Max Tracks (opsiyonel, plan varsayılanı kullanılır)</label>
              <input
                type="number"
                min="1"
                max="100000"
                value={createMaxTracks}
                onChange={(e) => setCreateMaxTracks(e.target.value)}
                placeholder="Plan varsayılanı"
                className="w-full px-3 py-2 bg-panel border border-white/10 rounded-lg text-text focus:outline-none focus:border-accent"
              />
            </div>
            {createError && <p className="text-danger text-sm">{createError}</p>}
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={createLoading}
                className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent-hover disabled:opacity-50"
              >
                {createLoading ? 'Oluşturuluyor...' : 'Müşteri Oluştur ve Lisans İndir'}
              </button>
              <button
                type="button"
                onClick={() => setShowCreate(false)}
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
        data={customers}
        onRowClick={handleRowClick}
        emptyMessage="Müşteri bulunamadı"
        actions={(row) => (
          <div className="flex items-center gap-1">
            <button
              onClick={() => navigate(`/customers/${row.id}`)}
              className="px-2 py-1 text-muted hover:text-text hover:bg-white/10 rounded"
              title="Detay"
            >
              <User size={14} />
            </button>
            {row.license_id && (
              <button
                onClick={async () => {
                  try {
                    await api.downloadLicense(row.license_id)
                  } catch (err) {
                    alert(err.message)
                  }
                }}
                className="px-2 py-1 text-accent hover:bg-accent/10 rounded"
                title="Lisans İndir"
              >
                <Download size={14} />
              </button>
            )}
            {row.license_id && (
              <button
                onClick={async () => {
                  if (!confirm(`Lisansı iptal et: ${row.license_key}?`)) return
                  try {
                    await api.revokeLicense({ license_id: row.license_id })
                    fetchCustomers()
                  } catch (err) {
                    alert(err.message)
                  }
                }}
                className="px-2 py-1 text-danger hover:bg-danger/10 rounded"
                title="Lisans İptal"
              >
                <Ban size={14} />
              </button>
            )}
          </div>
        )}
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

function CustomerDetail({ customerId }) {
  const navigate = useNavigate()
  const [customer, setCustomer] = useState(null)
  const [licenses, setLicenses] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchDetail = async () => {
      setLoading(true)
      try {
        const [customerData, licensesData] = await Promise.all([
          api.customer(customerId),
          api.customerLicenses(customerId),
        ])
        setCustomer(customerData)
        setLicenses(licensesData)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    fetchDetail()
  }, [customerId])

  if (loading) return <div className="flex items-center justify-center h-64 text-muted">Yükleniyor...</div>
  if (error) return <div className="text-danger">Hata: {error}</div>
  if (!customer) return <div className="text-danger">Müşteri bulunamadı</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button onClick={() => navigate('/customers')} className="p-2 hover:bg-white/5 rounded-lg transition-colors">
          <ChevronLeft size={20} />
        </button>
        <div>
          <h1 className="text-2xl font-bold">{customer.name || 'İsimsiz'}</h1>
          <p className="text-sm text-muted">{customer.email}</p>
          {customer.company_name && <p className="text-sm text-muted flex items-center gap-1"><Building2 size={12} /> {customer.company_name}</p>}
        </div>
        <div className="ml-auto">
          <StatusBadge status={customer.is_active ? 'active' : 'cancelled'} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Customer Info */}
        <div className="bg-card rounded-xl p-5 border border-white/10">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <User size={18} /> Müşteri Bilgileri
          </h2>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-muted">Email</span>
              <span>{customer.email}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted">Şirket</span>
              <span>{customer.company_name || '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted">Oluşturulma</span>
              <span>{new Date(customer.created_at).toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted">Durum</span>
              <StatusBadge status={customer.is_active ? 'active' : 'cancelled'} />
            </div>
          </div>
        </div>

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
                  <div className="flex items-center gap-2">
                    <StatusBadge status={lic.is_active ? 'active' : 'cancelled'} />
                    <button
                      onClick={async () => {
                        try {
                          await api.downloadLicense(lic.id)
                        } catch (err) {
                          alert(err.message)
                        }
                      }}
                      className="p-1 text-accent hover:bg-accent/10 rounded"
                      title="Lisans Dosyasını İndir"
                    >
                      <Download size={14} />
                    </button>
                    {lic.is_active && (
                      <button
                        onClick={async () => {
                          if (!confirm(`Lisansı iptal et: ${lic.key}?`)) return
                          try {
                            await api.revokeLicense({ license_id: lic.id })
                            const updatedLicenses = await api.customerLicenses(customerId)
                            setLicenses(updatedLicenses)
                          } catch (err) {
                            alert(err.message)
                          }
                        }}
                        className="p-1 text-danger hover:bg-danger/10 rounded"
                        title="Lisans İptal"
                      >
                        <Ban size={14} />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Issue New License */}
        <div className="lg:col-span-2 bg-card rounded-xl p-5 border border-white/10">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Plus size={18} /> Yeni Lisans Ver
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm text-muted mb-2">Plan</label>
              <select
                value={createPlan}
                onChange={(e) => setCreatePlan(e.target.value)}
                className="w-full px-3 py-2 bg-panel border border-white/10 rounded-lg text-text focus:outline-none focus:border-accent"
              >
                {PLANS.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm text-muted mb-2">Machine ID (opsiyonel)</label>
              <input
                type="text"
                value={createMachineId}
                onChange={(e) => setCreateMachineId(e.target.value)}
                placeholder="Cihaz kimliği"
                className="w-full px-3 py-2 bg-panel border border-white/10 rounded-lg text-text focus:outline-none focus:border-accent"
              />
            </div>
            <div>
              <label className="block text-sm text-muted mb-2">Bitiş Tarihi</label>
              <input
                type="date"
                value={createExpiry}
                onChange={(e) => setCreateExpiry(e.target.value)}
                className="w-full px-3 py-2 bg-panel border border-white/10 rounded-lg text-text focus:outline-none focus:border-accent"
              />
            </div>
            <div>
              <label className="block text-sm text-muted mb-2">Güncelleme Sonu</label>
              <input
                type="date"
                value={createUpdatesUntil}
                onChange={(e) => setCreateUpdatesUntil(e.target.value)}
                className="w-full px-3 py-2 bg-panel border border-white/10 rounded-lg text-text focus:outline-none focus:border-accent"
              />
            </div>
          </div>
          <button
            onClick={async () => {
              if (!createPlan) return
              try {
                const res = await api.issueLicense({
                  user_id: customerId,
                  plan: createPlan,
                  months: 12,
                  machine_id: createMachineId || undefined,
                  expiry: createExpiry || undefined,
                  updates_until: createUpdatesUntil || undefined,
                  max_tracks: createMaxTracks ? parseInt(createMaxTracks) : undefined,
                })
                if (res.ok && res.license) {
                  await api.downloadLicense(res.license.id)
                  const updatedLicenses = await api.customerLicenses(customerId)
                  setLicenses(updatedLicenses)
                }
              } catch (err) {
                alert(err.message)
              }
            }}
            className="mt-4 px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent-hover transition-colors"
          >
            Lisans Ver ve İndir
          </button>
        </div>
      </div>
    </div>
  )
}

export { CustomerDetail }