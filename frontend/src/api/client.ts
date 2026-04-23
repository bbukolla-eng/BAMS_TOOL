import axios from 'axios'
import { useAuthStore } from '@/stores/auth'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
})

// If running inside Electron, update baseURL to use the Electron-managed backend port
if (typeof window !== 'undefined' && (window as any).bamsElectron) {
  ;(window as any).bamsElectron.getBackendUrl().then((url: string) => {
    api.defaults.baseURL = `${url}/api/v1`
  })
}

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401) {
      const { refreshToken, setTokens, logout } = useAuthStore.getState()
      if (refreshToken) {
        try {
          const res = await axios.post(`${BASE_URL}/api/v1/auth/refresh`, { refresh_token: refreshToken })
          setTokens(res.data.access_token, res.data.refresh_token)
          error.config.headers.Authorization = `Bearer ${res.data.access_token}`
          return api.request(error.config)
        } catch {
          logout()
        }
      } else {
        logout()
      }
    }
    return Promise.reject(error)
  },
)

export default api
