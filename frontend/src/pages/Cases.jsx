import { useState, useEffect, useCallback } from 'react'
import {
  getCases, getCase, createCase, updateCase, deleteCase,
  addCaseEntity, removeCaseEntity, searchEntities,
} from '../api/client'
import {
  Briefcase, Plus, Trash2, Search, X, Loader2, Tag, User,
  Link2
} from 'lucide-react'
import toast from 'react-hot-toast'
import clsx from 'clsx'

const PRIORITY_COLORS = {
  LOW: 'bg-green-500/10 text-green-400 border-green-500/30',
  MEDIUM: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
  HIGH: 'bg-orange-500/10 text-orange-400 border-orange-500/30',
  CRITICAL: 'bg-red-500/10 text-red-400 border-red-500/30',
}

const STATUS_COLORS = {
  OPEN: 'badge-low',
  ACTIVE: 'badge-medium',
  CLOSED: 'badge-high',
  ARCHIVED: 'badge-critical',
}

function CreateCaseModal({ onClose, onCreated }) {
  const [form, setForm] = useState({ name: '', description: '', priority: 'MEDIUM', assigned_to: '' })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.name.trim()) return
    setLoading(true)
    try {
      await createCase(form)
      toast.success('Case created')
      onCreated()
    } catch { toast.error('Failed to create case') }
    finally { setLoading(false) }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={onClose}>
      <div className="card w-full max-w-md space-y-4" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h2 className="text-white font-semibold">New Case</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white"><X size={18} /></button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-3">
          <input
            value={form.name}
            onChange={e => setForm({ ...form, name: e.target.value })}
            placeholder="Case name"
            className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-accent"
            autoFocus
          />
          <textarea
            value={form.description}
            onChange={e => setForm({ ...form, description: e.target.value })}
            placeholder="Description (optional)"
            rows={3}
            className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-accent resize-none"
          />
          <div className="flex gap-3">
            <select
              value={form.priority}
              onChange={e => setForm({ ...form, priority: e.target.value })}
              className="flex-1 bg-surface border border-border rounded-lg px-3 py-2 text-sm text-white"
            >
              {['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].map(p => <option key={p} value={p}>{p}</option>)}
            </select>
            <input
              value={form.assigned_to}
              onChange={e => setForm({ ...form, assigned_to: e.target.value })}
              placeholder="Assigned to"
              className="flex-1 bg-surface border border-border rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-accent"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !form.name.trim()}
            className="w-full bg-accent hover:bg-red-700 disabled:opacity-50 text-white font-medium py-2 rounded-lg text-sm transition-colors"
          >
            {loading ? 'Creating…' : 'Create Case'}
          </button>
        </form>
      </div>
    </div>
  )
}

