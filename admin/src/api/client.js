// API client for DJ AI OS admin SPA
// Handles auth token + fetch wrapper

const TOKEN_KEY = 'dj_ai_os_admin_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

async function request(method, path, body = null) {
  const token = getToken()
  const headers = {
    'Content-Type': 'application/json',
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`/admin/api${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : null,
  })

  if (res.status === 401) {
    throw new Error('UNAUTHORIZED')
  }

  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(data.detail || `HTTP_${res.status}`)
  }
  return data
}

export const api = {
  login: (token) => request('POST', '/login', null, { headers: { Authorization: `Bearer ${token}` } }),
  stats: () => request('GET', '/stats'),
  users: (params = {}) => request('GET', `/users?${new URLSearchParams(params)}`),
  user: (id) => request('GET', `/users/${id}`),
  setUserActive: (id, isActive) => request('POST', `/users/${id}/active`, { is_active: isActive }),
  userLicenses: (userId) => request('GET', `/users/${userId}/licenses`),
  userSubscription: (userId) => request('GET', `/users/${userId}/subscription`),
  userMachines: (userId) => request('GET', `/users/${userId}/machines`),
  licenses: (params = {}) => request('GET', `/licenses?${new URLSearchParams(params)}`),
  license: (id) => request('GET', `/licenses/${id}`),
  issueLicense: (body) => request('POST', '/licenses/issue', body),
  revokeLicense: (body) => request('POST', '/licenses/revoke', body),
  deactivateMachine: (licenseId, machineId) => request('POST', `/licenses/${licenseId}/machines/${machineId}/deactivate`),
  renewLicense: (licenseId, months = 12) => request('POST', `/licenses/${licenseId}/renew`, { months }),
  changeLicensePlan: (licenseId, plan) => request('POST', `/licenses/${licenseId}/change-plan`, { plan }),
  downloadLicense: (licenseId) => {
    // Special handling for file download - returns blob
    const token = getToken()
    const headers = {}
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
    return fetch(`/admin/api/licenses/${licenseId}/download`, {
      method: 'GET',
      headers,
    }).then(res => {
      if (res.status === 401) {
        throw new Error('UNAUTHORIZED')
      }
      if (!res.ok) {
        return res.json().then(data => { throw new Error(data.detail || `HTTP_${res.status}`) })
      }
      return res.blob().then(blob => {
        // Create download link
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        // Extract filename from Content-Disposition header
        const contentDisposition = res.headers.get('Content-Disposition')
        let filename = `customer_${licenseId}.key`
        if (contentDisposition) {
          const match = contentDisposition.match(/filename="?([^"]+)"?/)
          if (match) filename = match[1]
        }
        a.download = filename
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
        return { ok: true }
      })
    })
  },
  // Customer endpoints
  customers: (params = {}) => request('GET', `/customers?${new URLSearchParams(params)}`),
  customer: (id) => request('GET', `/customers/${id}`),
  customerLicenses: (customerId) => request('GET', `/customers/${customerId}/licenses`),
  createCustomer: (body) => request('POST', '/customers', body),
  subscriptions: (params = {}) => request('GET', `/subscriptions?${new URLSearchParams(params)}`),
  subscription: (id) => request('GET', `/subscriptions/${id}`),
  cancelSubscription: (body) => request('POST', '/subscriptions/cancel', body),
  audit: (params = {}) => request('GET', `/audit?${new URLSearchParams(params)}`),
}

export default api
