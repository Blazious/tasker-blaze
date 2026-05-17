import api from './axios.js'

export const getMessages = async (taskId) => {
  const response = await api.get(`/chat/${taskId}/messages/`)
  return response.data
}

export const sendMessage = async (taskId, data) => {
  const response = await api.post(`/chat/${taskId}/messages/`, data)
  return response.data
}
