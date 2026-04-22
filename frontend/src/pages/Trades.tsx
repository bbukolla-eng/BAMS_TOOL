import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import api from '@/api/client'
import { Plus, Users } from 'lucide-react'

export default function TradesPage() {
  const qc = useQueryClient()
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({ name: '', code: '', division: '', base_labor_rate: 0, foreman_rate: 0, is_primary: false })

  const { data } = useQuery({ queryKey: ['trades'], queryFn: () => api.get('/trades/').then(r => r.data.items) })

  const create = useMutation({
    mutationFn: (d: typeof form) => api.post('/trades/', d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['trades'] }); setShowAdd(false) },
  })

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Trades</h1>
        <button onClick={() => setShowAdd(true)} className="btn-primary flex items-center gap-2"><Plus size={16} /> Add Trade</button>
      </div>
      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="table-header"><tr>
            <th className="px-4 py-3 text-left">Name</th>
            <th className="px-4 py-3 text-left">Code</th>
            <th className="px-4 py-3 text-left">Division</th>
            <th className="px-4 py-3 text-right">Base Rate $/hr</th>
            <th className="px-4 py-3 text-right">Foreman Rate</th>
            <th className="px-4 py-3 text-center">Primary</th>
          </tr></thead>
          <tbody className="divide-y divide-gray-100">
            {(data || []).map((t: any) => (
              <tr key={t.id} className={`hover:bg-gray-50 ${t.is_primary ? 'bg-blue-50' : ''}`}>
                <td className="px-4 py-3 font-medium">{t.name}</td>
                <td className="px-4 py-3 font-mono text-xs">{t.code}</td>
                <td className="px-4 py-3 text-gray-500">{t.division ? `Div. ${t.division}` : '—'}</td>
                <td className="px-4 py-3 text-right">${t.base_labor_rate?.toFixed(2)}</td>
                <td className="px-4 py-3 text-right">${t.foreman_rate?.toFixed(2)}</td>
                <td className="px-4 py-3 text-center">{t.is_primary ? '★' : ''}</td>
              </tr>
            ))}
            {!data?.length && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                <Users size={28} className="mx-auto mb-2 text-gray-300" /><p>No trades yet</p>
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
      {showAdd && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6">
            <h2 className="text-lg font-semibold mb-4">Add Trade</h2>
            <form onSubmit={(e) => { e.preventDefault(); create.mutate(form) }} className="space-y-3">
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Trade name *" required className="w-full border rounded-lg px-3 py-2 text-sm" />
              <div className="grid grid-cols-2 gap-2">
                <input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} placeholder="Code (e.g. MECH)" className="border rounded-lg px-3 py-2 text-sm" />
                <input value={form.division} onChange={(e) => setForm({ ...form, division: e.target.value })} placeholder="Division (e.g. 23)" className="border rounded-lg px-3 py-2 text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div><label className="text-xs text-gray-600">Base Rate $/hr</label>
                  <input type="number" step="0.01" value={form.base_labor_rate} onChange={(e) => setForm({ ...form, base_labor_rate: parseFloat(e.target.value) })} className="w-full border rounded-lg px-3 py-2 text-sm mt-1" />
                </div>
                <div><label className="text-xs text-gray-600">Foreman Rate $/hr</label>
                  <input type="number" step="0.01" value={form.foreman_rate} onChange={(e) => setForm({ ...form, foreman_rate: parseFloat(e.target.value) })} className="w-full border rounded-lg px-3 py-2 text-sm mt-1" />
                </div>
              </div>
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.is_primary} onChange={(e) => setForm({ ...form, is_primary: e.target.checked })} /> Primary trade (Division 23)</label>
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
