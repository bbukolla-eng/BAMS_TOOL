import { Outlet, NavLink, useParams, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth'
import {
  LayoutDashboard, FolderOpen, FileImage, Brain, FileText,
  Calculator, BookOpen, Users, DollarSign, Gavel, BarChart3,
  FileSignature, Package, ClipboardCheck, Wrench, LogOut,
  ChevronDown, Building2
} from 'lucide-react'
import { useState } from 'react'

const globalNav = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/projects', icon: FolderOpen, label: 'Projects' },
  { to: '/price-book', icon: BookOpen, label: 'Price Book' },
  { to: '/trades', icon: Users, label: 'Trades' },
  { to: '/overhead', icon: DollarSign, label: 'Overhead' },
]

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
