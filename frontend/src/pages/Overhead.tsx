import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import api from '@/api/client'
import { Plus, DollarSign } from 'lucide-react'

const DEFAULT_OVERHEAD = { name: 'Default', fica_rate: 0.0765, futa_rate: 0.006, suta_rate: 0.027, workers_comp_rate: 0.12, general_liability_rate: 0.015, health_insurance_rate: 0.08, vacation_rate: 0.05, general_overhead_rate: 0.10, small_tools_rate: 0.02, material_markup: 0.10, profit_margin: 0.08, contingency_rate: 0.03, bond_rate: 0.015, permit_rate: 0.01, is_default: true }

export default function OverheadPage() {
  const qc = useQueryClient()
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState(DEFAULT_OVERHEAD)

  const { data } = useQuery({ queryKey: ['overhead'], queryFn: () => api.get('/overhead/').then(r => r.data.items) })

  const create = useMutation({
    mutationFn: (d: typeof form) => api.post('/overhead/', d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['overhead'] }); setShowAdd(false) },
  })

  const pct = (v: number) => `${(v * 100).toFixed(2)}%`

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Overhead & Markup</h1>
        <button onClick={() => setShowAdd(true)} className="btn-primary flex items-center gap-2"><Plus size={16} /> New Config</button>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {(data || []).map((cfg: any) => (
          <div key={cfg.id} className={`card p-5 ${cfg.is_default ? 'ring-2 ring-blue-500' : ''}`}>
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-gray-900">{cfg.name}</h3>
              {cfg.is_default && <span className="badge-blue text-xs">Default</span>}
            </div>
            <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm">
              {[
                ['Labor Burden', cfg.total_burden_rate],
                ['General Overhead', cfg.general_overhead_rate],
                ['Material Markup', cfg.material_markup],
                ['Profit Margin', cfg.profit_margin],
                ['Contingency', cfg.contingency_rate],
                ['Bond Rate', cfg.bond_rate],
              ].map(([label, value]) => (
                <div key={label as string} className="flex justify-between py-1 border-b border-gray-50">
                  <span className="text-gray-600">{label as string}</span>
                  <span className="font-medium">{pct(value as number)}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
        {!data?.length && (
          <div className="card p-8 text-center text-gray-500 col-span-2">
            <DollarSign size={32} className="mx-auto mb-2 text-gray-300" />
            <p>No overhead configurations yet</p>
          </div>
        )}
      </div>
      {showAdd && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 overflow-auto">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 my-4">
            <h2 className="text-lg font-semibold mb-4">New Overhead Config</h2>
            <form onSubmit={(e) => { e.preventDefault(); create.mutate(form) }} className="space-y-3">
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Config name" className="w-full border rounded-lg px-3 py-2 text-sm" />
              <p className="text-xs font-semibold text-gray-600 uppercase">Labor Burden</p>
              {(['fica_rate', 'futa_rate', 'suta_rate', 'workers_comp_rate', 'general_liability_rate', 'health_insurance_rate', 'vacation_rate'] as const).map(key => (
                <div key={key} className="flex items-center justify-between">
                  <label className="text-sm text-gray-700 capitalize">{key.replace(/_rate$/, '').replace(/_/g, ' ')}</label>
                  <div className="flex items-center gap-1">
                    <input type="number" step="0.001" min="0" max="1" value={form[key]} onChange={(e) => setForm({ ...form, [key]: parseFloat(e.target.value) })} className="w-20 border rounded px-2 py-1 text-sm text-right" />
                    <span className="text-xs text-gray-500">{pct(form[key])}</span>
                  </div>
                </div>
              ))}
              <p className="text-xs font-semibold text-gray-600 uppercase mt-2">Markup</p>
              {(['material_markup', 'general_overhead_rate', 'profit_margin', 'contingency_rate', 'bond_rate', 'permit_rate'] as const).map(key => (
                <div key={key} className="flex items-center justify-between">
                  <label className="text-sm text-gray-700 capitalize">{key.replace(/_rate$/, '').replace(/_/g, ' ')}</label>
                  <div className="flex items-center gap-1">
                    <input type="number" step="0.001" min="0" max="1" value={form[key]} onChange={(e) => setForm({ ...form, [key]: parseFloat(e.target.value) })} className="w-20 border rounded px-2 py-1 text-sm text-right" />
                    <span className="text-xs text-gray-500">{pct(form[key])}</span>
                  </div>
                </div>
              ))}
              <div className="flex gap-2 pt-2">
                <button type="button" onClick={() => setShowAdd(false)} className="btn-secondary flex-1">Cancel</button>
                <button type="submit" className="btn-primary flex-1">Save</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
