import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import api from '@/api/client'
import { Plus, ClipboardCheck, CheckCircle, Circle } from 'lucide-react'

const DOC_TYPES = ['om_manual', 'warranty', 'as_built', 'punch_list', 'test_balance_report', 'commissioning_report', 'certificate_completion', 'attic_stock', 'training_record', 'lien_waiver', 'other']

export default function CloseoutPage() {
  const { id: projectId } = useParams<{ id: string }>()
  const qc = useQueryClient()
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({ title: '', doc_type: 'om_manual', description: '', warranty_duration_months: '' })

  const { data } = useQuery({
    queryKey: ['closeout', projectId],
    queryFn: () => api.get(`/closeout/project/${projectId}`).then((r) => r.data),
  })

  const create = useMutation({
    mutationFn: (d: any) => api.post('/closeout/', { project_id: parseInt(projectId!), ...d }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['closeout', projectId] }); setShowAdd(false) },
  })

  const markReceived = useMutation({
    mutationFn: (id: number) => api.patch(`/closeout/${id}`, { is_received: true }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['closeout', projectId] }),
  })

  const items = data?.items || []
  const summary = data?.summary || {}
  const total = Object.values(summary).reduce((a: number, s: any) => a + s.total, 0)
  const received = Object.values(summary).reduce((a: number, s: any) => a + s.received, 0)
  const pct = total > 0 ? Math.round((received / total) * 100) : 0

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Closeout</h1>
          {total > 0 && <p className="text-sm text-gray-500 mt-1">{received}/{total} documents received ({pct}%)</p>}
        </div>
        <button onClick={() => setShowAdd(true)} className="btn-primary flex items-center gap-2">
          <Plus size={16} /> Add Document
        </button>
      </div>

      {/* Progress bar */}
      {total > 0 && (
        <div className="mb-4 h-2 bg-gray-200 rounded-full overflow-hidden">
          <div className="h-full bg-green-500 transition-all" style={{ width: `${pct}%` }} />
        </div>
      )}

      <div className="space-y-2">
        {DOC_TYPES.filter(t => items.some((i: any) => i.doc_type === t)).map((type) => {
          const typeItems = items.filter((i: any) => i.doc_type === type)
          return (
            <div key={type} className="card overflow-hidden">
              <div className="px-4 py-2 bg-gray-50 border-b border-gray-100 flex items-center justify-between">
                <span className="text-xs font-semibold uppercase text-gray-600">{type.replace(/_/g, ' ')}</span>
                <span className="text-xs text-gray-500">{typeItems.filter((i: any) => i.is_received).length}/{typeItems.length}</span>
              </div>
              {typeItems.map((doc: any) => (
                <div key={doc.id} className="flex items-center gap-3 px-4 py-2.5 hover:bg-gray-50">
                  <button onClick={() => !doc.is_received && markReceived.mutate(doc.id)}>
                    {doc.is_received ? <CheckCircle size={18} className="text-green-500" /> : <Circle size={18} className="text-gray-300" />}
                  </button>
                  <div className="flex-1">
                    <p className={`text-sm ${doc.is_received ? 'text-gray-500 line-through' : 'text-gray-900 font-medium'}`}>{doc.title}</p>
                    {doc.warranty_expiry_date && <p className="text-xs text-gray-400">Expires {new Date(doc.warranty_expiry_date).toLocaleDateString()}</p>}
                  </div>
                  {doc.is_received && doc.received_date && (
                    <span className="text-xs text-gray-400">{new Date(doc.received_date).toLocaleDateString()}</span>
                  )}
                </div>
              ))}
            </div>
          )
        })}
        {!items.length && (
          <div className="card p-8 text-center text-gray-500">
            <ClipboardCheck size={32} className="mx-auto mb-2 text-gray-300" />
            <p>No closeout documents yet</p>
          </div>
        )}
      </div>

      {showAdd && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6">
            <h2 className="text-lg font-semibold mb-4">Add Closeout Document</h2>
            <form onSubmit={(e) => { e.preventDefault(); create.mutate({ ...form, warranty_duration_months: form.warranty_duration_months ? parseInt(form.warranty_duration_months) : undefined }) }} className="space-y-3">
              <select value={form.doc_type} onChange={(e) => setForm({ ...form, doc_type: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm">
                {DOC_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
              </select>
              <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="Title *" required className="w-full border rounded-lg px-3 py-2 text-sm" />
              {form.doc_type === 'warranty' && (
                <input type="number" value={form.warranty_duration_months} onChange={(e) => setForm({ ...form, warranty_duration_months: e.target.value })} placeholder="Warranty duration (months)" className="w-full border rounded-lg px-3 py-2 text-sm" />
              )}
              <div className="flex gap-2 pt-2">
                <button type="button" onClick={() => setShowAdd(false)} className="btn-secondary flex-1">Cancel</button>
                <button type="submit" className="btn-primary flex-1">Add</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
