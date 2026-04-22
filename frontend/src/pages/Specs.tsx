import { useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useRef, useState } from 'react'
import api from '@/api/client'
import { Upload, FileText, ChevronDown, ChevronRight } from 'lucide-react'

export default function SpecsPage() {
  const { id: projectId } = useParams<{ id: string }>()
  const qc = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [selectedSpec, setSelectedSpec] = useState<number | null>(null)
  const [expandedSection, setExpandedSection] = useState<number | null>(null)

  const { data: specs } = useQuery({
    queryKey: ['specs', projectId],
    queryFn: () => api.get(`/specs/project/${projectId}`).then((r) => r.data.items),
  })

  const { data: sections } = useQuery({
    queryKey: ['spec-sections', selectedSpec],
    queryFn: () => api.get(`/specs/${selectedSpec}/sections`).then((r) => r.data.items),
    enabled: !!selectedSpec,
  })

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    const form = new FormData()
    form.append('file', file)
    try {
      const res = await api.post(`/specs/project/${projectId}`, form, { headers: { 'Content-Type': 'multipart/form-data' } })
      qc.invalidateQueries({ queryKey: ['specs', projectId] })
      setSelectedSpec(res.data.id)
    } finally { setUploading(false) }
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Specifications</h1>
        <div>
          <input ref={fileRef} type="file" accept=".pdf" className="hidden" onChange={handleUpload} />
          <button onClick={() => fileRef.current?.click()} disabled={uploading} className="btn-primary flex items-center gap-2">
            <Upload size={16} /> {uploading ? 'Uploading...' : 'Upload Spec PDF'}
          </button>
        </div>
      </div>

      <div className="flex gap-4">
        {/* Spec list */}
        <div className="w-64 shrink-0 space-y-2">
          {(specs || []).map((spec: any) => (
            <button key={spec.id} onClick={() => setSelectedSpec(spec.id)}
              className={`w-full text-left card p-3 transition-colors ${selectedSpec === spec.id ? 'ring-2 ring-blue-500' : ''}`}>
              <div className="flex items-center gap-2 mb-1">
                <FileText size={14} className="text-blue-600 shrink-0" />
                <span className="text-sm font-medium text-gray-900 truncate">{spec.name}</span>
              </div>
              {spec.division && <span className="text-xs text-gray-500">Div. {spec.division}</span>}
              <span className={`ml-2 text-xs ${spec.processing_status === 'done' ? 'text-green-600' : 'text-yellow-600'}`}>
                {spec.processing_status}
              </span>
            </button>
          ))}
          {!specs?.length && <p className="text-sm text-gray-500">Upload spec PDFs to get started</p>}
        </div>

        {/* Sections */}
        <div className="flex-1 card overflow-hidden">
          {!selectedSpec ? (
            <div className="p-8 text-center text-gray-500">Select a spec to view sections</div>
          ) : !sections?.length ? (
            <div className="p-8 text-center text-gray-500">No sections extracted yet</div>
          ) : (
            <div className="divide-y divide-gray-100">
              {sections.map((sec: any) => (
                <div key={sec.id}>
                  <button className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 text-left"
                    onClick={() => setExpandedSection(expandedSection === sec.id ? null : sec.id)}>
                    <div>
                      <span className="font-mono text-xs text-blue-700 mr-2">{sec.section_number}</span>
                      <span className="text-sm font-medium text-gray-900">{sec.section_title}</span>
                    </div>
                    {expandedSection === sec.id ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                  </button>
                  {expandedSection === sec.id && (
                    <div className="px-4 pb-4 bg-gray-50">
                      {sec.structured_data && (
                        <div className="mt-2">
                          {sec.structured_data.materials?.length > 0 && (
                            <div className="mb-3">
                              <p className="text-xs font-semibold text-gray-600 mb-1">MATERIALS</p>
                              {sec.structured_data.materials.map((m: any, i: number) => (
                                <div key={i} className="text-xs text-gray-700 ml-2">• {m.name} {m.size ? `(${m.size})` : ''} {m.standard ? `— ${m.standard}` : ''}</div>
                              ))}
                            </div>
                          )}
                          {sec.structured_data.products?.length > 0 && (
                            <div className="mb-3">
                              <p className="text-xs font-semibold text-gray-600 mb-1">PRODUCTS</p>
                              {sec.structured_data.products.map((p: any, i: number) => (
                                <div key={i} className="text-xs text-gray-700 ml-2">• {p.description} {p.manufacturer_options?.length ? `(${p.manufacturer_options.join(', ')})` : ''}</div>
                              ))}
                            </div>
                          )}
                          {sec.structured_data.standards?.length > 0 && (
                            <div>
                              <p className="text-xs font-semibold text-gray-600 mb-1">STANDARDS</p>
                              <div className="flex flex-wrap gap-1">
                                {sec.structured_data.standards.map((s: string, i: number) => (
                                  <span key={i} className="badge-blue text-xs">{s}</span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
