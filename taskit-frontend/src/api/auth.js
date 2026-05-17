import api from './axios.js'

export const register = async (data) => {
  const response = await api.post('/auth/register/', data)
  return response.data
}

export const login = async (credentials) => {
  const response = await api.post('/auth/login/', credentials)
  return response.data
}

export const refreshToken = async (token) => {
  const response = await api.post('/auth/token/refresh/', { refresh: token })
  return response.data
}

export const verifyEmail = async (token) => {
  const response = await api.get('/auth/verify-email/', {
    params: { token },
  })
  return response.data
}

export const getMe = async () => {
  const response = await api.get('/auth/me/')
  return response.data
}

export const updateProfile = async (data) => {
  const response = await api.patch('/auth/me/', data)
  return response.data
}

export const activateTasker = async () => {
  const response = await api.post('/auth/activate-tasker/')
  return response.data
}

export const updateAvailability = async (data) => {
  const response = await api.patch('/auth/availability/', data)
  return response.data
}

export const getAvailableTaskers = async () => {
  const response = await api.get('/auth/available-taskers/')
  return response.data
}

export const logout = async (refreshTokenValue) => {
  const response = await api.post('/auth/logout/', { refresh: refreshTokenValue })
  return response.data
}

export const getStats = async () => {
  const response = await api.get('/auth/stats/')
  return response.data
}

export const getKycStatus = async () => {
  const response = await api.get('/auth/kyc/')
  return response.data
}

export const submitKyc = async (data) => {
  const response = await api.post('/auth/kyc/', data)
  return response.data
}

export const prefillProfileFromKyc = async () => {
  const response = await api.post('/auth/kyc/prefill-profile/')
  return response.data
}
