import axios from 'axios'
import { useAuthStore } from '../store/authStore.js'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

const api = axios.create({
  baseURL: API_BASE_URL,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('accessToken')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status !== 401 || originalRequest?._retry) {
      return Promise.reject(error)
    }

    originalRequest._retry = true
    const refreshToken = localStorage.getItem('refreshToken')

    if (!refreshToken) {
      useAuthStore.getState().clearAuth()
      window.location.assign('/login')
      return Promise.reject(error)
    }

    try {
      const response = await axios.post(
        `${API_BASE_URL}/auth/token/refresh/`,
        { refresh: refreshToken },
      )
      const accessToken = response.data.access
      localStorage.setItem('accessToken', accessToken)
      useAuthStore.setState({
        accessToken,
        isAuthenticated: true,
      })
      originalRequest.headers.Authorization = `Bearer ${accessToken}`
      return api(originalRequest)
    } catch (refreshError) {
      useAuthStore.getState().clearAuth()
      window.location.assign('/login')
      return Promise.reject(refreshError)
    }
  },
)

export default api
