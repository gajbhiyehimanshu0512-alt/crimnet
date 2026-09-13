import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 60000,
})

// ── Auth Interceptor ─────────────────────────────────────────────────────────

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('crimnet_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('crimnet_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

// ── Graph ─────────────────────────────────────────────────────────────────────

export const getGraphStats   = ()           => api.get('/api/graph/stats')
export const getNetwork      = (limit=300)  => api.get(`/api/graph/network?limit=${limit}`)
export const getEntity       = (id, depth=1)=> api.get(`/api/graph/entity/${id}?depth=${depth}`)
export const searchEntities  = (q)          => api.get(`/api/graph/search?q=${encodeURIComponent(q)}`)
export const getShortestPath = (from, to)   => api.get(`/api/graph/path?from_id=${from}&to_id=${to}`)
export const getCommunities  = ()           => api.get('/api/graph/communities')

// ── Analytics ─────────────────────────────────────────────────────────────────

export const runAnalytics    = ()     => api.post('/api/analytics/run')
export const getInfluencers  = (n=20) => api.get(`/api/analytics/influencers?top_n=${n}`)
export const getAnomalies    = ()     => api.get('/api/analytics/anomalies')
export const getTimeline     = (id)   => api.get(`/api/analytics/timeline/${id}`)
export const getRiskScore    = (id)   => api.get(`/api/analytics/risk/${id}`)

// ── AI ────────────────────────────────────────────────────────────────────────

export const queryAI      = (question)     => api.post('/api/ai/query', { question })
export const getReport    = (id, useLlm=true) => api.get(`/api/ai/report/${id}?use_llm=${useLlm}`)
export const getReportPdf = (id)           => api.get(`/api/ai/report/${id}/pdf`, { responseType: 'blob' })

// ── Ingestion ─────────────────────────────────────────────────────────────────

export const ingestFIR          = (file)        => { const f = new FormData(); f.append('file', file); return api.post('/api/ingest/fir', f) }
export const ingestCDR          = (file)        => { const f = new FormData(); f.append('file', file); return api.post('/api/ingest/cdr', f) }
export const ingestFinancial    = (file)        => { const f = new FormData(); f.append('file', file); return api.post('/api/ingest/financial', f) }
export const ingestSurveillance = (text)        => { const f = new FormData(); f.append('text', text); return api.post('/api/ingest/surveillance', f) }
export const ingestText         = (text, src)   => { const f = new FormData(); f.append('text', text); f.append('source_name', src || 'manual'); return api.post('/api/ingest/text', f) }

// ── Cases ─────────────────────────────────────────────────────────────────────

export const getCases           = ()            => api.get('/api/cases')
export const getCase            = (id)          => api.get(`/api/cases/${id}`)
export const createCase         = (data)        => api.post('/api/cases', data)
export const updateCase         = (id, data)    => api.put(`/api/cases/${id}`, data)
export const deleteCase         = (id)          => api.delete(`/api/cases/${id}`)
export const addCaseEntity      = (caseId, data)=> api.post(`/api/cases/${caseId}/entities`, data)
export const removeCaseEntity   = (caseId, eid) => api.delete(`/api/cases/${caseId}/entities/${eid}`)

