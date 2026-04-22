import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import api from '@/api/client'
import { Plus, FileSignature, Download } from 'lucide-react'
import { downloadBlob } from '@/utils/download'

export default function ProposalPage() {
  const { id: projectId } = useParams<{ id: string }>()
  const qc = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ title: '', client_name: '', attention_to: '', scope_of_work: '', inclusions: '', exclusions: '', clarifications: '', validity_days: 30 })

  const { data: bids } = useQuery({ queryKey: ['bids', projectId], queryFn: () => api.get(`/bids/project/${projectId}`).then(r => r.data.items) })
  const { data: proposals } = useQuery({ queryKey: ['proposals', projectId], queryFn: () => api.get(`/proposals/project/${projectId}`).then(r => r.data.items) })

  const [selectedBid, setSelectedBid] = useState('')

  const create = useMutation({
    mutationFn: (d: any) => api.post('/proposals/', { project_id: parseInt(projectId!), bid_id: selectedBid ? parseInt(selectedBid) : undefined, ...d }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['proposals', projectId] }); setShowCreate(false) },
  })

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Proposals</h1>
        <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
          <Plus size={16} /> New Proposal
        </button>
      </div>

      <div className="space-y-3">
        {(proposals || []).map((p: any) => (
          <div key={p.id} className="card p-4 flex items-center justify-between">
            <div>
              <p className="font-semibold text-gray-900">{p.title}</p>
              <p className="text-sm text-gray-500">{p.client_name} · Valid until {p.expiry_date ? new Date(p.expiry_date).toLocaleDateString() : '—'}</p>
              <span className={`text-xs px-2 py-0.5 rounded-full ${p.status === 'accepted' ? 'bg-green-100 text-green-700' : p.status === 'sent' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'}`}>{p.status}</span>
            </div>
            <button onClick={() => downloadBlob(`/proposals/${p.id}/export/pdf`, `proposal_${p.id}.pdf`)} className="btn-secondary text-xs flex items-center gap-1">
              <Download size={12} /> Export PDF
            </button>
          </div>
        ))}
        {!proposals?.length && (
          <div className="card p-12 text-center text-gray-500">
            <FileSignature size={32} className="mx-auto mb-2 text-gray-300" />
            <p>No proposals yet</p>
          </div>
        )}
      </div>

      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 overflow-auto">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl p-6 my-4">
            <h2 className="text-lg font-semibold mb-4">New Proposal</h2>
            <form onSubmit={(e) => { e.preventDefault(); create.mutate(form) }} className="space-y-3">
              <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="Proposal title *" required className="w-full border rounded-lg px-3 py-2 text-sm" />
              <div className="grid grid-cols-2 gap-2">
                <input value={form.client_name} onChange={(e) => setForm({ ...form, client_name: e.target.value })} placeholder="Client name" className="border rounded-lg px-3 py-2 text-sm" />
                <input value={form.attention_to} onChange={(e) => setForm({ ...form, attention_to: e.target.value })} placeholder="Attention to" className="border rounded-lg px-3 py-2 text-sm" />
              </div>
              <select value={selectedBid} onChange={(e) => setSelectedBid(e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm">
                <option value="">No bid linked</option>
                {(bids || []).map((b: any) => <option key={b.id} value={b.id}>{b.name} — ${b.grand_total?.toLocaleString()}</option>)}
              </select>
              <textarea value={form.scope_of_work} onChange={(e) => setForm({ ...form, scope_of_work: e.target.value })} placeholder="Scope of work" rows={4} className="w-full border rounded-lg px-3 py-2 text-sm" />
              <textarea value={form.inclusions} onChange={(e) => setForm({ ...form, inclusions: e.target.value })} placeholder="Inclusions" rows={3} className="w-full border rounded-lg px-3 py-2 text-sm" />
              <textarea value={form.exclusions} onChange={(e) => setForm({ ...form, exclusions: e.target.value })} placeholder="Exclusions" rows={3} className="w-full border rounded-lg px-3 py-2 text-sm" />
              <textarea value={form.clarifications} onChange={(e) => setForm({ ...form, clarifications: e.target.value })} placeholder="Clarifications & assumptions" rows={3} className="w-full border rounded-lg px-3 py-2 text-sm" />
              <div className="flex items-center gap-2">
                <label className="text-sm text-gray-700">Valid for</label>
                <input type="number" value={form.validity_days} onChange={(e) => setForm({ ...form, validity_days: parseInt(e.target.value) })} className="w-20 border rounded-lg px-3 py-2 text-sm" />
                <span className="text-sm text-gray-500">days</span>
              </div>
              <div className="flex gap-2 pt-2">
                <button type="button" onClick={() => setShowCreate(false)} className="btn-secondary flex-1">Cancel</button>
                <button type="submit" className="btn-primary flex-1">Create Proposal</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
