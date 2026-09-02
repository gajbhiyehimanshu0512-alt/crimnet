import { useState, useEffect, useRef, useCallback } from 'react'
import CytoscapeComponent from 'react-cytoscapejs'
import { getNetwork, getEntity, searchEntities, getCommunities } from '../api/client'
import { Search, ZoomIn, ZoomOut, Maximize2, Filter } from 'lucide-react'
import toast from 'react-hot-toast'
import clsx from 'clsx'

// Node colors by entity type
const TYPE_COLORS = {
  Person:       '#ef4444',
  Organization: '#a855f7',
  Location:     '#3b82f6',
  PhoneNumber:  '#22c55e',
  Vehicle:      '#f97316',
  BankAccount:  '#eab308',
  Event:        '#06b6d4',
  Unknown:      '#64748b',
}

// Risk-level border colors
const RISK_BORDER = {
  CRITICAL: '#ff0000',
  HIGH:     '#f97316',
  MEDIUM:   '#eab308',
  LOW:      '#22c55e',
}

function buildCytoscapeElements(nodes, edges) {
  const elements = []
  const nodeIds = new Set()

  for (const n of nodes) {
    if (!n?.id) continue
    nodeIds.add(n.id)
    const label = n.labels?.[0] || n.entity_type || 'Unknown'
    elements.push({
      data: {
        id: n.id,
        label: (n.name || n.id).slice(0, 20),
        type: label,
        risk_level: n.risk_level || 'LOW',
        pagerank: n.pagerank || 0,
        community: n.community_id ?? -1,
        color: TYPE_COLORS[label] || TYPE_COLORS.Unknown,
        borderColor: RISK_BORDER[n.risk_level] || '#334155',
      },
    })
  }

  for (const e of edges) {
    if (!e?.source || !e?.target) continue
    if (!nodeIds.has(e.source) || !nodeIds.has(e.target)) continue
    elements.push({
      data: {
        id: `${e.source}_${e.type || 'REL'}_${e.target}_${Math.random()}`,
        source: e.source,
        target: e.target,
        label: e.type || '',
        weight: e.weight || 1,
      },
    })
  }

  return elements
}

const CYTOSCAPE_STYLE = [
  {
    selector: 'node',
    style: {
      'background-color': 'data(color)',
      'border-color': 'data(borderColor)',
      'border-width': 2,
      'label': 'data(label)',
      'color': '#e2e8f0',
      'font-size': 10,
      'text-valign': 'bottom',
      'text-margin-y': 4,
      'width': 'mapData(pagerank, 0, 0.01, 20, 50)',
      'height': 'mapData(pagerank, 0, 0.01, 20, 50)',
      'min-zoomed-font-size': 8,
    },
  },
  {
    selector: 'edge',
    style: {
      'line-color': '#334155',
      'target-arrow-color': '#334155',
      'target-arrow-shape': 'triangle',
      'curve-style': 'bezier',
      'width': 'mapData(weight, 1, 10, 1, 3)',
      'opacity': 0.7,
      'label': 'data(label)',
      'font-size': 8,
      'color': '#64748b',
      'text-opacity': 0.6,
    },
  },
  {
    selector: 'node:selected',
    style: {
      'border-color': '#ffffff',
      'border-width': 3,
    },
  },
  {
    selector: 'edge:selected',
    style: { 'line-color': '#ffffff', 'target-arrow-color': '#ffffff' },
  },
]

