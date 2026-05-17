import api from './axios.js'

export const submitReview = async (taskId, data) => {
  const response = await api.post(`/reviews/submit/${taskId}/`, data)
  return response.data
}

export const getUserReviews = async (userId) => {
  const response = await api.get(`/reviews/user/${userId}/`)
  return response.data
}

export const getUserProfile = async (userId) => {
  const response = await api.get(`/profiles/${userId}/`)
  return response.data
}

export const reportUser = async (userId, data) => {
  const response = await api.post(`/reviews/report-user/${userId}/`, data)
  return response.data
}