function CaseDetail({ caseData, onRefresh }) {
  const [entityQ, setEntityQ] = useState('')
  const [entityResults, setEntityResults] = useState([])

  const handleSearch = async () => {
    if (entityQ.length < 2) return
    try {
      const { data } = await searchEntities(entityQ)
      setEntityResults(data.results || [])
    } catch { /* ignore */ }
  }

  const addEntity = async (entity) => {
    try {
      await addCaseEntity(caseData.id, { entity_id: entity.n.id })
      toast.success(`Added ${entity.n.name}`)
      setEntityResults([])
      setEntityQ('')
      onRefresh()
    } catch { toast.error('Failed to add entity') }
  }

  const removeEntity = async (entityId) => {
    try {
      await removeCaseEntity(caseData.id, entityId)
      toast.success('Entity removed')
      onRefresh()
    } catch { toast.error('Failed to remove entity') }
  }

  const saveStatus = async (status) => {
    try {
      await updateCase(caseData.id, { status })
      toast.success('Status updated')
      onRefresh()
    } catch { toast.error('Update failed') }
  }

  return (
    <div className="max-w-3xl space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs text-slate-500 uppercase tracking-wide mb-1">Case</div>
          <h1 className="text-2xl font-bold text-white">{caseData.name}</h1>
          <p className="text-slate-400 text-sm mt-1">{caseData.description || 'No description'}</p>
        </div>
        <div className="flex gap-2">
          <span className={clsx('text-xs px-3 py-1 rounded-full border font-bold', PRIORITY_COLORS[caseData.priority] || PRIORITY_COLORS.MEDIUM)}>
            {caseData.priority}
          </span>
          <span className={clsx('text-xs px-3 py-1 rounded-full font-bold', STATUS_COLORS[caseData.status])}>
            {caseData.status}
          </span>
        </div>
      </div>

      {/* Status Actions */}
      <div className="card">
        <h2 className="font-semibold text-white mb-3">Actions</h2>
        <div className="flex flex-wrap gap-2">
          {['OPEN', 'ACTIVE', 'CLOSED', 'ARCHIVED'].map(s => (
            <button
              key={s}
              onClick={() => saveStatus(s)}
              disabled={caseData.status === s}
              className={clsx(
                'px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors',
                caseData.status === s
                  ? 'bg-accent/20 border-accent/30 text-accent'
                  : 'bg-slate-800/50 border-border text-slate-400 hover:text-white hover:border-accent'
              )}
            >
              {s}
            </button>
          ))}
        </div>
        {caseData.assigned_to && (
          <div className="flex items-center gap-2 text-sm text-slate-400 mt-3">
            <User size={14} /> Assigned to: <span className="text-white">{caseData.assigned_to}</span>
          </div>
        )}
        {caseData.tags?.length > 0 && (
          <div className="flex items-center gap-2 text-sm text-slate-400 mt-2">
            <Tag size={14} /> Tags: {caseData.tags.map(t => (
              <span key={t} className="bg-slate-700 text-slate-300 px-2 py-0.5 rounded text-xs">{t}</span>
            ))}
          </div>
        )}
      </div>

      {/* Linked Entities */}
      <div className="card">
        <h2 className="font-semibold text-white mb-3 flex items-center gap-2">
          <Link2 size={16} className="text-accent" />
          Linked Entities ({caseData.entity_ids?.length || 0})
        </h2>

        {/* Search + Add */}
        <div className="flex gap-2 mb-3">
          <input
            value={entityQ}
            onChange={e => setEntityQ(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
            placeholder="Search entity to link…"
            className="flex-1 bg-surface border border-border rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-accent"
          />
          <button onClick={handleSearch} className="bg-card border border-border px-3 rounded-lg text-slate-400 hover:text-white">
            <Search size={14} />
          </button>
        </div>

        {entityResults.length > 0 && (
          <div className="border border-border rounded-lg mb-3 max-h-48 overflow-y-auto">
            {entityResults.map((r, i) => {
              const n = r.n || {}
              return (
                <button
                  key={i}
                  onClick={() => addEntity(r)}
                  className="w-full text-left px-3 py-2 hover:bg-slate-700/50 border-b border-border last:border-0 flex items-center justify-between text-sm"
                >
                  <div>
                    <span className="text-white">{n.name}</span>
                    <span className="text-slate-500 ml-2">{(r.labels || []).join(', ')}</span>
                  </div>
                  <Plus size={14} className="text-accent" />
                </button>
              )
            })}
          </div>
        )}

        {(!caseData.entity_ids || caseData.entity_ids.length === 0) ? (
          <p className="text-sm text-slate-500">No entities linked. Use the search above to add entities.</p>
        ) : (
          <div className="space-y-1">
            {caseData.entity_ids.map(eid => (
              <div key={eid} className="flex items-center justify-between bg-slate-800/50 rounded-lg px-3 py-2">
                <span className="text-sm text-slate-300 font-mono truncate">{eid}</span>
                <button onClick={() => removeEntity(eid)} className="text-slate-500 hover:text-red-400 ml-2 flex-shrink-0">
                  <X size={14} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="text-xs text-slate-500">
        Created: {caseData.created_at || 'N/A'} · Updated: {caseData.updated_at || 'N/A'}
      </div>
    </div>
  )
}

export default function Cases() {
  const [cases, setCases] = useState([])
  const [selected, setSelected] = useState(null)
  const [showCreate, setShowCreate] = useState(false)
  const [loading, setLoading] = useState(true)

  const fetchCases = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await getCases()
      setCases(data.cases || [])
    } catch { toast.error('Failed to load cases') }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { fetchCases() }, [fetchCases])

  const loadCase = async (id) => {
    try {
      const { data } = await getCase(id)
      setSelected(data)
    } catch { toast.error('Failed to load case') }
  }

  const handleDelete = async (id, e) => {
    e.stopPropagation()
    if (!confirm('Delete this case?')) return
    try {
      await deleteCase(id)
      toast.success('Case deleted')
      if (selected?.id === id) setSelected(null)
      fetchCases()
    } catch { toast.error('Delete failed') }
  }

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <div className="w-72 border-r border-border p-4 flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h2 className="text-white font-semibold flex items-center gap-2">
            <Briefcase className="text-accent" size={18} />
            Cases
          </h2>
          <button
            onClick={() => setShowCreate(true)}
            className="bg-accent/10 border border-accent/30 text-accent hover:bg-accent/20 rounded-lg p-1.5 transition-colors"
          >
            <Plus size={16} />
          </button>
        </div>

        <div className="space-y-1 overflow-y-auto flex-1">
          {loading ? (
            <div className="flex justify-center py-8 text-slate-500">
              <Loader2 size={20} className="animate-spin" />
            </div>
          ) : cases.length === 0 ? (
            <p className="text-sm text-slate-500 py-4 text-center">No cases yet. Create one to get started.</p>
          ) : cases.map(c => (
            <button
              key={c.id}
              onClick={() => loadCase(c.id)}
              className={clsx(
                'w-full text-left px-3 py-2.5 rounded-lg border transition-colors flex items-center justify-between group',
                selected?.id === c.id
                  ? 'bg-accent/10 border-accent/30 text-white'
                  : 'bg-slate-800/50 border-transparent text-slate-300 hover:border-border hover:bg-slate-700/50'
              )}
            >
              <div className="min-w-0">
                <div className="text-sm font-medium truncate">{c.name}</div>
                <div className="text-xs text-slate-500 flex items-center gap-1">
                  <span className={clsx('inline-block w-1.5 h-1.5 rounded-full',
                    c.status === 'OPEN' ? 'bg-green-400' :
                    c.status === 'ACTIVE' ? 'bg-yellow-400' :
                    c.status === 'CLOSED' ? 'bg-slate-400' : 'bg-red-400'
                  )} />
                  {c.status} · {c.priority}
                  {c.entity_ids?.length > 0 && ` · ${c.entity_ids.length} entities`}
                </div>
              </div>
              <button
                onClick={(e) => handleDelete(c.id, e)}
                className="text-slate-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 ml-2"
              >
                <Trash2 size={14} />
              </button>
            </button>
          ))}
        </div>
      </div>

      {/* Detail */}
      <div className="flex-1 p-6 overflow-y-auto">
        {!selected ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-500">
            <Briefcase size={48} className="mb-3 opacity-30" />
            <p>Select a case or create a new one.</p>
          </div>
        ) : (
          <CaseDetail caseData={selected} onRefresh={() => { fetchCases(); loadCase(selected.id) }} />
        )}
      </div>

      {showCreate && <CreateCaseModal onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); fetchCases() }} />}
    </div>
  )
}
