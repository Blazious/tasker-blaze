import api from './axios.js'

export const getSupportConversation = async () => {
  const response = await api.get('/support/conversation/')
  return response.data
}

export const sendSupportMessage = async (data) => {
  const response = await api.post('/support/chat/', data)
  return response.data
}

export const escalateSupportTicket = async (data) => {
  const response = await api.post('/support/escalate/', data)
  return response.data
}

export const getSupportTickets = async () => {
  const response = await api.get('/support/tickets/')
  return response.data
}
