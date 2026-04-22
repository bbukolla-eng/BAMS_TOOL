import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, useRef } from 'react'
import api from '@/api/client'
import { Plus, Search, Upload, BookOpen } from 'lucide-react'

export default function PriceBookPage() {
  const qc = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({ category: '', description: '', unit: 'EA', material_unit_cost: 0, labor_hours_per_unit: 0, csi_code: '', size: '' })

  const { data } = useQuery({
    queryKey: ['price-book', search, category],
    queryFn: () => api.get('/price-book/', { params: { search: search || undefined, category: category || undefined } }).then(r => r.data),
  })

  const create = useMutation({
    mutationFn: (d: typeof form) => api.post('/price-book/', d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['price-book'] }); setShowAdd(false) },
  })

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const form = new FormData()
    form.append('file', file)
    await api.post('/price-book/import-excel', form, { headers: { 'Content-Type': 'multipart/form-data' } })
    qc.invalidateQueries({ queryKey: ['price-book'] })
  }

  const categories = [...new Set((data?.items || []).map((i: any) => i.category))].sort()

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Price Book</h1>
        <div className="flex gap-2">
          <input ref={fileRef} type="file" accept=".xlsx,.xls" className="hidden" onChange={handleImport} />
          <button onClick={() => fileRef.current?.click()} className="btn-secondary flex items-center gap-2 text-sm">
            <Upload size={14} /> Import Excel
          </button>
          <button onClick={() => setShowAdd(true)} className="btn-primary flex items-center gap-2">
            <Plus size={16} /> Add Item
          </button>
        </div>
      </div>

      <div className="flex gap-3 mb-4">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search items..." className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm" />
        </div>
        <select value={category} onChange={(e) => setCategory(e.target.value)} className="border rounded-lg px-3 py-2 text-sm">
          <option value="">All categories</option>
          {categories.map((c: any) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="table-header">
            <tr>
              <th className="px-4 py-3 text-left">CSI</th>
              <th className="px-4 py-3 text-left">Description</th>
              <th className="px-4 py-3 text-left">Category</th>
              <th className="px-4 py-3 text-left">Size</th>
              <th className="px-4 py-3 text-left">Unit</th>
              <th className="px-4 py-3 text-right">Material $/Unit</th>
              <th className="px-4 py-3 text-right">Labor Hrs/Unit</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {(data?.items || []).map((item: any) => (
              <tr key={item.id} className="hover:bg-gray-50">
                <td className="px-4 py-2.5 font-mono text-xs text-gray-500">{item.csi_code || '—'}</td>
                <td className="px-4 py-2.5 text-gray-900">{item.description}</td>
                <td className="px-4 py-2.5 text-gray-500 capitalize text-xs">{item.category}</td>
                <td className="px-4 py-2.5 text-gray-500 text-xs">{item.size || '—'}</td>
                <td className="px-4 py-2.5 text-gray-500">{item.unit}</td>
                <td className="px-4 py-2.5 text-right font-medium">${item.material_unit_cost?.toFixed(2)}</td>
                <td className="px-4 py-2.5 text-right text-gray-500">{item.labor_hours_per_unit?.toFixed(3)}</td>
              </tr>
            ))}
            {!data?.items?.length && (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                <BookOpen size={28} className="mx-auto mb-2 text-gray-300" />
                No items yet. Import from Excel or add manually.
              </td></tr>
            )}
          </tbody>
        </table>
      </div>

      {showAdd && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-lg font-semibold mb-4">Add Price Book Item</h2>
            <form onSubmit={(e) => { e.preventDefault(); create.mutate(form) }} className="space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <input value={form.csi_code} onChange={(e) => setForm({ ...form, csi_code: e.target.value })} placeholder="CSI code (e.g. 23 31 13)" className="border rounded-lg px-3 py-2 text-sm" />
                <input value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} placeholder="Category *" required className="border rounded-lg px-3 py-2 text-sm" />
              </div>
              <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Description *" required className="w-full border rounded-lg px-3 py-2 text-sm" />
              <div className="grid grid-cols-3 gap-2">
                <input value={form.size} onChange={(e) => setForm({ ...form, size: e.target.value })} placeholder="Size" className="border rounded-lg px-3 py-2 text-sm" />
                <select value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} className="border rounded-lg px-3 py-2 text-sm">
                  {['EA', 'LF', 'SF', 'LB', 'TON', 'GAL', 'HR'].map(u => <option key={u}>{u}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-xs text-gray-600">Material $/Unit</label>
                  <input type="number" step="0.01" value={form.material_unit_cost} onChange={(e) => setForm({ ...form, material_unit_cost: parseFloat(e.target.value) })} className="w-full border rounded-lg px-3 py-2 text-sm mt-1" />
                </div>
                <div>
                  <label className="text-xs text-gray-600">Labor Hrs/Unit</label>
                  <input type="number" step="0.001" value={form.labor_hours_per_unit} onChange={(e) => setForm({ ...form, labor_hours_per_unit: parseFloat(e.target.value) })} className="w-full border rounded-lg px-3 py-2 text-sm mt-1" />
                </div>
              </div>
              <div className="flex gap-2 pt-2">
                <button type="button" onClick={() => setShowAdd(false)} className="btn-secondary flex-1">Cancel</button>
                <button type="submit" className="btn-primary flex-1">Add Item</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
