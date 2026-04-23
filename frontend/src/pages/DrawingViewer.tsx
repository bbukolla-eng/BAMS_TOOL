import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import api from '@/api/client'
import { useRef, useState } from 'react'
import { ZoomIn, ZoomOut, Layers, CheckSquare, AlertCircle } from 'lucide-react'

// Rendered iframe dimensions for PDF pages
const IFRAME_W = 1200
const IFRAME_H = 900

/** Convert a symbol's real-world foot coordinates to iframe pixels.
 *
 * Symbols are stored in feet relative to the drawing page's coordinate
 * system (origin top-left, x right, y down).  We map them linearly onto
 * the fixed 1200×900 iframe using the page's known dimensions in feet.
 * If the page dimensions are missing we fall back to a neutral 100ft×77ft
 * estimate that approximates a typical architectural sheet at 1/8"=1'-0".
 */
function feetToPx(
  valueFt: number,
  axis: 'x' | 'y',
  pageWidthFt: number,
  pageHeightFt: number,
): number {
  const fallbackW = 100 // ft — typical half-size arch sheet at 1/8"=1'
  const fallbackH = 77
  const wFt = pageWidthFt > 0 ? pageWidthFt : fallbackW
  const hFt = pageHeightFt > 0 ? pageHeightFt : fallbackH
  return axis === 'x' ? (valueFt / wFt) * IFRAME_W : (valueFt / hFt) * IFRAME_H
}

function confidenceColor(conf: number): string {
  if (conf > 0.8) return '#22c55e'
  if (conf > 0.6) return '#f59e0b'
  return '#ef4444'
}

