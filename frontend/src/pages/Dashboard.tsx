import { useQuery } from '@tanstack/react-query'
import api from '@/api/client'
import { FolderOpen, FileImage, Calculator, Gavel, Clock, TrendingUp } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function Dashboard() {
  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: () => api.get('/projects/').then((r) => r.data.items),
  })

  const activeProjects = projects?.filter((p: any) => p.status === 'active') || []
  const biddingProjects = projects?.filter((p: any) => p.status === 'bidding') || []

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">Division 23 HVAC — MEP Construction Management</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {[
          { label: 'Total Projects', value: projects?.length || 0, icon: FolderOpen, color: 'blue' },
          { label: 'Active', value: activeProjects.length, icon: TrendingUp, color: 'green' },
          { label: 'Bidding', value: biddingProjects.length, icon: Gavel, color: 'yellow' },
          { label: 'Due This Week', value: 0, icon: Clock, color: 'red' },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="card p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">{label}</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
              </div>
              <div className={`w-10 h-10 rounded-lg bg-${color}-100 flex items-center justify-center`}>
                <Icon size={20} className={`text-${color}-600`} />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Recent Projects */}
      <div className="card">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-900">Recent Projects</h2>
          <Link to="/projects" className="text-sm text-blue-600 hover:text-blue-700">View all</Link>
        </div>
        <div className="divide-y divide-gray-100">
          {!projects?.length && (
            <div className="p-8 text-center text-gray-500">
              <FolderOpen size={32} className="mx-auto mb-2 text-gray-300" />
              <p className="text-sm">No projects yet</p>
              <Link to="/projects" className="btn-primary mt-3 inline-block">Create Project</Link>
            </div>
          )}
          {projects?.slice(0, 8).map((p: any) => (
            <Link key={p.id} to={`/projects/${p.id}`} className="flex items-center justify-between px-5 py-3 hover:bg-gray-50 transition-colors">
              <div>
                <p className="text-sm font-medium text-gray-900">{p.name}</p>
                <p className="text-xs text-gray-500">{p.project_number || 'No number'} · {p.city || p.address || 'No location'}</p>
              </div>
              <div className="flex items-center gap-3">
                {p.bid_due_date && (
                  <span className="text-xs text-gray-500">Due {new Date(p.bid_due_date).toLocaleDateString()}</span>
                )}
                <StatusBadge status={p.status} />
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    active: 'badge-green',
    bidding: 'badge-yellow',
    won: 'badge-blue',
    lost: 'badge-red',
    archived: 'bg-gray-100 text-gray-600 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
  }
  return <span className={map[status] || 'badge-blue'}>{status}</span>
}
