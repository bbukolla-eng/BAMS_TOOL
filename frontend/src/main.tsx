import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, HashRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 2,
    },
  },
})

// In Electron the app loads via file://; BrowserRouter can't push history
// entries because Chromium blocks renderer-initiated file:// navigations.
// HashRouter keeps all routes in the URL fragment (#/login) so navigation
// stays inside the same loaded index.html.
const isElectron =
  typeof window !== 'undefined' &&
  ((window as any).bamsElectron !== undefined ||
    window.location.protocol === 'file:')
const Router = isElectron ? HashRouter : BrowserRouter

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <Router>
        <App />
      </Router>
    </QueryClientProvider>
  </React.StrictMode>,
)
