import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import api from '@/api/client'
import { Plus, Wrench, CheckCircle, XCircle } from 'lucide-react'

export default function EquipmentPage() {
  const { id: projectId } = useParams<{ id: string }>()
  const qc = useQueryClient()
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({ tag: '', equipment_type: 'ahu', description: '', manufacturer: '', model_number: '', floor: '', room: '', location_description: '' })

  const { data } = useQuery({
    queryKey: ['equipment', projectId],
    queryFn: () => api.get(`/equipment/project/${projectId}`).then((r) => r.data),
  })

  const create = useMutation({
    mutationFn: (d: typeof form) => api.post('/equipment/', { project_id: parseInt(projectId!), ...d }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['equipment', projectId] }); setShowAdd(false) },
  })

  const toggleInstalled = useMutation({
    mutationFn: ({ id, is_installed }: { id: number; is_installed: boolean }) =>
      api.patch(`/equipment/${id}`, { is_installed }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['equipment', projectId] }),
  })

  const items = data?.items || []
  const summary = data?.summary || {}

  const HVAC_TYPES = ['ahu', 'fcu', 'vav_box', 'diffuser_supply', 'diffuser_return', 'exhaust_fan', 'inline_fan', 'pump', 'boiler', 'chiller', 'cooling_tower', 'heat_exchanger', 'vrf_indoor', 'vrf_outdoor', 'thermostat', 'other']

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Equipment Schedule</h1>
        <button onClick={() => setShowAdd(true)} className="btn-primary flex items-center gap-2">
          <Plus size={16} /> Add Equipment
        </button>
      </div>

      {/* Summary by type */}
      {Object.keys(summary).length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {Object.entries(summary).map(([type, s]: [string, any]) => (
            <div key={type} className="card px-3 py-2 text-sm">
              <span className="font-medium capitalize">{type.replace(/_/g, ' ')}</span>
              <span className="text-gray-500 ml-2">{s.total} total</span>
              {s.installed > 0 && <span className="text-green-600 ml-1">· {s.installed} installed</span>}
            </div>
          ))}
        </div>
      )}

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="table-header">
            <tr>
              <th className="px-4 py-3 text-left">Tag</th>
              <th className="px-4 py-3 text-left">Type</th>
              <th className="px-4 py-3 text-left">Description</th>
              <th className="px-4 py-3 text-left">Manufacturer / Model</th>
              <th className="px-4 py-3 text-left">Location</th>
              <th className="px-4 py-3 text-center">Approved</th>
              <th className="px-4 py-3 text-center">Installed</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {items.map((eq: any) => (
              <tr key={eq.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono font-medium text-blue-700">{eq.tag || '—'}</td>
                <td className="px-4 py-3 text-gray-500 capitalize text-xs">{eq.equipment_type.replace(/_/g, ' ')}</td>
                <td className="px-4 py-3 text-gray-900">{eq.description}</td>
                <td className="px-4 py-3 text-gray-500 text-xs">
                  {eq.manufacturer || '—'} {eq.model_number ? `/ ${eq.model_number}` : ''}
                </td>
                <td className="px-4 py-3 text-gray-500 text-xs">
                  {[eq.floor && `Fl. ${eq.floor}`, eq.room, eq.location_description].filter(Boolean).join(' · ')}
                </td>
                <td className="px-4 py-3 text-center">
                  {eq.is_approved ? <CheckCircle size={16} className="mx-auto text-green-500" /> : <XCircle size={16} className="mx-auto text-gray-300" />}
                </td>
                <td className="px-4 py-3 text-center">
                  <button onClick={() => toggleInstalled.mutate({ id: eq.id, is_installed: !eq.is_installed })}>
                    {eq.is_installed ? <CheckCircle size={16} className="mx-auto text-green-500" /> : <XCircle size={16} className="mx-auto text-gray-300" />}
                  </button>
                </td>
              </tr>
            ))}
            {!items.length && (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                <Wrench size={28} className="mx-auto mb-2 text-gray-300" />
                No equipment added yet
              </td></tr>
            )}
          </tbody>
        </table>
      </div>

      {showAdd && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-lg font-semibold mb-4">Add Equipment</h2>
            <form onSubmit={(e) => { e.preventDefault(); create.mutate(form) }} className="space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <input value={form.tag} onChange={(e) => setForm({ ...form, tag: e.target.value })} placeholder="Tag (e.g. AHU-1)" className="border rounded-lg px-3 py-2 text-sm" />
                <select value={form.equipment_type} onChange={(e) => setForm({ ...form, equipment_type: e.target.value })} className="border rounded-lg px-3 py-2 text-sm">
                  {HVAC_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
                </select>
              </div>
              <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Description *" required className="w-full border rounded-lg px-3 py-2 text-sm" />
              <div className="grid grid-cols-2 gap-2">
                <input value={form.manufacturer} onChange={(e) => setForm({ ...form, manufacturer: e.target.value })} placeholder="Manufacturer" className="border rounded-lg px-3 py-2 text-sm" />
                <input value={form.model_number} onChange={(e) => setForm({ ...form, model_number: e.target.value })} placeholder="Model #" className="border rounded-lg px-3 py-2 text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <input value={form.floor} onChange={(e) => setForm({ ...form, floor: e.target.value })} placeholder="Floor" className="border rounded-lg px-3 py-2 text-sm" />
                <input value={form.room} onChange={(e) => setForm({ ...form, room: e.target.value })} placeholder="Room" className="border rounded-lg px-3 py-2 text-sm" />
              </div>
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
