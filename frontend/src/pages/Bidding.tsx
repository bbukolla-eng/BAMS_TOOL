import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import api from '@/api/client'
import { Plus, Download, Calculator, ChevronDown } from 'lucide-react'
import { downloadBlob } from '@/utils/download'

export default function BiddingPage() {
  const { id: projectId } = useParams<{ id: string }>()
  const qc = useQueryClient()
  const [selectedBidId, setSelectedBidId] = useState<number | null>(null)

  const { data: bids } = useQuery({
    queryKey: ['bids', projectId],
    queryFn: () => api.get(`/bids/project/${projectId}`).then((r) => r.data.items),
  })

  const { data: bidDetail } = useQuery({
    queryKey: ['bid', selectedBidId],
    queryFn: () => api.get(`/bids/${selectedBidId}`).then((r) => r.data),
    enabled: !!selectedBidId,
  })

  const createBid = useMutation({
    mutationFn: () => api.post('/bids/', { project_id: parseInt(projectId!), name: `Bid v${(bids?.length || 0) + 1}` }),
    onSuccess: (res) => { qc.invalidateQueries({ queryKey: ['bids', projectId] }); setSelectedBidId(res.data.id) },
  })

  const importTakeoff = useMutation({
    mutationFn: (bidId: number) => api.post(`/bids/${bidId}/import-takeoff`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['bid', selectedBidId] }),
  })

  const calculate = useMutation({
    mutationFn: (bidId: number) => api.post(`/bids/${bidId}/calculate`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['bid', selectedBidId] }),
  })

  const fmt = (n: number) => `$${(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}`

  const bid = bidDetail

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-gray-900">Bidding</h1>
          {bids && bids.length > 0 && (
            <select value={selectedBidId || ''} onChange={(e) => setSelectedBidId(parseInt(e.target.value))}
              className="border rounded-lg px-2 py-1.5 text-sm">
              <option value="">Select bid...</option>
              {bids.map((b: any) => <option key={b.id} value={b.id}>{b.name} ({b.status})</option>)}
            </select>
          )}
        </div>
        <div className="flex gap-2">
          {selectedBidId && (
            <>
              <button onClick={() => importTakeoff.mutate(selectedBidId)} className="btn-secondary text-sm" disabled={importTakeoff.isPending}>
                Import Takeoff
              </button>
              <button onClick={() => calculate.mutate(selectedBidId)} className="btn-secondary text-sm flex items-center gap-1" disabled={calculate.isPending}>
                <Calculator size={14} /> Calculate
              </button>
              <button onClick={() => downloadBlob(`/bids/${selectedBidId}/export/excel`, `bid_${selectedBidId}.xlsx`)} className="btn-secondary text-sm flex items-center gap-1">
                <Download size={14} /> Export Excel
              </button>
            </>
          )}
          <button onClick={() => createBid.mutate()} className="btn-primary flex items-center gap-2">
            <Plus size={16} /> New Bid
          </button>
        </div>
      </div>

      {bid ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Line Items */}
          <div className="lg:col-span-2 card overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-100 font-semibold text-gray-900">Line Items</div>
            <div className="overflow-auto max-h-[60vh]">
              <table className="w-full text-sm">
                <thead className="table-header sticky top-0">
                  <tr>
                    <th className="px-3 py-2 text-left">Description</th>
                    <th className="px-3 py-2 text-right">Qty</th>
                    <th className="px-3 py-2 text-left">Unit</th>
                    <th className="px-3 py-2 text-right">Material</th>
                    <th className="px-3 py-2 text-right">Labor</th>
                    <th className="px-3 py-2 text-right">Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {(bid.line_items || []).map((li: any) => (
                    <tr key={li.id} className="hover:bg-gray-50">
                      <td className="px-3 py-2 text-gray-900">{li.description}</td>
                      <td className="px-3 py-2 text-right">{li.quantity?.toFixed(2)}</td>
                      <td className="px-3 py-2 text-gray-500">{li.unit}</td>
                      <td className="px-3 py-2 text-right">{fmt(li.material_total)}</td>
                      <td className="px-3 py-2 text-right">{fmt(li.labor_total)}</td>
                      <td className="px-3 py-2 text-right font-medium">{fmt(li.line_total)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Bid Summary */}
          <div className="card p-5 h-fit">
            <h3 className="font-semibold text-gray-900 mb-4">Bid Summary</h3>
            {[
              ['Material Cost', bid.total_material_cost],
              ['Material Markup', bid.total_material_markup],
              ['Labor Cost', bid.total_labor_cost],
              ['Labor Burden', bid.total_burden],
              ['Overhead', bid.total_overhead],
              ['Subtotal', bid.subtotal],
              ['Contingency', bid.contingency],
              ['Bond', bid.bond],
              ['Permit & Fees', bid.permit],
              ['Profit', bid.profit],
            ].map(([label, value]) => (
              <div key={label as string} className="flex justify-between py-1.5 text-sm">
                <span className="text-gray-600">{label as string}</span>
                <span className="font-medium">{fmt(value as number)}</span>
              </div>
            ))}
            <div className="border-t-2 border-blue-700 mt-3 pt-3 flex justify-between">
              <span className="font-bold text-gray-900">GRAND TOTAL</span>
              <span className="font-bold text-xl text-blue-700">{fmt(bid.grand_total)}</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="card p-12 text-center text-gray-500">
          <Calculator size={40} className="mx-auto mb-3 text-gray-300" />
          <p>Create or select a bid to get started</p>
        </div>
      )}
    </div>
  )
}
