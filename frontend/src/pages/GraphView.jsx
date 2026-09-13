import { useState, useEffect, useRef, useCallback } from 'react'
import CytoscapeComponent from 'react-cytoscapejs'
import { getNetwork, getEntity, searchEntities, getCommunities } from '../api/client'
import { Search, ZoomIn, ZoomOut, Maximize2, Filter, Lock, Unlock } from 'lucide-react'
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
      'border-width': 'mapData(pagerank, 0, 0.01, 1, 4)',
      'label': 'data(label)',
      'color': '#e2e8f0',
      'font-size': 'mapData(pagerank, 0, 0.01, 9, 13)',
      'font-weight': 'bold',
      'text-valign': 'center',
      'text-halign': 'center',
      'width': 'mapData(pagerank, 0, 0.01, 30, 70)',
      'height': 'mapData(pagerank, 0, 0.01, 30, 70)',
      'min-zoomed-font-size': 8,
      'cursor': 'pointer',
      'transition-property': 'background-color, border-width',
      'transition-duration': '200ms',
      'shadow-blur': '8',
      'shadow-color': '#000',
      'shadow-opacity': '0.6',
      'shadow-offset-x': '0',
      'shadow-offset-y': '2',
    },
  },
  {
    selector: 'node:hover',
    style: {
      'border-width': 'mapData(pagerank, 0, 0.01, 3, 6)',
      'shadow-blur': '12',
      'shadow-opacity': '0.9',
    },
  },
  {
    selector: 'node:locked',
    style: {
      'border-color': '#fbbf24',
      'border-width': 'mapData(pagerank, 0, 0.01, 3, 6)',
      'background-image-opacity': 0.5,
    },
  },
  {
    selector: 'edge',
    style: {
      'line-color': '#475569',
      'target-arrow-color': '#475569',
      'target-arrow-shape': 'triangle',
      'curve-style': 'bezier',
      'width': 'mapData(weight, 1, 10, 1, 4)',
      'opacity': 0.6,
      'label': 'data(label)',
      'font-size': 9,
      'color': '#cbd5e1',
      'text-opacity': 0.8,
      'text-background-color': '#1e293b',
      'text-background-opacity': 0.8,
      'text-background-padding': '3px',
      'text-border-color': '#475569',
      'text-border-width': 0.5,
    },
  },
  {
    selector: 'edge:hover',
    style: {
      'line-color': '#94a3b8',
      'target-arrow-color': '#94a3b8',
      'opacity': 0.9,
      'width': 'mapData(weight, 1, 10, 2, 5)',
    },
  },
  {
    selector: 'node:selected',
    style: {
      'border-color': '#60a5fa',
      'border-width': 'mapData(pagerank, 0, 0.01, 4, 7)',
      'shadow-blur': '15',
      'shadow-color': '#60a5fa',
      'shadow-opacity': '0.8',
    },
  },
  {
    selector: 'edge:selected',
    style: { 
      'line-color': '#60a5fa',
      'target-arrow-color': '#60a5fa',
      'opacity': 1,
      'width': 'mapData(weight, 1, 10, 3, 6)',
    },
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
  const [pinnedNodes, setPinnedNodes] = useState(new Set())

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
          const node = cyRef.current.$(`#${CSS.escape(id)}`)
          node.select()
          cyRef.current.center(node)
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

  const handleNodeDoubleClick = useCallback((event) => {
    const node = event.target
    if (node.isNode && node.isNode()) {
      const nodeId = node.data('id')
      node.locked(!node.locked())
      setPinnedNodes(prev => {
        const next = new Set(prev)
        if (node.locked()) {
          next.add(nodeId)
        } else {
          next.delete(nodeId)
        }
        return next
      })
      toast.success(node.locked() ? '📌 Node pinned' : '📍 Node unpinned')
    }
  }, [])

  const visibleTypes = ['All', 'Person', 'Organization', 'Location', 'PhoneNumber', 'Vehicle', 'BankAccount']
  const [layoutMode, setLayoutMode] = useState('cose')

  const filteredElements = filterType === 'All'
    ? elements
    : elements.filter(el => !el.data.source || el.data.type === filterType)

  const getLayoutConfig = (mode) => {
    const baseConfig = {
      animate: true,
      animationDuration: 1500,
      animationEasing: 'ease-out',
      tile: true,
      tilingPaddingVertical: 20,
      tilingPaddingHorizontal: 20,
      fit: true,
    }

    switch(mode) {
      case 'cose':
        return { ...baseConfig, name: 'cose', nodeRepulsion: 8000, nodeOverlap: 50, idealEdgeLength: 200, edgeElasticity: 150, nestingFactor: 1.5, gravity: 300, numIter: 300, refresh: 20 }
      case 'concentric':
        return { ...baseConfig, name: 'concentric', concentric: (n) => n.data('pagerank') * 100, minNodeSpacing: 50 }
      case 'hierarchical':
        return { ...baseConfig, name: 'breadthfirst', directed: true, spacingFactor: 1.5 }
      default:
        return { ...baseConfig, name: 'cose' }
    }
  }

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

        {/* Layout Modes */}
        <div className="flex gap-1">
          {[
            { mode: 'cose', label: '🕸️ Force', title: 'Force-directed layout' },
            { mode: 'concentric', label: '◯ Concentric', title: 'Circular by influence' },
            { mode: 'hierarchical', label: '⬇️ Hierarchical', title: 'Top-down layout' },
          ].map(({ mode, label, title }) => (
            <button
              key={mode}
              onClick={() => setLayoutMode(mode)}
              title={title}
              className={clsx(
                'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
                layoutMode === mode
                  ? 'bg-accent text-white'
                  : 'bg-card border border-border text-slate-400 hover:text-white'
              )}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Controls */}
        <div className="flex gap-1 ml-auto">
          <button onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 1.2)} className="p-2 bg-card border border-border rounded-lg text-slate-400 hover:text-white hover:border-accent" title="Zoom in">
            <ZoomIn size={16} />
          </button>
          <button onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 0.8)} className="p-2 bg-card border border-border rounded-lg text-slate-400 hover:text-white hover:border-accent" title="Zoom out">
            <ZoomOut size={16} />
          </button>
          <button onClick={() => cyRef.current?.fit()} className="p-2 bg-card border border-border rounded-lg text-slate-400 hover:text-white hover:border-accent" title="Fit to screen">
            <Maximize2 size={16} />
          </button>
          <button onClick={() => loadGraph()} className="px-3 py-2 bg-card border border-border rounded-lg text-slate-400 hover:text-white hover:border-accent text-xs font-medium">
            ⟳ Reload
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
            layout={getLayoutConfig(layoutMode)}
            cy={cy => {
              cyRef.current = cy
              cy.on('tap', 'node', handleNodeClick)
              cy.on('dbltap', 'node', handleNodeDoubleClick)
              
              // Prevent panning during drag
              cy.on('grab', 'node', () => {
                cy.boxSelectionEnabled(false)
              })
              cy.on('free', 'node', () => {
                cy.boxSelectionEnabled(true)
              })
            }}
          />

          {/* Legend */}
          <div className="absolute bottom-3 left-3 bg-gradient-to-b from-card to-card/80 border border-border rounded-lg p-4 text-xs space-y-3 max-w-xs shadow-lg">
            <div>
              <div className="font-semibold text-slate-200 mb-2">Entity Types</div>
              {Object.entries(TYPE_COLORS).slice(0, 5).map(([type, color]) => (
                <div key={type} className="flex items-center gap-2 mb-1">
                  <div className="w-4 h-4 rounded-full" style={{ background: color }} />
                  <span className="text-slate-300 flex-1">{type}</span>
                </div>
              ))}
            </div>
            <div className="border-t border-border pt-2">
              <div className="font-semibold text-slate-200 mb-1">Risk Levels</div>
              {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(level => (
                <div key={level} className="flex items-center gap-2 mb-1">
                  <div className="w-4 h-4 rounded" style={{ 
                    border: `3px solid ${RISK_BORDER[level]}`,
                    background: 'transparent'
                  }} />
                  <span className="text-slate-300 text-xs flex-1">{level}</span>
                </div>
              ))}
            </div>
            <div className="border-t border-border pt-2">
              <div className="font-semibold text-slate-200 mb-2">Tips</div>
              <div className="space-y-1 text-slate-400 text-xs leading-relaxed">
                <div>💡 <strong>Larger nodes</strong> = more influential</div>
                <div>🖱️ <strong>Click</strong> to view details</div>
                <div>🔓 <strong>Double-click</strong> to pin node</div>
                <div>🔍 <strong>Scroll</strong> to zoom</div>
              </div>
            </div>
          </div>
        </div>

        {/* Node Detail Panel */}
        {selectedNode && (
          <div className="w-80 card overflow-y-auto shadow-2xl border-l-4" style={{ borderColor: TYPE_COLORS[selectedNode.entity?.labels?.[0]] || '#64748b' }}>
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-border">
              <div>
                <h3 className="font-bold text-white text-lg">{selectedNode.entity?.n?.name || 'Unknown'}</h3>
                <div className="text-xs text-slate-400 mt-1">{(selectedNode.entity?.labels || []).join(', ') || 'Unknown Type'}</div>
              </div>
              <button onClick={() => setSelectedNode(null)} className="text-slate-400 hover:text-white text-xl">✕</button>
            </div>
            <div className="space-y-4">
              {/* Risk Level */}
              <div>
                <div className="text-xs text-slate-400 font-semibold uppercase mb-2">Threat Level</div>
                <span className={clsx('inline-block text-xs px-3 py-1 rounded-full font-bold',
                  selectedNode.entity?.n?.risk_level === 'CRITICAL' ? 'bg-red-900/50 text-red-200 border border-red-700' :
                  selectedNode.entity?.n?.risk_level === 'HIGH'     ? 'bg-orange-900/50 text-orange-200 border border-orange-700' :
                  selectedNode.entity?.n?.risk_level === 'MEDIUM'   ? 'bg-yellow-900/50 text-yellow-200 border border-yellow-700' : 
                  'bg-green-900/50 text-green-200 border border-green-700'
                )}>
                  {selectedNode.entity?.n?.risk_level || 'UNKNOWN'}
                </span>
              </div>

              {/* Influence Score */}
              {selectedNode.entity?.n?.pagerank && (
                <div>
                  <div className="text-xs text-slate-400 font-semibold uppercase mb-2">Influence Score</div>
                  <div className="w-full bg-slate-700 rounded-full h-2">
                    <div 
                      className="bg-gradient-to-r from-blue-500 to-cyan-400 h-2 rounded-full" 
                      style={{ width: `${Math.min(selectedNode.entity?.n?.pagerank * 1000, 100)}%` }}
                    />
                  </div>
                  <div className="text-xs text-slate-300 mt-1">{(selectedNode.entity?.n?.pagerank * 1000).toFixed(1)}</div>
                </div>
              )}

              {/* ID */}
              <div>
                <div className="text-xs text-slate-400 font-semibold uppercase mb-1">ID</div>
                <div className="text-xs text-slate-300 font-mono bg-slate-800/50 p-2 rounded break-all">{selectedNode.entity?.n?.id || '—'}</div>
              </div>

              {/* Connected Entities */}
              <div>
                <div className="text-xs text-slate-400 font-semibold uppercase mb-2">
                  Connected Entities ({selectedNode.neighbors?.nodes?.length || 0})
                </div>
                {selectedNode.neighbors?.nodes && selectedNode.neighbors.nodes.length > 0 ? (
                  <div className="space-y-1 max-h-64 overflow-y-auto">
                    {selectedNode.neighbors.nodes.filter(n => n.id !== selectedNode.entity?.n?.id).slice(0, 20).map((n, i) => (
                      <div key={i} className="text-xs bg-slate-800/50 rounded px-3 py-2 text-slate-200 flex items-center gap-2 hover:bg-slate-700 transition-colors">
                        <div 
                          className="w-2 h-2 rounded-full flex-shrink-0" 
                          style={{ background: TYPE_COLORS[n.labels?.[0]] || '#64748b' }}
                        />
                        <div className="flex-1 min-w-0">
                          <div className="truncate font-medium">{n.name || n.id}</div>
                          <div className="text-slate-500 text-xs">{n.labels?.[0] || 'Unknown'}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-xs text-slate-500 italic">No connections found</div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
