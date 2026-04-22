import { useParams, Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, useRef, useEffect } from 'react'
import api from '@/api/client'
import { useJobProgress } from '@/hooks/useJobProgress'
import { Upload, FileImage, Clock, CheckCircle, AlertCircle, Eye, Loader } from 'lucide-react'

function DrawingCard({ d, projectId }: { d: any; projectId: string }) {
  const qc = useQueryClient()
  const isProcessing = d.processing_status === 'processing' || d.processing_status === 'pending'
  const jobKey = isProcessing ? `drawing:${d.id}` : null
  const progress = useJobProgress(jobKey)

  // Refresh list when SSE signals completion
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

export default function DrawingsPage() {
  const { id: projectId } = useParams<{ id: string }>()
  const qc = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [discipline, setDiscipline] = useState('mechanical')

  const { data } = useQuery({
    queryKey: ['drawings', projectId],
    queryFn: () => api.get(`/drawings/project/${projectId}`).then((r) => r.data.items),
    // Only poll if any drawing is still processing; SSE handles live updates
    refetchInterval: (query) => {
      const items: any[] = query.state.data || []
      return items.some((d) => d.processing_status === 'processing' || d.processing_status === 'pending') ? 10000 : false
    },
  })

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

  const drawings = data || []

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Drawings</h1>
        <div className="flex gap-2 items-center">
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
            <DrawingCard key={d.id} d={d} projectId={projectId!} />
          ))}
        </div>
      )}
    </div>
  )
}