export default function DrawingViewer() {
  const { id: projectId, drawingId } = useParams<{ id: string; drawingId: string }>()
  const [zoom, setZoom] = useState(1)
  const [showSymbols, setShowSymbols] = useState(true)
  const [showRuns, setShowRuns] = useState(true)
  const [selectedPage, setSelectedPage] = useState(1)
  const [selectedSymbol, setSelectedSymbol] = useState<any | null>(null)

  const { data: drawing } = useQuery({
    queryKey: ['drawing', drawingId],
    queryFn: () => api.get(`/drawings/${drawingId}`).then((r) => r.data),
  })

  const { data: drawingUrl } = useQuery({
    queryKey: ['drawing-url', drawingId],
    queryFn: () => api.get(`/drawings/${drawingId}/url`).then((r) => r.data),
  })

  const { data: pages } = useQuery({
    queryKey: ['drawing-pages', drawingId],
    queryFn: () => api.get(`/drawings/${drawingId}/pages`).then((r) => r.data),
    enabled: !!drawing,
  })

  const { data: symbols } = useQuery({
    queryKey: ['symbols', drawingId, selectedPage],
    queryFn: () =>
      api.get(`/drawings/${drawingId}/pages/${selectedPage}/symbols`).then((r) => r.data),
    enabled: !!drawing,
  })

  // Get the current page's real-world dimensions from the pages list
  const currentPage = pages?.items?.find((p: any) => p.page_number === selectedPage)
  const pageWidthFt: number = currentPage?.width_ft ?? 0
  const pageHeightFt: number = currentPage?.height_ft ?? 0

  const pageCount: number = pages?.items?.length ?? 1

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="h-12 bg-white border-b border-gray-200 flex items-center px-4 gap-3 flex-shrink-0">
        <span className="font-medium text-gray-900 text-sm truncate max-w-xs">
          {drawing?.name}
        </span>

        {/* Page selector */}
        {pageCount > 1 && (
          <div className="flex items-center gap-1 border rounded px-2 py-0.5">
            <button
              onClick={() => setSelectedPage((p) => Math.max(1, p - 1))}
              disabled={selectedPage === 1}
              className="text-xs disabled:opacity-40"
            >
              ‹
            </button>
            <span className="text-xs w-16 text-center">
              Page {selectedPage}/{pageCount}
            </span>
            <button
              onClick={() => setSelectedPage((p) => Math.min(pageCount, p + 1))}
              disabled={selectedPage === pageCount}
              className="text-xs disabled:opacity-40"
            >
              ›
            </button>
          </div>
        )}

        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={() => setShowSymbols((v) => !v)}
            className={`flex items-center gap-1 text-xs px-2 py-1 rounded ${showSymbols ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'}`}
          >
            <CheckSquare size={12} /> Symbols {symbols?.symbols?.length ?? 0}
          </button>
          <button
            onClick={() => setShowRuns((v) => !v)}
            className={`flex items-center gap-1 text-xs px-2 py-1 rounded ${showRuns ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}
          >
            <Layers size={12} /> Runs {symbols?.material_runs?.length ?? 0}
          </button>
          <div className="flex items-center gap-1 border rounded px-2">
            <button onClick={() => setZoom((z) => Math.max(0.25, z - 0.25))}>
              <ZoomOut size={14} />
            </button>
            <span className="text-xs w-12 text-center">{Math.round(zoom * 100)}%</span>
            <button onClick={() => setZoom((z) => Math.min(4, z + 0.25))}>
              <ZoomIn size={14} />
            </button>
          </div>
        </div>
      </div>

      {/* Viewer */}
      <div className="flex-1 overflow-auto bg-gray-800 flex items-start justify-center p-4">
        {drawingUrl?.url ? (
          <div
            className="relative"
            style={{
              transform: `scale(${zoom})`,
              transformOrigin: 'top left',
              width: IFRAME_W,
              height: IFRAME_H,
            }}
          >
            {drawing?.file_type === 'pdf' ? (
              <iframe
                src={drawingUrl.url}
                style={{ width: IFRAME_W, height: IFRAME_H, border: 'none' }}
                title="Drawing"
              />
            ) : (
              <img
                src={drawingUrl.url}
                alt="Drawing"
                style={{ width: IFRAME_W, height: IFRAME_H, objectFit: 'contain' }}
              />
            )}

            {/* Symbol overlays — positions mapped from feet to pixels */}
            {showSymbols &&
              symbols?.symbols?.map((sym: any) => {
                const left = feetToPx(sym.x ?? 0, 'x', pageWidthFt, pageHeightFt)
                const top = feetToPx(sym.y ?? 0, 'y', pageWidthFt, pageHeightFt)
                const w = feetToPx(sym.width ?? 2, 'x', pageWidthFt, pageHeightFt)
                const h = feetToPx(sym.height ?? 2, 'y', pageWidthFt, pageHeightFt)
                const color = confidenceColor(sym.confidence ?? 0)
                const isSelected = selectedSymbol?.id === sym.id
                return (
                  <div
                    key={sym.id}
                    onClick={() => setSelectedSymbol(isSelected ? null : sym)}
                    title={`${sym.symbol_type} (${Math.round((sym.confidence ?? 0) * 100)}%)`}
                    style={{
                      position: 'absolute',
                      left,
                      top,
                      width: Math.max(w, 8),
                      height: Math.max(h, 8),
                      border: `2px solid ${color}`,
                      borderRadius: 4,
                      backgroundColor: isSelected ? `${color}33` : 'transparent',
                      cursor: 'pointer',
                      boxShadow: isSelected ? `0 0 0 2px ${color}` : undefined,
                    }}
                  />
                )
              })}
          </div>
        ) : (
          <div className="text-gray-400 text-center mt-20">
            {drawing?.processing_status === 'processing' ? (
              <p>Processing drawing… This may take a minute.</p>
            ) : drawing?.processing_status === 'error' ? (
              <p className="text-red-400 flex items-center gap-2">
                <AlertCircle size={16} /> {drawing.processing_error || 'Processing failed'}
              </p>
            ) : (
              <p>Loading drawing…</p>
            )}
          </div>
        )}
      </div>

      {/* Selected symbol detail */}
      {selectedSymbol && (
        <div className="bg-blue-50 border-t border-blue-200 px-4 py-2 flex items-center gap-4 text-sm flex-shrink-0">
          <span className="font-medium text-blue-800">{selectedSymbol.symbol_type}</span>
          <span className="text-blue-600">
            Position: ({selectedSymbol.x?.toFixed(1)} ft, {selectedSymbol.y?.toFixed(1)} ft)
          </span>
          <span className="text-blue-600">
            Confidence: {Math.round((selectedSymbol.confidence ?? 0) * 100)}%
          </span>
          {selectedSymbol.label && (
            <span className="text-blue-600">Label: {selectedSymbol.label}</span>
          )}
          <button
            onClick={() => setSelectedSymbol(null)}
            className="ml-auto text-blue-400 hover:text-blue-600"
          >
            ✕
          </button>
        </div>
      )}

      {/* Bottom panel — Material runs */}
      {symbols?.material_runs?.length > 0 && showRuns && (
        <div className="h-36 bg-white border-t border-gray-200 overflow-auto flex-shrink-0">
          <table className="w-full text-xs">
            <thead className="bg-gray-50 sticky top-0">
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
                  <td className="px-3 py-1.5 text-right font-mono">
                    {run.length_ft != null ? run.length_ft.toFixed(1) : '—'}
                  </td>
                  <td className="px-3 py-1.5 text-gray-400 font-mono">{run.layer_name}</td>
                  <td className="px-3 py-1.5 text-center">
                    <span
                      className={
                        run.confidence > 0.85
                          ? 'text-green-600'
                          : run.confidence > 0.65
                            ? 'text-yellow-600'
                            : 'text-red-600'
                      }
                    >
                      {Math.round((run.confidence ?? 0) * 100)}%
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
