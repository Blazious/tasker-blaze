import api from './axios.js'

export const getAdminOverview = async () => {
  const response = await api.get('/support/admin/overview/')
  return response.data
}

export const getAdminSupportTickets = async (params = {}) => {
  const response = await api.get('/support/admin/tickets/', { params })
  return response.data
}

export const updateAdminSupportTicket = async (id, data) => {
  const response = await api.patch(`/support/admin/tickets/${id}/`, data)
  return response.data
}

export const getAdminUserReports = async (params = {}) => {
  const response = await api.get('/reviews/admin/reports/', { params })
  return response.data
}

export const updateAdminUserReport = async (id, data) => {
  const response = await api.patch(`/reviews/admin/reports/${id}/`, data)
  return response.data
}

export const getAdminKycSubmissions = async (params = {}) => {
  const response = await api.get('/auth/admin/kyc/', { params })
  return response.data
}

export const updateAdminKycSubmission = async (id, data) => {
  const response = await api.patch(`/auth/admin/kyc/${id}/`, data)
  return response.data
}

export const getAdminPlatformInvoices = async (params = {}) => {
  const response = await api.get('/payments/admin/platform-invoices/', { params })
  return response.data
}

export const updateAdminPlatformInvoice = async (id, data) => {
  const response = await api.patch(`/payments/admin/platform-invoices/${id}/`, data)
  return response.data
}
