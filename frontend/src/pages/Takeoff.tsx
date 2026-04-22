import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import api from '@/api/client'
import { RefreshCw, Download, Lock, Unlock, Edit2, Check, X } from 'lucide-react'

interface TakeoffItem {
  id: number
  category: string
  description: string
  csi_code: string
  system: string
  quantity: number
  adjusted_quantity: number
  unit: string
  unit_material_cost: number | null
  unit_labor_hours: number | null
  material_total: number | null
  labor_total: number | null
  confidence: number
  is_locked: boolean
  notes: string | null
}

function ConfidenceDot({ value }: { value: number }) {
  const cls = value >= 0.85 ? 'bg-green-500' : value >= 0.65 ? 'bg-yellow-500' : 'bg-red-500'
  return (
    <span title={`${Math.round(value * 100)}% confidence`} className={`inline-block w-2 h-2 rounded-full ${cls}`} />
  )
}

export default function TakeoffPage() {
  const { id: projectId } = useParams<{ id: string }>()
  const qc = useQueryClient()
  const [editId, setEditId] = useState<number | null>(null)
  const [editQty, setEditQty] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['takeoff', projectId],
    queryFn: () => api.get(`/takeoff/project/${projectId}`).then((r) => r.data),
  })

  const regenerate = useMutation({
    mutationFn: () => api.post(`/takeoff/project/${projectId}/regenerate`),
    onSuccess: () => setTimeout(() => qc.invalidateQueries({ queryKey: ['takeoff', projectId] }), 3000),
  })

  const updateItem = useMutation({
    mutationFn: ({ id, quantity }: { id: number; quantity: number }) =>
      api.patch(`/takeoff/${id}`, { quantity }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['takeoff', projectId] }); setEditId(null) },
  })

  const items: TakeoffItem[] = data?.items || []
  const summary = data?.summary || {}

  const categories = [...new Set(items.map((i) => i.category))].sort()

  const fmt = (n: number | null | undefined) =>
    n != null ? `$${n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—'

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Takeoff</h1>
        <div className="flex gap-2">
          <button onClick={() => regenerate.mutate()} className="btn-secondary flex items-center gap-2" disabled={regenerate.isPending}>
            <RefreshCw size={14} className={regenerate.isPending ? 'animate-spin' : ''} />
            Regenerate from Drawings
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        {Object.entries(summary).map(([cat, s]: [string, any]) => (
          <div key={cat} className="card p-3">
            <p className="text-xs text-gray-500 capitalize">{cat.replace('_', ' ')}</p>
            <p className="text-lg font-bold text-gray-900">{s.count} items</p>
            <p className="text-xs text-green-600">{fmt(s.material_total)} material</p>
          </div>
        ))}
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="table-header">
              <th className="px-3 py-3 text-left">Description</th>
              <th className="px-3 py-3 text-left">CSI</th>
              <th className="px-3 py-3 text-left">System</th>
              <th className="px-3 py-3 text-right">Qty</th>
              <th className="px-3 py-3 text-left">Unit</th>
              <th className="px-3 py-3 text-right">Unit Cost</th>
              <th className="px-3 py-3 text-right">Material</th>
              <th className="px-3 py-3 text-right">Labor Hrs</th>
              <th className="px-3 py-3 text-center">Conf</th>
              <th className="px-3 py-3 text-center">Lock</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading && (
              <tr><td colSpan={10} className="px-3 py-8 text-center text-gray-500">Loading...</td></tr>
            )}
            {categories.map((cat) => (
              <>
                <tr key={`header-${cat}`} className="bg-blue-50">
                  <td colSpan={10} className="px-3 py-2 text-xs font-semibold text-blue-800 uppercase tracking-wide capitalize">
                    {cat.replace(/_/g, ' ')}
                  </td>
                </tr>
                {items.filter((i) => i.category === cat).map((item) => (
                  <tr key={item.id} className={`hover:bg-gray-50 ${item.is_locked ? 'bg-amber-50' : ''}`}>
                    <td className="px-3 py-2 text-gray-900">{item.description}</td>
                    <td className="px-3 py-2 text-gray-500 font-mono text-xs">{item.csi_code}</td>
                    <td className="px-3 py-2 text-gray-500 text-xs">{item.system}</td>
                    <td className="px-3 py-2 text-right">
                      {editId === item.id ? (
                        <div className="flex items-center gap-1 justify-end">
                          <input value={editQty} onChange={(e) => setEditQty(e.target.value)} className="w-20 border rounded px-1 py-0.5 text-xs text-right" />
                          <button onClick={() => updateItem.mutate({ id: item.id, quantity: parseFloat(editQty) })} className="text-green-600 hover:text-green-700"><Check size={12} /></button>
                          <button onClick={() => setEditId(null)} className="text-gray-400 hover:text-gray-600"><X size={12} /></button>
                        </div>
                      ) : (
                        <span className="cursor-pointer hover:text-blue-600" onClick={() => { setEditId(item.id); setEditQty(String(item.adjusted_quantity)) }}>
                          {item.adjusted_quantity.toFixed(2)}
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-gray-500">{item.unit}</td>
                    <td className="px-3 py-2 text-right text-gray-700">{fmt(item.unit_material_cost)}</td>
                    <td className="px-3 py-2 text-right font-medium text-gray-900">{fmt(item.material_total)}</td>
                    <td className="px-3 py-2 text-right text-gray-500">{item.unit_labor_hours?.toFixed(2) ?? '—'}</td>
                    <td className="px-3 py-2 text-center"><ConfidenceDot value={item.confidence} /></td>
                    <td className="px-3 py-2 text-center text-gray-400">
                      {item.is_locked ? <Lock size={12} className="text-amber-500" /> : <Unlock size={12} />}
                    </td>
                  </tr>
                ))}
              </>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
