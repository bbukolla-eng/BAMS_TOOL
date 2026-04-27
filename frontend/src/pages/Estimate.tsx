import { useParams, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import api from '@/api/client'
import {
  Plus, Download, Calculator, BarChart3, ListChecks,
} from 'lucide-react'
import { downloadBlob } from '@/utils/download'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'

const CHART_COLORS = ['#1d4ed8', '#0891b2', '#16a34a', '#ca8a04', '#dc2626', '#9333ea']

const fmt = (n: number) =>
  `$${(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}`

const fmtInt = (n: number) =>
  `$${(n || 0).toLocaleString('en-US', { minimumFractionDigits: 0 })}`

// ─── Line Items tab ───────────────────────────────────────────────────────────

function LineItemsTab({
  projectId,
  selectedBidId,
  setSelectedBidId,
  bids,
}: {
  projectId: string
  selectedBidId: number | null
  setSelectedBidId: (id: number) => void
  bids: any[]
}) {
  const qc = useQueryClient()

  const { data: bidDetail } = useQuery({
    queryKey: ['bid', selectedBidId],
    queryFn: () => api.get(`/bids/${selectedBidId}`).then((r) => r.data),
    enabled: !!selectedBidId,
  })

  const createBid = useMutation({
    mutationFn: () =>
      api.post('/bids/', {
        project_id: parseInt(projectId),
        name: `Bid v${(bids?.length || 0) + 1}`,
      }),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['bids', projectId] })
      setSelectedBidId(res.data.id)
    },
  })

  const importTakeoff = useMutation({
    mutationFn: (bidId: number) => api.post(`/bids/${bidId}/import-takeoff`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['bid', selectedBidId] }),
  })

  const calculate = useMutation({
    mutationFn: (bidId: number) => api.post(`/bids/${bidId}/calculate`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['bid', selectedBidId] }),
  })

  const bid = bidDetail

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          {bids.length > 0 && (
            <select
              value={selectedBidId || ''}
              onChange={(e) => setSelectedBidId(parseInt(e.target.value))}
              className="border rounded-lg px-2 py-1.5 text-sm"
            >
              <option value="">Select bid…</option>
              {bids.map((b: any) => (
                <option key={b.id} value={b.id}>
                  {b.name} ({b.status})
                </option>
              ))}
            </select>
          )}
        </div>
        <div className="flex gap-2">
          {selectedBidId && (
            <>
              <button
                onClick={() => importTakeoff.mutate(selectedBidId)}
                className="btn-secondary text-sm"
                disabled={importTakeoff.isPending}
              >
                Import Takeoff
              </button>
              <button
                onClick={() => calculate.mutate(selectedBidId)}
                className="btn-secondary text-sm flex items-center gap-1"
                disabled={calculate.isPending}
              >
                <Calculator size={14} /> Calculate
              </button>
              <button
                onClick={() =>
                  downloadBlob(
                    `/bids/${selectedBidId}/export/excel`,
                    `bid_${selectedBidId}.xlsx`,
                  )
                }
                className="btn-secondary text-sm flex items-center gap-1"
              >
                <Download size={14} /> Export Excel
              </button>
            </>
          )}
          <button
            onClick={() => createBid.mutate()}
            className="btn-primary flex items-center gap-2"
          >
            <Plus size={16} /> New Bid
          </button>
        </div>
      </div>

      {bid ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 card overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-100 font-semibold text-gray-900">
              Line Items
            </div>
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
                      <td className="px-3 py-2 text-right font-medium">
                        {fmt(li.line_total)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

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
              <div
                key={label as string}
                className="flex justify-between py-1.5 text-sm"
              >
                <span className="text-gray-600">{label as string}</span>
                <span className="font-medium">{fmt(value as number)}</span>
              </div>
            ))}
            <div className="border-t-2 border-blue-700 mt-3 pt-3 flex justify-between">
              <span className="font-bold text-gray-900">GRAND TOTAL</span>
              <span className="font-bold text-xl text-blue-700">
                {fmt(bid.grand_total)}
              </span>
            </div>
          </div>
        </div>
      ) : (
        <div className="card p-12 text-center text-gray-500">
          <Calculator size={40} className="mx-auto mb-3 text-gray-300" />
          <p>Create or select a bid to get started</p>
        </div>
      )}
    </>
  )
}

// ─── Summary Charts tab ───────────────────────────────────────────────────────

