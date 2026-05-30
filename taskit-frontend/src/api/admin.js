import api from './axios.js'

export const getAdminOverview = async () => {
  const response = await api.get('/support/admin/overview/')
  return response.data
}
