import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import api from '@/api/client'
import { Plus, Package } from 'lucide-react'

const STATUS_COLORS: Record<string, string> = {
  not_submitted: 'bg-gray-100 text-gray-600',
  submitted: 'bg-blue-100 text-blue-700',
  under_review: 'bg-yellow-100 text-yellow-700',
  approved: 'bg-green-100 text-green-700',
  approved_as_noted: 'bg-teal-100 text-teal-700',
  revise_resubmit: 'bg-orange-100 text-orange-700',
  rejected: 'bg-red-100 text-red-700',
}

export default function SubmittalsPage() {
  const { id: projectId } = useParams<{ id: string }>()
  const qc = useQueryClient()
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({ title: '', spec_section_ref: '', required_date: '' })

  const { data } = useQuery({
    queryKey: ['submittals', projectId],
    queryFn: () => api.get(`/submittals/project/${projectId}`).then((r) => r.data.items),
  })

  const create = useMutation({
    mutationFn: (d: typeof form) => api.post('/submittals/', { project_id: parseInt(projectId!), ...d }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['submittals', projectId] }); setShowAdd(false) },
  })

  const updateStatus = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) => api.patch(`/submittals/${id}`, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['submittals', projectId] }),
  })

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Submittals</h1>
        <button onClick={() => setShowAdd(true)} className="btn-primary flex items-center gap-2">
          <Plus size={16} /> New Submittal
        </button>
      </div>

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="table-header">
            <tr>
              <th className="px-4 py-3 text-left">#</th>
              <th className="px-4 py-3 text-left">Title</th>
              <th className="px-4 py-3 text-left">Spec Ref</th>
              <th className="px-4 py-3 text-left">Required Date</th>
              <th className="px-4 py-3 text-left">Rev</th>
              <th className="px-4 py-3 text-left">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {(data || []).map((s: any) => (
              <tr key={s.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs text-gray-500">{s.submittal_number}</td>
                <td className="px-4 py-3 font-medium text-gray-900">{s.title}</td>
                <td className="px-4 py-3 text-gray-500 font-mono text-xs">{s.spec_section_ref || '—'}</td>
                <td className="px-4 py-3 text-gray-500 text-xs">{s.required_date ? new Date(s.required_date).toLocaleDateString() : '—'}</td>
                <td className="px-4 py-3 text-center">{s.revision}</td>
                <td className="px-4 py-3">
                  <select value={s.status} onChange={(e) => updateStatus.mutate({ id: s.id, status: e.target.value })}
                    className={`text-xs px-2 py-1 rounded-full font-medium border-0 ${STATUS_COLORS[s.status]}`}>
                    {Object.keys(STATUS_COLORS).map(st => <option key={st} value={st}>{st.replace(/_/g, ' ')}</option>)}
                  </select>
                </td>
              </tr>
            ))}
            {!data?.length && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                <Package size={28} className="mx-auto mb-2 text-gray-300" />
                No submittals yet
              </td></tr>
            )}
          </tbody>
        </table>
      </div>

      {showAdd && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6">
            <h2 className="text-lg font-semibold mb-4">New Submittal</h2>
            <form onSubmit={(e) => { e.preventDefault(); create.mutate(form) }} className="space-y-3">
              <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="Title *" required className="w-full border rounded-lg px-3 py-2 text-sm" />
              <input value={form.spec_section_ref} onChange={(e) => setForm({ ...form, spec_section_ref: e.target.value })} placeholder="Spec section (e.g. 23 74 13)" className="w-full border rounded-lg px-3 py-2 text-sm" />
              <input type="date" value={form.required_date} onChange={(e) => setForm({ ...form, required_date: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
              <div className="flex gap-2 pt-2">
                <button type="button" onClick={() => setShowAdd(false)} className="btn-secondary flex-1">Cancel</button>
                <button type="submit" className="btn-primary flex-1">Create</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
