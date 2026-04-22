import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, useRef } from 'react'
import api from '@/api/client'
import { Upload, FileImage, Clock, CheckCircle, AlertCircle, Eye } from 'lucide-react'

const STATUS_ICON: Record<string, React.ReactNode> = {
  done: <CheckCircle size={14} className="text-green-500" />,
  processing: <Clock size={14} className="text-yellow-500 animate-spin" />,
  error: <AlertCircle size={14} className="text-red-500" />,
  pending: <Clock size={14} className="text-gray-400" />,
}

export default function DrawingsPage() {
  const { id: projectId } = useParams<{ id: string }>()
  const qc = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [discipline, setDiscipline] = useState('mechanical')

  const { data } = useQuery({
    queryKey: ['drawings', projectId],
    queryFn: () => api.get(`/drawings/project/${projectId}`).then((r) => r.data.items),
    refetchInterval: 5000,
  })

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    const form = new FormData()
    form.append('file', file)
    form.append('discipline', discipline)
    try {
      await api.post(`/drawings/project/${projectId}`, form, { headers: { 'Content-Type': 'multipart/form-data' } })
      qc.invalidateQueries({ queryKey: ['drawings', projectId] })
    } finally {
      setUploading(false)
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

      {drawings.length === 0 ? (
        <div className="card p-12 text-center">
          <FileImage size={40} className="mx-auto mb-3 text-gray-300" />
          <p className="text-gray-500 text-sm">No drawings yet. Upload PDF, DWG, or DXF files.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {drawings.map((d: any) => (
            <div key={d.id} className="card p-4">
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  {STATUS_ICON[d.processing_status]}
                  <span className="text-xs text-gray-500 capitalize">{d.discipline}</span>
                </div>
                <span className="text-xs text-gray-400 uppercase font-mono">{d.file_type}</span>
              </div>
              <h3 className="font-medium text-gray-900 text-sm mt-1">{d.name}</h3>
              <p className="text-xs text-gray-500 mt-0.5">{d.original_filename}</p>
              {d.file_size_bytes && <p className="text-xs text-gray-400 mt-1">{(d.file_size_bytes / 1024 / 1024).toFixed(1)} MB · {d.page_count} page{d.page_count !== 1 ? 's' : ''}</p>}
              {d.processing_status === 'error' && d.processing_error && (
                <p className="text-xs text-red-500 mt-1 truncate">{d.processing_error}</p>
              )}
              <div className="mt-3 flex gap-2">
                <Link to={`${d.id}`} className="btn-secondary text-xs flex items-center gap-1 flex-1 justify-center">
                  <Eye size={12} /> View
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