function SummaryTab({
  selectedBidId,
  setSelectedBidId,
  bids,
}: {
  selectedBidId: number | null
  setSelectedBidId: (id: number) => void
  bids: any[]
}) {
  const { data: bid } = useQuery<any>({
    queryKey: ['bid', selectedBidId],
    queryFn: () => api.get(`/bids/${selectedBidId}`).then((r) => r.data),
    enabled: !!selectedBidId,
  })

  const categoryTotals: Record<string, number> = {}
  for (const li of (bid?.line_items || []) as any[]) {
    const cat = li.category || 'other'
    categoryTotals[cat] = (categoryTotals[cat] || 0) + (li.line_total || 0)
  }
  const chartData = Object.entries(categoryTotals)
    .map(([name, value]) => ({ name: name.replace(/_/g, ' '), value }))
    .sort((a, b) => b.value - a.value)

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <div className="flex gap-2 items-center">
          <select
            value={selectedBidId || ''}
            onChange={(e) => setSelectedBidId(parseInt(e.target.value))}
            className="border rounded-lg px-3 py-2 text-sm"
          >
            {bids.map((b: any) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </select>
          {selectedBidId && (
            <button
              onClick={() =>
                downloadBlob(
                  `/bids/${selectedBidId}/export/excel`,
                  `bid_${selectedBidId}.xlsx`,
                )
              }
              className="btn-secondary flex items-center gap-1 text-sm"
            >
              <Download size={14} /> Export
            </button>
          )}
        </div>
      </div>

      {bid ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="card p-5">
            <h3 className="font-semibold text-gray-900 mb-4">Cost by Category</h3>
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 60 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} angle={-30} textAnchor="end" />
                  <YAxis tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v: any) => fmtInt(v)} />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                    {chartData.map((_, i) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-500 text-sm text-center py-8">No line items yet</p>
            )}
          </div>

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
                <div
                  key={label as string}
                  className={`flex justify-between py-1.5 text-sm ${
                    bold ? 'border-t border-gray-200 mt-2 pt-3 font-semibold' : ''
                  }`}
                >
                  <span className={bold ? 'text-gray-900' : 'text-gray-600'}>
                    {label as string}
                  </span>
                  <span className={bold ? 'font-bold text-gray-900' : 'font-medium'}>
                    {fmtInt(value as number)}
                  </span>
                </div>
              ))}
              <div className="flex justify-between py-2 text-base border-t-2 border-blue-700 mt-3">
                <span className="font-bold text-gray-900">GRAND TOTAL</span>
                <span className="font-bold text-xl text-blue-700">
                  {fmtInt(bid.grand_total)}
                </span>
              </div>
            </div>
          </div>

          <div className="card p-5">
            <h3 className="font-semibold text-gray-900 mb-3">Labor Summary</h3>
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Total Labor Hours</span>
              <span className="font-bold">{(bid.total_labor_hours || 0).toFixed(1)} hrs</span>
            </div>
            <div className="flex justify-between text-sm mt-2">
              <span className="text-gray-600">Total Labor Cost</span>
              <span className="font-bold">{fmtInt(bid.total_labor_cost)}</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="card p-12 text-center text-gray-500">
          <BarChart3 size={40} className="mx-auto mb-3 text-gray-300" />
          <p>Create a bid to see the summary</p>
        </div>
      )}
    </>
  )
}

// ─── Page shell ───────────────────────────────────────────────────────────────

export default function EstimatePage() {
  const { id: projectId } = useParams<{ id: string }>()
  const [params, setParams] = useSearchParams()
  const tab = params.get('tab') === 'summary' ? 'summary' : 'line-items'
  const bidParam = params.get('bid')
  const selectedBidId = bidParam ? parseInt(bidParam) : null

  const { data: bids } = useQuery<any[]>({
    queryKey: ['bids', projectId],
    queryFn: () => api.get(`/bids/project/${projectId}`).then((r) => r.data.items),
  })

  // First-load default: pick the latest bid if none chosen via URL
  useEffect(() => {
    if (!selectedBidId && bids?.length) {
      const next = new URLSearchParams(params)
      next.set('bid', String(bids[0].id))
      setParams(next, { replace: true })
    }
  }, [bids, selectedBidId, params, setParams])

  const setSelectedBidId = (id: number) => {
    const next = new URLSearchParams(params)
    if (id) next.set('bid', String(id))
    else next.delete('bid')
    setParams(next, { replace: true })
  }

  const setTab = (next: 'line-items' | 'summary') => {
    const newParams = new URLSearchParams(params)
    if (next === 'line-items') newParams.delete('tab')
    else newParams.set('tab', next)
    setParams(newParams, { replace: true })
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold text-gray-900">Estimate</h1>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200 mb-6">
        <button
          onClick={() => setTab('line-items')}
          className={`px-4 py-2 text-sm font-medium transition-colors -mb-px border-b-2 ${
            tab === 'line-items'
              ? 'text-blue-700 border-blue-700'
              : 'text-gray-500 border-transparent hover:text-gray-700'
          }`}
        >
          <ListChecks size={14} className="inline -mt-0.5 mr-1.5" /> Line Items
        </button>
        <button
          onClick={() => setTab('summary')}
          className={`px-4 py-2 text-sm font-medium transition-colors -mb-px border-b-2 ${
            tab === 'summary'
              ? 'text-blue-700 border-blue-700'
              : 'text-gray-500 border-transparent hover:text-gray-700'
          }`}
        >
          <BarChart3 size={14} className="inline -mt-0.5 mr-1.5" /> Summary Charts
        </button>
      </div>

      {tab === 'line-items' ? (
        <LineItemsTab
          projectId={projectId!}
          selectedBidId={selectedBidId}
          setSelectedBidId={setSelectedBidId}
          bids={bids || []}
        />
      ) : (
        <SummaryTab
          selectedBidId={selectedBidId}
          setSelectedBidId={setSelectedBidId}
          bids={bids || []}
        />
      )}
    </div>
  )
}
