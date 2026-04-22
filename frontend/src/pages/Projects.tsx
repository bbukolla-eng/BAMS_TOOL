import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import api from '@/api/client'
import { Plus, Search, FolderOpen, Calendar, MapPin } from 'lucide-react'

export default function ProjectsPage() {
  const qc = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [search, setSearch] = useState('')
  const [form, setForm] = useState({ name: '', project_number: '', address: '', city: '', state: '', bid_due_date: '', project_type: 'commercial' })

  const { data, isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: () => api.get('/projects/').then((r) => r.data.items),
  })

  const create = useMutation({
    mutationFn: (data: typeof form) => api.post('/projects/', data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['projects'] }); setShowCreate(false) },
  })

  const filtered = (data || []).filter((p: any) =>
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    p.project_number?.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Projects</h1>
        <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
          <Plus size={16} /> New Project
        </button>
      </div>

      {/* Search */}
      <div className="relative mb-4">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search projects..."
          className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Projects Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {isLoading && <p className="text-gray-500 text-sm">Loading...</p>}
        {filtered.map((p: any) => (
          <Link key={p.id} to={`/projects/${p.id}`} className="card p-4 hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between mb-2">
              <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                <FolderOpen size={16} className="text-blue-600" />
              </div>
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                p.status === 'active' ? 'bg-green-100 text-green-700' :
                p.status === 'bidding' ? 'bg-yellow-100 text-yellow-700' :
                p.status === 'won' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-700'
              }`}>{p.status}</span>
            </div>
            <h3 className="font-semibold text-gray-900 mt-2">{p.name}</h3>
            {p.project_number && <p className="text-xs text-gray-500 mt-0.5">#{p.project_number}</p>}
            <div className="mt-3 space-y-1">
              {(p.city || p.state) && (
                <div className="flex items-center gap-1 text-xs text-gray-500">
                  <MapPin size={12} /> {[p.city, p.state].filter(Boolean).join(', ')}
                </div>
              )}
              {p.bid_due_date && (
                <div className="flex items-center gap-1 text-xs text-gray-500">
                  <Calendar size={12} /> Due {new Date(p.bid_due_date).toLocaleDateString()}
                </div>
              )}
            </div>
          </Link>
        ))}
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-lg font-semibold mb-4">New Project</h2>
            <form onSubmit={(e) => { e.preventDefault(); create.mutate(form) }} className="space-y-3">
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Project name *" required className="w-full border rounded-lg px-3 py-2 text-sm" />
              <input value={form.project_number} onChange={(e) => setForm({ ...form, project_number: e.target.value })} placeholder="Project number" className="w-full border rounded-lg px-3 py-2 text-sm" />
              <div className="grid grid-cols-2 gap-2">
                <input value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} placeholder="City" className="border rounded-lg px-3 py-2 text-sm" />
                <input value={form.state} onChange={(e) => setForm({ ...form, state: e.target.value })} placeholder="State" className="border rounded-lg px-3 py-2 text-sm" />
              </div>
              <input type="date" value={form.bid_due_date} onChange={(e) => setForm({ ...form, bid_due_date: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm text-gray-700" />
              <select value={form.project_type} onChange={(e) => setForm({ ...form, project_type: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm">
                {['commercial', 'industrial', 'residential', 'institutional', 'healthcare', 'data_center'].map(t => <option key={t} value={t}>{t}</option>)}
              </select>
              <div className="flex gap-2 pt-2">
                <button type="button" onClick={() => setShowCreate(false)} className="btn-secondary flex-1">Cancel</button>
                <button type="submit" className="btn-primary flex-1" disabled={create.isPending}>Create</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
