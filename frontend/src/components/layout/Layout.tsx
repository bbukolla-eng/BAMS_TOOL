import { Outlet, NavLink, useParams, useNavigate, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '@/stores/auth'
import api from '@/api/client'
import {
  LayoutDashboard, FolderOpen, FileImage, Brain, FileText,
  Calculator, BookOpen, Users, DollarSign, Gavel, BarChart3,
  FileSignature, Package, ClipboardCheck, Wrench, LogOut,
  ChevronDown, Building2, Settings,
} from 'lucide-react'
import { useState } from 'react'

const globalNav = [
  { to: '/projects', icon: FolderOpen, label: 'Projects' },
  { to: '/price-book', icon: BookOpen, label: 'Price Book' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

function ProjectSwitcher({ projectId }: { projectId: string }) {
  const navigate = useNavigate()
  const location = useLocation()
  const [open, setOpen] = useState(false)

  const { data: projects } = useQuery<any[]>({
    queryKey: ['projects'],
    queryFn: () => api.get('/projects/').then((r) => r.data.items),
  })

  const current = projects?.find((p) => String(p.id) === projectId)

  // Keep only the first sub-segment (e.g. /drawings, /estimate) so we don't
  // carry a previous project's child IDs into the new project's URL.
  const match = location.pathname.match(/^\/projects\/[^/]+(\/[^/]+)?/)
  const subPath = match?.[1] || ''

  const handleSelect = (id: number) => {
    setOpen(false)
    navigate(`/projects/${id}${subPath}`)
  }

  if (!projects?.length) return null

  return (
    <div className="relative px-2 mb-2">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm bg-gray-50 hover:bg-gray-100 border border-gray-200"
      >
        <FolderOpen size={14} className="text-blue-700 flex-shrink-0" />
        <span className="flex-1 text-left text-gray-900 font-medium truncate">
          {current?.name || 'Select project'}
        </span>
        <ChevronDown size={14} className={`text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute left-2 right-2 mt-1 bg-white border border-gray-200 rounded-md shadow-lg z-20 max-h-64 overflow-y-auto">
            {projects.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => handleSelect(p.id)}
                className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-50 ${
                  String(p.id) === projectId ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-700'
                }`}
              >
                <div className="truncate">{p.name}</div>
                {p.project_number && (
                  <div className="text-xs text-gray-400 truncate">{p.project_number}</div>
                )}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

function ProjectNav({ projectId }: { projectId: string }) {
  const items = [
    { to: `/projects/${projectId}`, icon: FolderOpen, label: 'Overview', exact: true },
    { to: `/projects/${projectId}/drawings`, icon: FileImage, label: 'Drawings' },
    { to: `/projects/${projectId}/specs`, icon: FileText, label: 'Specs' },
    { to: `/projects/${projectId}/takeoff`, icon: Calculator, label: 'Takeoff' },
    { to: `/projects/${projectId}/estimate`, icon: Gavel, label: 'Estimate' },
  ]
  return (
    <div className="mt-4">
      <p className="px-3 text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">Project</p>
      <ProjectSwitcher projectId={projectId} />
      {items.map(({ to, icon: Icon, label }) => (
        <NavLink
          key={to}
          to={to}
          end={label === 'Overview'}
          className={({ isActive }) =>
            `flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors ${
              isActive ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-600 hover:bg-gray-100'
            }`
          }
        >
          <Icon size={16} />
          {label}
        </NavLink>
      ))}
    </div>
  )
}

export default function Layout() {
  const { id: projectId } = useParams()
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-56 bg-white border-r border-gray-200 flex flex-col">
        {/* Logo */}
        <div className="h-14 flex items-center gap-2 px-4 border-b border-gray-200">
          <div className="w-7 h-7 bg-blue-700 rounded flex items-center justify-center">
            <Building2 size={16} className="text-white" />
          </div>
          <span className="font-bold text-gray-900 text-base">BAMS AI</span>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-0.5">
          <p className="px-3 text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">Main</p>
          {globalNav.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors ${
                  isActive ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-600 hover:bg-gray-100'
                }`
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}

          {projectId && <ProjectNav projectId={projectId} />}
        </nav>

        {/* User */}
        <div className="border-t border-gray-200 p-3">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-gray-200 rounded-full flex items-center justify-center text-xs font-medium text-gray-600">
              {user?.email?.[0]?.toUpperCase() || 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-gray-900 truncate">{user?.email || 'User'}</p>
              <p className="text-xs text-gray-500 capitalize">{user?.role || 'estimator'}</p>
            </div>
            <button onClick={handleLogout} className="text-gray-400 hover:text-gray-600">
              <LogOut size={14} />
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
