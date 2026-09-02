import { useState } from 'react'
import { searchEntities, getTimeline } from '../api/client'
import { Clock, Search, MapPin, Phone, DollarSign, Users, AlertTriangle, Scale } from 'lucide-react'
import toast from 'react-hot-toast'

const EVENT_ICONS = {
  '📞 Phone Call':         Phone,
  '🤝 Meeting':            Users,
  '📍 Location Visit':     MapPin,
  '💰 Financial Transfer': DollarSign,
  '⚖️ Legal Action':       Scale,
  '🔗 Association':        Users,
}

const EVENT_COLORS = {
  '📞 Phone Call':         'bg-green-900/40 border-green-700',
  '📍 Location Visit':     'bg-blue-900/40 border-blue-700',
  '💰 Financial Transfer': 'bg-yellow-900/40 border-yellow-700',
  '⚖️ Legal Action':       'bg-red-900/40 border-red-700',
  '🤝 Meeting':            'bg-purple-900/40 border-purple-700',
  '🔗 Association':        'bg-slate-700/40 border-slate-600',
}

export default function Timeline() {
  const [searchQ, setSearchQ] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [selectedEntity, setSelectedEntity] = useState(null)
  const [timeline, setTimeline] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!searchQ.trim()) return
    try {
      const { data } = await searchEntities(searchQ)
      setSearchResults(data.results || [])
    } catch { toast.error('Search failed') }
  }

  const loadTimeline = async (entity) => {
    setSelectedEntity(entity)
    setLoading(true)
    try {
      const { data } = await getTimeline(entity.id)
      setTimeline(data)
    } catch { toast.error('Could not load timeline') }
    finally { setLoading(false) }
  }

  return (
    <div className="flex h-screen">
      {/* Sidebar: Entity Picker */}
      <div className="w-72 border-r border-border p-4 flex flex-col gap-4">
        <h2 className="text-white font-semibold flex items-center gap-2">
          <Clock className="text-accent" size={18} />
          Timeline
        </h2>
        <form onSubmit={handleSearch} className="flex gap-2">
          <input
            value={searchQ}
            onChange={e => setSearchQ(e.target.value)}
            placeholder="Search suspect…"
            className="flex-1 bg-surface border border-border rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-accent"
          />
          <button type="submit" className="bg-card border border-border px-3 rounded-lg text-slate-400 hover:text-white">
            <Search size={14} />
          </button>
        </form>
        <div className="space-y-1 overflow-y-auto">
          {searchResults.map((r, i) => {
            const n = r.n || {}
            return (
              <button
                key={i}
                onClick={() => loadTimeline(n)}
                className={`w-full text-left px-3 py-2 rounded-lg border transition-colors ${
                  selectedEntity?.id === n.id
                    ? 'bg-accent/20 border-accent/40 text-white'
                    : 'bg-slate-800/50 border-transparent text-slate-300 hover:bg-slate-700'
                }`}
              >
                <div className="text-sm truncate font-medium">{n.name || '—'}</div>
                <div className="text-xs text-slate-400">{(r.labels || []).join(', ')}</div>
              </button>
            )
          })}
        </div>
      </div>

      {/* Main: Timeline */}
      <div className="flex-1 p-6 overflow-y-auto">
        {!selectedEntity && (
          <div className="flex flex-col items-center justify-center h-full text-slate-500">
            <Clock size={48} className="mb-3 opacity-30" />
            <p>Search for an entity to view its event timeline.</p>
          </div>
        )}

        {selectedEntity && (
          <>
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-white">{selectedEntity.name}</h2>
              <p className="text-slate-400 text-sm">
                {timeline ? `${timeline.total_events} events in timeline` : 'Loading…'}
              </p>
            </div>

            {loading && (
              <div className="text-slate-400 animate-pulse text-center py-12">
                Building timeline…
              </div>
            )}

            {timeline && timeline.events.length === 0 && (
              <div className="text-slate-500 text-center py-12">
                No timestamped events found for this entity.
              </div>
            )}

            {/* Timeline Items */}
            <div className="relative">
              {/* Vertical line */}
              <div className="absolute left-6 top-0 bottom-0 w-px bg-border" />

              <div className="space-y-4">
                {(timeline?.events || []).map((ev, i) => {
                  const colorClass = EVENT_COLORS[ev.event_type] || 'bg-slate-700/40 border-slate-600'
                  return (
                    <div key={i} className="flex gap-4 pl-14 relative">
                      {/* Dot */}
                      <div className="absolute left-4 top-3 w-5 h-5 rounded-full bg-slate-700 border-2 border-accent flex items-center justify-center text-xs">
                        {ev.event_type?.charAt(0) || '•'}
                      </div>

                      <div className={`flex-1 border rounded-lg p-3 ${colorClass}`}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium text-white">{ev.event_type}</span>
                          <span className="text-xs text-slate-400">{ev.timestamp || 'No date'}</span>
                        </div>
                        <p className="text-sm text-slate-300">
                          {ev.relation} with{' '}
                          <span className="text-white font-medium">{ev.other_entity || 'Unknown'}</span>
                          {ev.location && <span className="text-slate-400"> at {ev.location}</span>}
                          {ev.value && <span className="text-slate-400"> (₹{ev.value.toLocaleString?.() ?? ev.value})</span>}
                        </p>
                        {ev.source_doc && (
                          <p className="text-xs text-slate-500 mt-1">Source: {ev.source_doc}</p>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
