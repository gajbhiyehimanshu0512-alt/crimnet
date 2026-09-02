import { useState } from 'react'
import { searchEntities, getReport, getReportPdf } from '../api/client'
import { FileText, Search, Download, AlertTriangle, Users, Clock, Shield, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import clsx from 'clsx'

function RiskMeter({ score }) {
  const pct = Math.min(100, score || 0)
  const color = pct >= 75 ? 'bg-red-500' : pct >= 50 ? 'bg-orange-500' : pct >= 25 ? 'bg-yellow-500' : 'bg-green-500'
  return (
    <div>
      <div className="flex justify-between text-xs text-slate-400 mb-1">
        <span>Risk Score</span>
        <span className="text-white font-semibold">{pct.toFixed(1)} / 100</span>
      </div>
      <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

export default function Reports() {
  const [searchQ, setSearchQ] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleSearch = async (e) => {
    e.preventDefault()
    try {
      const { data } = await searchEntities(searchQ)
      setSearchResults(data.results || [])
    } catch { toast.error('Search failed') }
  }

  const loadReport = async (entity) => {
    setLoading(true)
    setReport(null)
    try {
      const { data } = await getReport(entity.id, true)
      setReport(data)
      toast.success(`Report generated for ${entity.name}`)
    } catch { toast.error('Report generation failed') }
    finally { setLoading(false) }
  }

  const downloadPdfReport = async () => {
    if (!report) return
    try {
      const response = await getReportPdf(report.entity_id)
      const url = URL.createObjectURL(response.data)
      const a = document.createElement('a')
      a.href = url
      a.download = `intel-report-${report.entity_name.replace(/\s/g, '_')}.pdf`
      a.click()
      URL.revokeObjectURL(url)
      toast.success('PDF report downloaded')
    } catch {
      toast.error('PDF download failed')
    }
  }

  const downloadReport = () => {
    if (!report) return
    const content = `
INTELLIGENCE REPORT — RESTRICTED
Generated: ${new Date().toLocaleString()}
For Law Enforcement Use Only

SUBJECT: ${report.entity_name}
TYPE:     ${report.entity_type}
RISK LEVEL: ${report.risk_level} (Score: ${report.risk_score?.toFixed(1)}/100)

EXECUTIVE SUMMARY
${report.summary}

KNOWN ASSOCIATES (${report.associate_count})
${report.known_associates?.slice(0, 10).map(a => `• ${a.name} (${a.type})`).join('\n') || 'None identified'}

CENTRALITY SCORES
• PageRank:     ${(report.centrality_scores?.pagerank || 0).toFixed(6)}
• Betweenness:  ${((report.centrality_scores?.betweenness || 0) * 100).toFixed(2)}%
• Degree:       ${((report.centrality_scores?.degree || 0) * 100).toFixed(2)}%

RECOMMENDATIONS
${report.recommendations?.join('\n') || 'None'}

SOURCE DOCUMENTS
${report.source_documents?.join('\n') || 'None specified'}
    `.trim()

    const blob = new Blob([content], { type: 'text/plain' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href = url
    a.download = `intel-report-${report.entity_name.replace(/\s/g, '_')}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <div className="w-72 border-r border-border p-4 flex flex-col gap-4">
        <h2 className="text-white font-semibold flex items-center gap-2">
          <FileText className="text-accent" size={18} />
          Intelligence Reports
        </h2>
        <form onSubmit={handleSearch} className="flex gap-2">
          <input
            value={searchQ}
            onChange={e => setSearchQ(e.target.value)}
            placeholder="Search entity…"
            className="flex-1 bg-surface border border-border rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-accent"
          />
          <button type="submit" className="bg-card border border-border px-3 rounded-lg text-slate-400 hover:text-white">
            <Search size={14} />
          </button>
        </form>
        <div className="space-y-1 overflow-y-auto flex-1">
          {searchResults.map((r, i) => {
            const n = r.n || {}
            return (
              <button
                key={i}
                onClick={() => loadReport(n)}
                className="w-full text-left px-3 py-2 rounded-lg bg-slate-800/50 border border-transparent hover:border-border text-slate-300 hover:text-white hover:bg-slate-700 transition-colors"
              >
                <div className="text-sm font-medium truncate">{n.name}</div>
                <div className="text-xs text-slate-500">{(r.labels || []).join(', ')}</div>
              </button>
            )
          })}
        </div>
      </div>

      {/* Report View */}
      <div className="flex-1 p-6 overflow-y-auto">
        {loading && (
          <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-3">
            <Loader2 size={40} className="animate-spin" />
            <p>Generating intelligence report…</p>
          </div>
        )}

        {!loading && !report && (
          <div className="flex flex-col items-center justify-center h-full text-slate-500">
            <FileText size={48} className="mb-3 opacity-30" />
            <p>Search for an entity and select it to generate a report.</p>
          </div>
        )}

        {!loading && report && (
          <div className="max-w-3xl space-y-6">
            {/* Header */}
            <div className="flex items-start justify-between">
              <div>
                <div className="text-xs text-slate-500 uppercase tracking-wide mb-1">Intelligence Report · Restricted</div>
                <h1 className="text-3xl font-bold text-white">{report.entity_name}</h1>
                <p className="text-slate-400">{report.entity_type} · {report.community_membership}</p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={downloadReport}
                  className="flex items-center gap-2 px-4 py-2 bg-card border border-border rounded-lg text-slate-300 hover:text-white hover:border-accent transition-colors text-sm"
                >
                  <Download size={14} />
                  TXT
                </button>
                <button
                  onClick={downloadPdfReport}
                  className="flex items-center gap-2 px-4 py-2 bg-accent/10 border border-accent/30 rounded-lg text-accent hover:bg-accent/20 transition-colors text-sm font-medium"
                >
                  <Download size={14} />
                  PDF
                </button>
              </div>
            </div>

            {/* Risk */}
            <div className="card">
              <div className="flex items-center gap-2 mb-4">
                <Shield size={18} className="text-accent" />
                <h2 className="font-semibold text-white">Risk Assessment</h2>
                <span className={clsx('ml-auto text-xs px-3 py-1 rounded-full font-bold',
                  report.risk_level === 'CRITICAL' ? 'badge-critical' :
                  report.risk_level === 'HIGH'     ? 'badge-high' :
                  report.risk_level === 'MEDIUM'   ? 'badge-medium' : 'badge-low'
                )}>
                  {report.risk_level}
                </span>
              </div>
              <RiskMeter score={report.risk_score} />
              <div className="grid grid-cols-3 gap-3 mt-4 text-xs text-center">
                {Object.entries(report.risk_breakdown || {}).slice(0, 3).map(([k, v]) => (
                  <div key={k} className="bg-slate-800/50 rounded-lg p-2">
                    <div className="text-white font-semibold">{v.toFixed(1)}</div>
                    <div className="text-slate-400">{k.replace('_contribution', '').replace(/_/g, ' ')}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Summary */}
            <div className="card">
              <h2 className="font-semibold text-white mb-3">Executive Summary</h2>
              <p className="text-slate-300 leading-relaxed">{report.summary}</p>
            </div>

            {/* Centrality */}
            <div className="card">
              <h2 className="font-semibold text-white mb-3">Network Position</h2>
              <div className="grid grid-cols-3 gap-4 text-center">
                <div>
                  <div className="text-2xl font-bold text-blue-400">
                    {((report.centrality_scores?.pagerank || 0) * 1000).toFixed(2)}
                  </div>
                  <div className="text-xs text-slate-400">PageRank ×1000</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-purple-400">
                    {((report.centrality_scores?.betweenness || 0) * 100).toFixed(1)}%
                  </div>
                  <div className="text-xs text-slate-400">Betweenness</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-green-400">
                    {((report.centrality_scores?.degree || 0) * 100).toFixed(1)}%
                  </div>
                  <div className="text-xs text-slate-400">Degree</div>
                </div>
              </div>
            </div>

            {/* Associates */}
            <div className="card">
              <h2 className="font-semibold text-white mb-3 flex items-center gap-2">
                <Users size={16} className="text-accent" />
                Known Associates ({report.associate_count})
              </h2>
              <div className="grid grid-cols-2 gap-2">
                {(report.known_associates || []).slice(0, 12).map((a, i) => (
                  <div key={i} className="flex items-center gap-2 bg-slate-800/50 rounded-lg px-3 py-2">
                    <div className="w-2 h-2 rounded-full bg-accent flex-shrink-0" />
                    <div className="min-w-0">
                      <div className="text-sm text-white truncate">{a.name}</div>
                      <div className="text-xs text-slate-400">{a.type}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Recommendations */}
            <div className="card">
              <h2 className="font-semibold text-white mb-3 flex items-center gap-2">
                <AlertTriangle size={16} className="text-accent" />
                Investigative Recommendations
              </h2>
              <ul className="space-y-2">
                {(report.recommendations || []).map((r, i) => (
                  <li key={i} className="text-sm text-slate-300">{r}</li>
                ))}
              </ul>
            </div>

            {/* Footer */}
            <div className="text-xs text-slate-500 pb-6">
              Report generated: {new Date(report.generated_at).toLocaleString()} ·
              Sources: {(report.source_documents || []).join(', ') || 'None specified'}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