export default function GraphView() {
  const cyRef = useRef(null)
  const [elements, setElements] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedNode, setSelectedNode] = useState(null)
  const [searchQ, setSearchQ] = useState('')
  const [nodeLimit, setNodeLimit] = useState(300)
  const [filterType, setFilterType] = useState('All')

  const loadGraph = useCallback(async (limit = nodeLimit) => {
    setLoading(true)
    try {
      const { data } = await getNetwork(limit)
      const els = buildCytoscapeElements(data.nodes || [], data.edges || [])
      setElements(els)
      toast.success(`Loaded ${data.total_nodes} nodes, ${data.total_edges} edges`)
    } catch {
      toast.error('Could not load graph — is the backend running?')
    } finally {
      setLoading(false)
    }
  }, [nodeLimit])

  useEffect(() => { loadGraph() }, [])

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!searchQ.trim()) return
    try {
      const { data } = await searchEntities(searchQ)
      if (data.results?.length) {
        const id = data.results[0].n?.id
        if (id && cyRef.current) {
          cyRef.current.$(`#${CSS.escape(id)}`).select()
          cyRef.current.center(cyRef.current.$(`#${CSS.escape(id)}`))
        }
        toast.success(`Found ${data.count} results for "${searchQ}"`)
      } else {
        toast('No matching entities found.')
      }
    } catch { toast.error('Search failed.') }
  }

  const handleNodeClick = useCallback(async (event) => {
    const node = event.target
    const id = node.data('id')
    try {
      const { data } = await getEntity(id, 1)
      setSelectedNode(data)
    } catch {}
  }, [])

  const visibleTypes = ['All', 'Person', 'Organization', 'Location', 'PhoneNumber', 'Vehicle', 'BankAccount']

  const filteredElements = filterType === 'All'
    ? elements
    : elements.filter(el => !el.data.source || el.data.type === filterType)

  return (
    <div className="flex h-screen flex-col p-4 gap-4">
      {/* Toolbar */}
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="text-xl font-bold text-white">Network Graph</h1>

        {/* Search */}
        <form onSubmit={handleSearch} className="flex gap-2 flex-1 max-w-xs">
          <input
            value={searchQ}
            onChange={e => setSearchQ(e.target.value)}
            placeholder="Search entity…"
            className="flex-1 bg-card border border-border rounded-lg px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-accent"
          />
          <button type="submit" className="bg-accent text-white px-3 py-1.5 rounded-lg">
            <Search size={14} />
          </button>
        </form>

        {/* Type filter */}
        <div className="flex gap-1 flex-wrap">
          {visibleTypes.map(t => (
            <button
              key={t}
              onClick={() => setFilterType(t)}
              className={clsx(
                'text-xs px-2 py-1 rounded-md transition-colors',
                filterType === t
                  ? 'bg-accent text-white'
                  : 'bg-card border border-border text-slate-400 hover:text-white'
              )}
            >
              {t}
            </button>
          ))}
        </div>

        {/* Zoom controls */}
        <div className="flex gap-1 ml-auto">
          <button onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 1.2)} className="p-2 bg-card border border-border rounded-lg text-slate-400 hover:text-white">
            <ZoomIn size={16} />
          </button>
          <button onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 0.8)} className="p-2 bg-card border border-border rounded-lg text-slate-400 hover:text-white">
            <ZoomOut size={16} />
          </button>
          <button onClick={() => cyRef.current?.fit()} className="p-2 bg-card border border-border rounded-lg text-slate-400 hover:text-white">
            <Maximize2 size={16} />
          </button>
          <button onClick={() => loadGraph()} className="px-3 py-2 bg-card border border-border rounded-lg text-slate-400 hover:text-white text-xs">
            Reload
          </button>
        </div>
      </div>

      <div className="flex flex-1 gap-4 min-h-0">
        {/* Graph */}
        <div className="flex-1 cy-container relative">
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center z-10 bg-black/40 rounded-lg">
              <div className="text-slate-300 animate-pulse">Loading network…</div>
            </div>
          )}
          <CytoscapeComponent
            elements={filteredElements}
            style={{ width: '100%', height: '100%' }}
            stylesheet={CYTOSCAPE_STYLE}
            layout={{ name: 'cose', animate: true, randomize: false, nodeRepulsion: 8000, idealEdgeLength: 100 }}
            cy={cy => {
              cyRef.current = cy
              cy.on('tap', 'node', handleNodeClick)
            }}
          />

          {/* Legend */}
          <div className="absolute bottom-3 left-3 bg-card/90 border border-border rounded-lg p-3 text-xs space-y-1">
            {Object.entries(TYPE_COLORS).slice(0, 6).map(([type, color]) => (
              <div key={type} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ background: color }} />
                <span className="text-slate-300">{type}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Node Detail Panel */}
        {selectedNode && (
          <div className="w-72 card overflow-y-auto">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-white">Entity Details</h3>
              <button onClick={() => setSelectedNode(null)} className="text-slate-400 hover:text-white">✕</button>
            </div>
            <div className="space-y-3">
              <div>
                <div className="text-xs text-slate-400">Name</div>
                <div className="text-white font-medium">{selectedNode.entity?.n?.name || '—'}</div>
              </div>
              <div>
                <div className="text-xs text-slate-400">Type</div>
                <div className="text-white">{(selectedNode.entity?.labels || []).join(', ') || '—'}</div>
              </div>
              <div>
                <div className="text-xs text-slate-400">Risk Level</div>
                <span className={clsx('text-xs px-2 py-0.5 rounded-full font-semibold',
                  selectedNode.entity?.n?.risk_level === 'CRITICAL' ? 'badge-critical' :
                  selectedNode.entity?.n?.risk_level === 'HIGH'     ? 'badge-high' :
                  selectedNode.entity?.n?.risk_level === 'MEDIUM'   ? 'badge-medium' : 'badge-low'
                )}>
                  {selectedNode.entity?.n?.risk_level || 'UNKNOWN'}
                </span>
              </div>
              <div>
                <div className="text-xs text-slate-400 mb-1">Neighbors ({selectedNode.neighbors?.nodes?.length || 0})</div>
                <div className="space-y-1 max-h-48 overflow-y-auto">
                  {(selectedNode.neighbors?.nodes || []).filter(n => n.id !== selectedNode.entity?.n?.id).slice(0, 15).map((n, i) => (
                    <div key={i} className="text-xs bg-slate-700/50 rounded px-2 py-1 text-slate-300 truncate">
                      {n.name || n.id}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
