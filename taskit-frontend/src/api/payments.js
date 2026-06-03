import api from './axios.js'

export const initiatePayment = async (taskId) => {
  const response = await api.post(`/payments/initiate/${taskId}/`)
  return response.data
}

export const getPaymentStatus = async (taskId) => {
  const response = await api.get(`/payments/status/${taskId}/`)
  return response.data
}

export const releasePayment = async (taskId) => {
  const response = await api.post(`/payments/release/${taskId}/`)
  return response.data
}

export const disputePayment = async (taskId, data) => {
  const response = await api.post(`/payments/dispute/${taskId}/`, data)
  return response.data
}

export const getMyEarnings = async () => {
  const response = await api.get('/payments/my-earnings/')
  return response.data
}

export const getPlatformBilling = async () => {
  const response = await api.get('/payments/platform-billing/')
  return response.data
}

export const generatePlatformInvoice = async () => {
  const response = await api.post('/payments/platform-billing/')
  return response.data
}

export const createTestPlatformInvoice = async (amount = 70) => {
  const response = await api.post('/payments/platform-billing/test-invoice/', { amount })
  return response.data
}

export const payPlatformInvoice = async (invoiceId, data = {}) => {
  const response = await api.post(`/payments/platform-invoices/${invoiceId}/pay/`, data)
  return response.data
}

export const getPlatformInvoicePaymentStatus = async (invoiceId) => {
  const response = await api.get(`/payments/platform-invoices/${invoiceId}/status/`)
  return response.data
}
