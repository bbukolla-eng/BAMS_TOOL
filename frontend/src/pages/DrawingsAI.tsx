import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/api/client'
import { Brain, CheckCircle, AlertTriangle, BarChart3, RefreshCw } from 'lucide-react'

export default function DrawingsAIPage() {
  const { id: projectId } = useParams<{ id: string }>()
  const qc = useQueryClient()

  const { data: drawings } = useQuery({
    queryKey: ['drawings', projectId],
    queryFn: () => api.get(`/drawings/project/${projectId}`).then((r) => r.data.items),
  })

  const { data: accuracy } = useQuery({
    queryKey: ['accuracy'],
    queryFn: () => api.get('/drawings-ai/accuracy-report').then((r) => r.data),
  })

  const reprocess = useMutation({
    mutationFn: (drawingId: number) => api.post('/drawings-ai/reprocess', { drawing_id: drawingId }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['drawings', projectId] }),
  })

  const processed = drawings?.filter((d: any) => d.processing_status === 'done') || []
  const processing = drawings?.filter((d: any) => d.processing_status === 'processing') || []
  const errors = drawings?.filter((d: any) => d.processing_status === 'error') || []

  return (
    <div className="p-6">
      <div className="flex items-center gap-3 mb-6">
        <Brain size={24} className="text-purple-600" />
        <h1 className="text-2xl font-bold text-gray-900">Drawings AI</h1>
      </div>

      {/* Status Summary */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="card p-4 text-center">
          <CheckCircle size={24} className="mx-auto mb-2 text-green-500" />
          <p className="text-2xl font-bold text-gray-900">{processed.length}</p>
          <p className="text-sm text-gray-500">Processed</p>
        </div>
        <div className="card p-4 text-center">
          <RefreshCw size={24} className="mx-auto mb-2 text-yellow-500 animate-spin" style={{ animationPlayState: processing.length > 0 ? 'running' : 'paused' }} />
          <p className="text-2xl font-bold text-gray-900">{processing.length}</p>
          <p className="text-sm text-gray-500">Processing</p>
        </div>
        <div className="card p-4 text-center">
          <AlertTriangle size={24} className="mx-auto mb-2 text-red-500" />
          <p className="text-2xl font-bold text-gray-900">{errors.length}</p>
          <p className="text-sm text-gray-500">Errors</p>
        </div>
      </div>

      {/* Accuracy Report */}
      {accuracy?.training_jobs?.length > 0 && (
        <div className="card mb-6">
          <div className="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
            <BarChart3 size={16} className="text-purple-600" />
            <span className="font-semibold text-gray-900">Model Training History</span>
          </div>
          <table className="w-full text-sm">
            <thead className="table-header">
              <tr>
                <th className="px-4 py-2 text-left">Model</th>
                <th className="px-4 py-2 text-left">Status</th>
                <th className="px-4 py-2 text-right">Feedback Used</th>
                <th className="px-4 py-2 text-right">Baseline mAP50</th>
                <th className="px-4 py-2 text-right">New mAP50</th>
                <th className="px-4 py-2 text-center">Promoted</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {accuracy.training_jobs.map((job: any) => (
                <tr key={job.id}>
                  <td className="px-4 py-2 font-mono text-xs">{job.model_type}</td>
                  <td className="px-4 py-2">{job.status}</td>
                  <td className="px-4 py-2 text-right">{job.feedback_count}</td>
                  <td className="px-4 py-2 text-right">{job.baseline_map50?.toFixed(3) ?? '—'}</td>
                  <td className="px-4 py-2 text-right">{job.new_map50?.toFixed(3) ?? '—'}</td>
                  <td className="px-4 py-2 text-center">{job.was_promoted ? '✓' : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Drawing List with reprocess buttons */}
      <div className="card overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100 font-semibold text-gray-900">All Drawings</div>
        <div className="divide-y divide-gray-100">
          {(drawings || []).map((d: any) => (
            <div key={d.id} className="flex items-center justify-between px-4 py-3">
              <div>
                <p className="text-sm font-medium text-gray-900">{d.name}</p>
                <p className="text-xs text-gray-500">{d.discipline} · {d.processing_status}</p>
              </div>
              <button onClick={() => reprocess.mutate(d.id)} className="btn-secondary text-xs flex items-center gap-1" disabled={d.processing_status === 'processing'}>
                <RefreshCw size={11} /> Reprocess
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
