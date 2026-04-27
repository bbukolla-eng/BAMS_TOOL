import { useParams, Link, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, useRef, useEffect } from 'react'
import api from '@/api/client'
import { useJobProgress } from '@/hooks/useJobProgress'
import {
  Upload, FileImage, Clock, CheckCircle, AlertCircle, Eye, Loader,
  Brain, AlertTriangle, BarChart3, RefreshCw,
} from 'lucide-react'

// ─── Drawing card (used by Upload tab) ────────────────────────────────────────

function DrawingCard({ d, projectId }: { d: any; projectId: string }) {
  const qc = useQueryClient()
  const isProcessing = d.processing_status === 'processing' || d.processing_status === 'pending'
  const jobKey = isProcessing ? `drawing:${d.id}` : null
  const progress = useJobProgress(jobKey)

  useEffect(() => {
    if (progress?.stage === 'done' || progress?.stage === 'error') {
      qc.invalidateQueries({ queryKey: ['drawings', projectId] })
    }
  }, [progress?.stage, qc, projectId])

  const statusIcon = () => {
    if (d.processing_status === 'done') return <CheckCircle size={14} className="text-green-500" />
    if (d.processing_status === 'error') return <AlertCircle size={14} className="text-red-500" />
    if (isProcessing) return <Loader size={14} className="text-yellow-500 animate-spin" />
    return <Clock size={14} className="text-gray-400" />
  }

  return (
    <div className="card p-4">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          {statusIcon()}
          <span className="text-xs text-gray-500 capitalize">{d.discipline}</span>
        </div>
        <span className="text-xs text-gray-400 uppercase font-mono">{d.file_type}</span>
      </div>
      <h3 className="font-medium text-gray-900 text-sm mt-1">{d.name}</h3>
      <p className="text-xs text-gray-500 mt-0.5">{d.original_filename}</p>
      {d.file_size_bytes && (
        <p className="text-xs text-gray-400 mt-1">
          {(d.file_size_bytes / 1024 / 1024).toFixed(1)} MB · {d.page_count} page{d.page_count !== 1 ? 's' : ''}
        </p>
      )}
      {isProcessing && progress && (
        <div className="mt-2">
          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 transition-all duration-300"
              style={{ width: `${progress.pct ?? 0}%` }}
            />
          </div>
          {progress.message && <p className="text-xs text-gray-500 mt-1">{progress.message}</p>}
        </div>
      )}
      {d.processing_status === 'error' && d.processing_error && (
        <p className="text-xs text-red-500 mt-1 truncate">{d.processing_error}</p>
      )}
      <div className="mt-3 flex gap-2">
        <Link to={`${d.id}`} className="btn-secondary text-xs flex items-center gap-1 flex-1 justify-center">
          <Eye size={12} /> View
        </Link>
      </div>
    </div>
  )
}

// ─── Upload tab ───────────────────────────────────────────────────────────────

function UploadTab({ projectId, drawings }: { projectId: string; drawings: any[] }) {
  const qc = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [discipline, setDiscipline] = useState('mechanical')

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setUploadError(null)
    const form = new FormData()
    form.append('file', file)
    form.append('discipline', discipline)
    try {
      await api.post(`/drawings/project/${projectId}`, form, { headers: { 'Content-Type': 'multipart/form-data' } })
      qc.invalidateQueries({ queryKey: ['drawings', projectId] })
    } catch (err: any) {
      setUploadError(err?.response?.data?.detail || 'Upload failed. Please try again.')
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  return (
    <>
      <div className="flex items-center justify-end gap-2 mb-4">
        <select value={discipline} onChange={(e) => setDiscipline(e.target.value)} className="border rounded-lg px-3 py-2 text-sm">
          <option value="mechanical">Mechanical</option>
          <option value="electrical">Electrical</option>
          <option value="plumbing">Plumbing</option>
          <option value="fire_protection">Fire Protection</option>
          <option value="architectural">Architectural</option>
        </select>
        <input ref={fileRef} type="file" accept=".pdf,.dwg,.dxf,.png,.jpg,.tiff" className="hidden" onChange={handleUpload} />
        <button onClick={() => fileRef.current?.click()} disabled={uploading} className="btn-primary flex items-center gap-2">
          <Upload size={16} /> {uploading ? 'Uploading...' : 'Upload Drawing'}
        </button>
      </div>

      {uploadError && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{uploadError}</div>
      )}

      {drawings.length === 0 ? (
        <div className="card p-12 text-center">
          <FileImage size={40} className="mx-auto mb-3 text-gray-300" />
          <p className="text-gray-500 text-sm">No drawings yet. Upload PDF, DWG, or DXF files.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {drawings.map((d: any) => (
            <DrawingCard key={d.id} d={d} projectId={projectId} />
          ))}
        </div>
      )}
    </>
  )
}

