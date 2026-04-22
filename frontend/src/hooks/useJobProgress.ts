import { useEffect, useRef, useState } from 'react'
import { useAuthStore } from '@/stores/auth'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export interface JobProgress {
  stage: string
  pct?: number
  message?: string
  error?: string
}

/**
 * Subscribe to SSE job progress for a job key like "drawing:42" or "spec:7".
 * Returns the latest progress update; clears when job_key changes.
 * Automatically appends the auth token as a query param since EventSource
 * can't set headers.
 */
export function useJobProgress(jobKey: string | null): JobProgress | null {
  const [progress, setProgress] = useState<JobProgress | null>(null)
  const esRef = useRef<EventSource | null>(null)

  useEffect(() => {
    if (!jobKey) {
      setProgress(null)
      return
    }

    const token = useAuthStore.getState().token
    const url = `${BASE_URL}/api/v1/jobs/${encodeURIComponent(jobKey)}/progress${token ? `?token=${token}` : ''}`

    const es = new EventSource(url)
    esRef.current = es

    es.onmessage = (e) => {
      try {
        const data: JobProgress = JSON.parse(e.data)
        setProgress(data)
        if (data.stage === 'done' || data.stage === 'error') {
          es.close()
        }
      } catch {
        // ignore malformed messages (e.g. keepalive comments)
      }
    }

    es.onerror = () => {
      // SSE connection lost — backend may have finished; stop retrying
      es.close()
    }

    return () => {
      es.close()
      esRef.current = null
    }
  }, [jobKey])

  return progress
}
