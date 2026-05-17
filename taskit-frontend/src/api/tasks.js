import api from './axios.js'

export const getCategories = async () => {
  const response = await api.get('/tasks/categories/')
  return response.data
}

export const getTasks = async (filters = {}) => {
  const response = await api.get('/tasks/', { params: filters })
  return response.data
}

export const getTask = async (id) => {
  const response = await api.get(`/tasks/${id}/`)
  return response.data
}

export const createTask = async (data) => {
  const response = await api.post('/tasks/', data)
  return response.data
}

export const getMyTasks = async () => {
  const response = await api.get('/tasks/my-tasks/')
  return response.data
}

export const getMyAssignments = async () => {
  const response = await api.get('/tasks/my-assignments/')
  return response.data
}

export const getMyBids = async () => {
  const response = await api.get('/tasks/my-bids/')
  return response.data
}

export const placeBid = async (taskId, data) => {
  const response = await api.post(`/tasks/${taskId}/bids/`, data)
  return response.data
}

export const acceptBid = async (taskId, bidId) => {
  const response = await api.post(`/tasks/${taskId}/bids/${bidId}/accept/`)
  return response.data
}

export const rejectBid = async (taskId, bidId) => {
  const response = await api.post(`/tasks/${taskId}/bids/${bidId}/reject/`)
  return response.data
}

export const getTaskBids = async (taskId) => {
  const response = await api.get(`/tasks/${taskId}/bids/`)
  return response.data
}
