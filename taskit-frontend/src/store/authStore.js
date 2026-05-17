import { create } from 'zustand'

const storedAccessToken = localStorage.getItem('accessToken')
const storedRefreshToken = localStorage.getItem('refreshToken')
const storedUser = localStorage.getItem('user')

export const useAuthStore = create((set) => ({
  user: storedUser ? JSON.parse(storedUser) : null,
  accessToken: storedAccessToken,
  refreshToken: storedRefreshToken,
  isAuthenticated: Boolean(storedAccessToken),
  setAuth: (user, tokens) => {
    localStorage.setItem('user', JSON.stringify(user))
    localStorage.setItem('accessToken', tokens.access)
    localStorage.setItem('refreshToken', tokens.refresh)
    set({
      user,
      accessToken: tokens.access,
      refreshToken: tokens.refresh,
      isAuthenticated: true,
    })
  },
  clearAuth: () => {
    localStorage.removeItem('user')
    localStorage.removeItem('accessToken')
    localStorage.removeItem('refreshToken')
    set({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
    })
  },
}))
