import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import api from '@/api/client'
import { useState, useEffect } from 'react'
import { BarChart3, Download } from 'lucide-react'
import { downloadBlob } from '@/utils/download'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'

const COLORS = ['#1d4ed8', '#0891b2', '#16a34a', '#ca8a04', '#dc2626', '#9333ea']

export default function BidSummaryPage() {
  const { id: projectId } = useParams<{ id: string }>()
  const [selectedBid, setSelectedBid] = useState<number | null>(null)

  const { data: bids } = useQuery<any[]>({
    queryKey: ['bids', projectId],
    queryFn: () => api.get(`/bids/project/${projectId}`).then(r => r.data.items),
  })

  useEffect(() => {
    if (bids?.length && !selectedBid) setSelectedBid(bids[0].id)
  }, [bids])

  const { data: bid } = useQuery<any>({
    queryKey: ['bid', selectedBid],
    queryFn: () => api.get(`/bids/${selectedBid}`).then(r => r.data),
    enabled: !!selectedBid,
  })

  const fmt = (n: number) => `$${(n || 0).toLocaleString('en-US', { minimumFractionDigits: 0 })}`

  // Build chart data from line items grouped by category
  const categoryTotals: Record<string, number> = {}
  for (const li of (bid?.line_items || []) as any[]) {
    const cat = li.category || 'other'
    categoryTotals[cat] = (categoryTotals[cat] || 0) + (li.line_total || 0)
  }
  const chartData = Object.entries(categoryTotals).map(([name, value]) => ({ name: name.replace(/_/g, ' '), value })).sort((a, b) => b.value - a.value)

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Bid Summary</h1>
        <div className="flex gap-2 items-center">
          <select value={selectedBid || ''} onChange={(e) => setSelectedBid(parseInt(e.target.value))} className="border rounded-lg px-3 py-2 text-sm">
            {(bids || []).map((b: any) => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
          {selectedBid && (
            <button onClick={() => downloadBlob(`/bids/${selectedBid}/export/excel`, `bid_${selectedBid}.xlsx`)} className="btn-secondary flex items-center gap-1 text-sm">
              <Download size={14} /> Export
            </button>
          )}
        </div>
      </div>

      {bid ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Cost breakdown chart */}
          <div className="card p-5">
            <h3 className="font-semibold text-gray-900 mb-4">Cost by Category</h3>
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 60 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} angle={-30} textAnchor="end" />
                  <YAxis tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v: any) => fmt(v)} />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                    {chartData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : <p className="text-gray-500 text-sm text-center py-8">No line items yet</p>}
          </div>

          {/* Bid summary table */}
          <div className="card p-5">
            <h3 className="font-semibold text-gray-900 mb-4">Cost Summary</h3>
            <div className="space-y-1">
              {[
                ['Material Cost', bid.total_material_cost, false],
                ['Material Markup', bid.total_material_markup, false],
                ['Labor Cost', bid.total_labor_cost, false],
                ['Labor Burden', bid.total_burden, false],
                ['General Overhead', bid.total_overhead, false],
                ['Subtotal', bid.subtotal, true],
                ['Contingency', bid.contingency, false],
                ['Bond', bid.bond, false],
                ['Permit & Fees', bid.permit, false],
                ['Profit', bid.profit, false],
              ].map(([label, value, bold]) => (
                <div key={label as string} className={`flex justify-between py-1.5 text-sm ${bold ? 'border-t border-gray-200 mt-2 pt-3 font-semibold' : ''}`}>
                  <span className={bold ? 'text-gray-900' : 'text-gray-600'}>{label as string}</span>
                  <span className={bold ? 'font-bold text-gray-900' : 'font-medium'}>{fmt(value as number)}</span>
                </div>
              ))}
              <div className="flex justify-between py-2 text-base border-t-2 border-blue-700 mt-3">
                <span className="font-bold text-gray-900">GRAND TOTAL</span>
                <span className="font-bold text-xl text-blue-700">{fmt(bid.grand_total)}</span>
              </div>
            </div>
          </div>

          {/* Labor hours */}
          <div className="card p-5">
            <h3 className="font-semibold text-gray-900 mb-3">Labor Summary</h3>
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Total Labor Hours</span>
              <span className="font-bold">{(bid.total_labor_hours || 0).toFixed(1)} hrs</span>
            </div>
            <div className="flex justify-between text-sm mt-2">
              <span className="text-gray-600">Total Labor Cost</span>
              <span className="font-bold">{fmt(bid.total_labor_cost)}</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="card p-12 text-center text-gray-500">
          <BarChart3 size={40} className="mx-auto mb-3 text-gray-300" />
          <p>Create a bid to see the summary</p>
        </div>
      )}
    </div>
  )
}