// ─── AI Processing tab ────────────────────────────────────────────────────────

function AIProcessingTab({ projectId, drawings }: { projectId: string; drawings: any[] }) {
  const qc = useQueryClient()

  const { data: accuracy } = useQuery({
    queryKey: ['accuracy'],
    queryFn: () => api.get('/drawings-ai/accuracy-report').then((r) => r.data),
  })

  const reprocess = useMutation({
    mutationFn: (drawingId: number) => api.post('/drawings-ai/reprocess', { drawing_id: drawingId }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['drawings', projectId] }),
  })

  const processed = drawings.filter((d: any) => d.processing_status === 'done')
  const processing = drawings.filter((d: any) => d.processing_status === 'processing')
  const errors = drawings.filter((d: any) => d.processing_status === 'error')

  return (
    <>
      {/* Status summary */}
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

      {/* Accuracy report */}
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

      {/* Drawings with reprocess controls */}
      <div className="card overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100 font-semibold text-gray-900">All Drawings</div>
        <div className="divide-y divide-gray-100">
          {drawings.length === 0 && (
            <div className="px-4 py-8 text-center text-sm text-gray-500">
              No drawings yet — upload some on the Upload tab.
            </div>
          )}
          {drawings.map((d: any) => (
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
    </>
  )
}

// ─── Page shell ───────────────────────────────────────────────────────────────

export default function DrawingsPage() {
  const { id: projectId } = useParams<{ id: string }>()
  const [params, setParams] = useSearchParams()
  const tab = params.get('tab') === 'ai' ? 'ai' : 'upload'

  const { data } = useQuery({
    queryKey: ['drawings', projectId],
    queryFn: () => api.get(`/drawings/project/${projectId}`).then((r) => r.data.items),
    refetchInterval: (query) => {
      const items: any[] = query.state.data || []
      return items.some((d) => d.processing_status === 'processing' || d.processing_status === 'pending') ? 10000 : false
    },
  })

  const drawings = data || []

  const setTab = (next: 'upload' | 'ai') => {
    const newParams = new URLSearchParams(params)
    if (next === 'upload') newParams.delete('tab')
    else newParams.set('tab', next)
    setParams(newParams, { replace: true })
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold text-gray-900">Drawings</h1>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200 mb-6">
        <button
          onClick={() => setTab('upload')}
          className={`px-4 py-2 text-sm font-medium transition-colors -mb-px border-b-2 ${
            tab === 'upload' ? 'text-blue-700 border-blue-700' : 'text-gray-500 border-transparent hover:text-gray-700'
          }`}
        >
          <FileImage size={14} className="inline -mt-0.5 mr-1.5" /> Upload
        </button>
        <button
          onClick={() => setTab('ai')}
          className={`px-4 py-2 text-sm font-medium transition-colors -mb-px border-b-2 ${
            tab === 'ai' ? 'text-purple-700 border-purple-700' : 'text-gray-500 border-transparent hover:text-gray-700'
          }`}
        >
          <Brain size={14} className="inline -mt-0.5 mr-1.5" /> AI Processing
        </button>
      </div>

      {tab === 'upload' ? (
        <UploadTab projectId={projectId!} drawings={drawings} />
      ) : (
        <AIProcessingTab projectId={projectId!} drawings={drawings} />
      )}
    </div>
  )
}
