import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
  token: string | null
  refreshToken: string | null
  user: { id: number; email: string; role: string; orgId: number } | null
  setTokens: (access: string, refresh: string) => void
  setUser: (user: AuthState['user']) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      refreshToken: null,
      user: null,
      setTokens: (access, refresh) => set({ token: access, refreshToken: refresh }),
      setUser: (user) => set({ user }),
      logout: () => set({ token: null, refreshToken: null, user: null }),
    }),
    { name: 'bams-auth' },
  ),
)
