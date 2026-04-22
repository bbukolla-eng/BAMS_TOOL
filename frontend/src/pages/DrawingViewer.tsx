import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import api from '@/api/client'
import { useEffect, useRef, useState } from 'react'
import { ZoomIn, ZoomOut, Layers, CheckSquare } from 'lucide-react'

export default function DrawingViewer() {
  const { id: projectId, drawingId } = useParams<{ id: string; drawingId: string }>()
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [zoom, setZoom] = useState(1)
  const [showSymbols, setShowSymbols] = useState(true)
  const [showRuns, setShowRuns] = useState(true)
  const [selectedPage, setSelectedPage] = useState(1)

  const { data: drawing } = useQuery({
    queryKey: ['drawing', drawingId],
    queryFn: () => api.get(`/drawings/${drawingId}`).then((r) => r.data),
  })

  const { data: drawingUrl } = useQuery({
    queryKey: ['drawing-url', drawingId],
    queryFn: () => api.get(`/drawings/${drawingId}/url`).then((r) => r.data),
  })

  const { data: symbols } = useQuery({
    queryKey: ['symbols', drawingId, selectedPage],
    queryFn: () => api.get(`/drawings/${drawingId}/pages/${selectedPage}/symbols`).then((r) => r.data),
    enabled: !!drawing,
  })

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="h-12 bg-white border-b border-gray-200 flex items-center px-4 gap-3">
        <span className="font-medium text-gray-900 text-sm truncate">{drawing?.name}</span>
        <div className="ml-auto flex items-center gap-2">
          <button onClick={() => setShowSymbols((v) => !v)} className={`flex items-center gap-1 text-xs px-2 py-1 rounded ${showSymbols ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'}`}>
            <CheckSquare size={12} /> Symbols {symbols?.symbols?.length || 0}
          </button>
          <button onClick={() => setShowRuns((v) => !v)} className={`flex items-center gap-1 text-xs px-2 py-1 rounded ${showRuns ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
            <Layers size={12} /> Runs {symbols?.material_runs?.length || 0}
          </button>
          <div className="flex items-center gap-1 border rounded px-2">
            <button onClick={() => setZoom((z) => Math.max(0.25, z - 0.25))}><ZoomOut size={14} /></button>
            <span className="text-xs w-12 text-center">{Math.round(zoom * 100)}%</span>
            <button onClick={() => setZoom((z) => Math.min(4, z + 0.25))}><ZoomIn size={14} /></button>
          </div>
        </div>
      </div>

      {/* Viewer */}
      <div className="flex-1 overflow-auto bg-gray-800 flex items-center justify-center">
        {drawingUrl?.url ? (
          <div className="relative" style={{ transform: `scale(${zoom})`, transformOrigin: 'top left' }}>
            {drawing?.file_type === 'pdf' ? (
              <iframe src={drawingUrl.url} className="w-[1200px] h-[900px]" title="Drawing" />
            ) : (
              <img src={drawingUrl.url} alt="Drawing" className="max-w-none" />
            )}
            {/* Symbol overlays */}
            {showSymbols && symbols?.symbols?.map((sym: any) => (
              <div
                key={sym.id}
                title={`${sym.symbol_type} (${Math.round(sym.confidence * 100)}%)`}
                style={{
                  position: 'absolute',
                  left: `${sym.x * 4}px`,  // approximate px mapping
                  top: `${sym.y * 4}px`,
                  width: `${(sym.width || 2) * 4}px`,
                  height: `${(sym.height || 2) * 4}px`,
                  border: `2px solid ${sym.confidence > 0.8 ? '#22c55e' : sym.confidence > 0.6 ? '#f59e0b' : '#ef4444'}`,
                  borderRadius: '4px',
                  backgroundColor: 'transparent',
                  cursor: 'pointer',
                }}
              />
            ))}
          </div>
        ) : (
          <div className="text-gray-400 text-center">
            {drawing?.processing_status === 'processing' ? (
              <p>Processing drawing... This may take a minute.</p>
            ) : drawing?.processing_status === 'error' ? (
              <p className="text-red-400">Error: {drawing.processing_error}</p>
            ) : (
              <p>Loading drawing...</p>
            )}
          </div>
        )}
      </div>

      {/* Bottom panel - Material runs summary */}
      {symbols?.material_runs?.length > 0 && showRuns && (
        <div className="h-32 bg-white border-t border-gray-200 overflow-auto">
          <table className="w-full text-xs">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-1.5 text-left">Material Type</th>
                <th className="px-3 py-1.5 text-left">Size</th>
                <th className="px-3 py-1.5 text-right">Length (LF)</th>
                <th className="px-3 py-1.5 text-left">Layer</th>
                <th className="px-3 py-1.5 text-center">Confidence</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {symbols.material_runs.map((run: any) => (
                <tr key={run.id} className="hover:bg-gray-50">
                  <td className="px-3 py-1.5 font-medium">{run.material_type}</td>
                  <td className="px-3 py-1.5 text-gray-500">{run.size || '—'}</td>
                  <td className="px-3 py-1.5 text-right font-mono">{run.length_ft.toFixed(1)}</td>
                  <td className="px-3 py-1.5 text-gray-400 font-mono text-xs">{run.layer_name}</td>
                  <td className="px-3 py-1.5 text-center">
                    <span className={run.confidence > 0.85 ? 'text-green-600' : run.confidence > 0.65 ? 'text-yellow-600' : 'text-red-600'}>
                      {Math.round(run.confidence * 100)}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
