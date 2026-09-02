import { useState } from 'react'
import { queryAI, searchEntities, getReport } from '../api/client'
import { MessageSquare, Search, FileText, Send, Loader2, Bot, User } from 'lucide-react'
import toast from 'react-hot-toast'
import clsx from 'clsx'

const EXAMPLE_QUESTIONS = [
  'Who are the top 3 most influential suspects in the network?',
  'Which entities are critical brokers that connect different criminal groups?',
  'Summarize all known activities of the most dangerous person.',
  'Which phone numbers show the most suspicious calling patterns?',
  'What locations appear most frequently in the network?',
]

function Message({ role, content, meta }) {
  return (
    <div className={clsx('flex gap-3', role === 'user' ? 'flex-row-reverse' : 'flex-row')}>
      <div className={clsx(
        'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm',
        role === 'user' ? 'bg-accent' : 'bg-blue-600'
      )}>
        {role === 'user' ? <User size={14} /> : <Bot size={14} />}
      </div>
      <div className={clsx(
        'max-w-[80%] rounded-xl px-4 py-3 text-sm',
        role === 'user' ? 'bg-accent/20 text-white' : 'bg-card border border-border text-slate-200'
      )}>
        <p className="whitespace-pre-wrap leading-relaxed">{content}</p>
        {meta && (
          <div className="mt-2 pt-2 border-t border-border text-xs text-slate-400">
            {meta.documents_used > 0 && <span>📄 {meta.documents_used} docs used · </span>}
            <span>🤖 {meta.model}</span>
          </div>
        )}
      </div>
    </div>
  )
}

export default function InvestigatorSearch() {
  const [messages, setMessages] = useState([{
    role: 'assistant',
    content: 'Hello, Investigator. I\'m your AI intelligence assistant. Ask me anything about the criminal network — suspects, relationships, patterns, or anomalies.',
  }])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [searchQ, setSearchQ] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [selectedEntity, setSelectedEntity] = useState(null)
  const [report, setReport] = useState(null)
  const [reportLoading, setReportLoading] = useState(false)

  const handleSend = async () => {
    if (!input.trim() || loading) return
    const question = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: question }])
    setLoading(true)
    try {
      const { data } = await queryAI(question)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.answer,
        meta: { documents_used: data.documents_used, model: data.model },
      }])
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '❌ Unable to connect to AI engine. Make sure Ollama is running with a model loaded.',
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!searchQ.trim()) return
    try {
      const { data } = await searchEntities(searchQ)
      setSearchResults(data.results || [])
    } catch { toast.error('Search failed') }
  }

  const handleGetReport = async (id) => {
    setReportLoading(true)
    setReport(null)
    try {
      const { data } = await getReport(id, false)  // false = no LLM for speed
      setReport(data)
    } catch { toast.error('Report generation failed') }
    finally { setReportLoading(false) }
  }

  return (
    <div className="flex h-screen gap-0">
      {/* Left: Chat */}
      <div className="flex-1 flex flex-col p-4">
        <h1 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
          <MessageSquare className="text-accent" size={22} />
          AI Investigator Assistant
        </h1>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto space-y-4 pr-2 mb-4">
          {messages.map((m, i) => <Message key={i} {...m} />)}
          {loading && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
                <Bot size={14} />
              </div>
              <div className="bg-card border border-border rounded-xl px-4 py-3 flex items-center gap-2 text-slate-400 text-sm">
                <Loader2 size={14} className="animate-spin" /> Analyzing intelligence data…
              </div>
            </div>
          )}
        </div>

        {/* Example prompts */}
        <div className="flex gap-2 flex-wrap mb-3">
          {EXAMPLE_QUESTIONS.slice(0, 3).map((q, i) => (
            <button
              key={i}
              onClick={() => setInput(q)}
              className="text-xs bg-slate-700/50 border border-border text-slate-300 px-2 py-1 rounded-lg hover:border-accent hover:text-white transition-colors"
            >
              {q.slice(0, 45)}…
            </button>
          ))}
        </div>

        {/* Input */}
        <div className="flex gap-2">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
            placeholder="Ask about suspects, relationships, patterns…"
            className="flex-1 bg-card border border-border rounded-xl px-4 py-3 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-accent"
          />
          <button
            onClick={handleSend}
            disabled={loading}
            className="bg-accent text-white px-4 py-3 rounded-xl hover:bg-red-700 disabled:opacity-50 transition-colors"
          >
            <Send size={16} />
          </button>
        </div>
      </div>

      {/* Right: Entity Search + Report */}
      <div className="w-80 border-l border-border flex flex-col p-4 gap-4">
        <div>
          <h2 className="text-white font-semibold mb-3 flex items-center gap-2">
            <Search size={16} className="text-accent" /> Entity Search
          </h2>
          <form onSubmit={handleSearch} className="flex gap-2 mb-3">
            <input
              value={searchQ}
              onChange={e => setSearchQ(e.target.value)}
              placeholder="Search name, phone…"
              className="flex-1 bg-surface border border-border rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-accent"
            />
            <button type="submit" className="bg-card border border-border px-3 rounded-lg text-slate-400 hover:text-white">
              <Search size={14} />
            </button>
          </form>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {searchResults.map((r, i) => {
              const n = r.n || {}
              return (
                <button
                  key={i}
                  onClick={() => { setSelectedEntity(n); handleGetReport(n.id) }}
                  className="w-full text-left px-3 py-2 rounded-lg bg-slate-800/50 hover:bg-slate-700 border border-transparent hover:border-border transition-colors"
                >
                  <div className="text-sm text-white truncate">{n.name || '—'}</div>
                  <div className="text-xs text-slate-400">{(r.labels || []).join(', ')}</div>
                </button>
              )
            })}
          </div>
        </div>

        {/* Report Panel */}
        <div className="flex-1 overflow-y-auto">
          {reportLoading && (
            <div className="text-slate-400 text-sm flex items-center gap-2">
              <Loader2 size={14} className="animate-spin" /> Generating report…
            </div>
          )}
          {report && (
            <div className="space-y-3">
              <h3 className="font-semibold text-white flex items-center gap-2">
                <FileText size={16} className="text-accent" /> Intelligence Report
              </h3>
              <div className="space-y-2 text-sm">
                <div>
                  <span className="text-slate-400">Subject: </span>
                  <span className="text-white font-medium">{report.entity_name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-slate-400">Risk:</span>
                  <span className={clsx('text-xs px-2 py-0.5 rounded-full font-semibold',
                    report.risk_level === 'CRITICAL' ? 'badge-critical' :
                    report.risk_level === 'HIGH'     ? 'badge-high' :
                    report.risk_level === 'MEDIUM'   ? 'badge-medium' : 'badge-low'
                  )}>
                    {report.risk_level} ({report.risk_score?.toFixed(1)}/100)
                  </span>
                </div>
                <div>
                  <div className="text-slate-400 text-xs mb-1">Summary</div>
                  <p className="text-slate-300 text-xs leading-relaxed">{report.summary}</p>
                </div>
                <div>
                  <div className="text-slate-400 text-xs mb-1">Associates ({report.associate_count})</div>
                  <div className="space-y-1">
                    {(report.known_associates || []).slice(0, 6).map((a, i) => (
                      <div key={i} className="text-xs text-slate-300 bg-slate-800/50 rounded px-2 py-1 truncate">
                        {a.name} <span className="text-slate-500">({a.type})</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <div className="text-slate-400 text-xs mb-1">Recommendations</div>
                  {(report.recommendations || []).map((r, i) => (
                    <p key={i} className="text-xs text-slate-300 mb-1">{r}</p>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
