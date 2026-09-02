import { useState, useEffect } from 'react'
import { getGraphStats, getInfluencers, getAnomalies, runAnalytics } from '../api/client'
import { Users, MapPin, Phone, Car, AlertTriangle, Network, TrendingUp, Zap } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import toast from 'react-hot-toast'
import clsx from 'clsx'

const RISK_COLORS = { CRITICAL: '#ef4444', HIGH: '#f97316', MEDIUM: '#eab308', LOW: '#22c55e' }

function StatCard({ icon: Icon, label, value, color = 'text-blue-400' }) {
  return (
    <div className="card flex items-center gap-4">
      <div className={clsx('p-3 rounded-lg bg-slate-700', color)}>
        <Icon size={22} />
      </div>
      <div>
        <div className="text-2xl font-bold text-white">{value ?? '—'}</div>
        <div className="text-sm text-slate-400">{label}</div>
      </div>
    </div>
  )
}

function RiskBadge({ level }) {
  const classes = {
    CRITICAL: 'badge-critical',
    HIGH: 'badge-high',
    MEDIUM: 'badge-medium',
    LOW: 'badge-low',
  }
  return (
    <span className={clsx('text-xs px-2 py-0.5 rounded-full font-semibold', classes[level] || 'bg-slate-700 text-slate-300')}>
      {level}
    </span>
  )
}

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [influencers, setInfluencers] = useState([])
  const [alerts, setAlerts] = useState([])
  const [running, setRunning] = useState(false)

  useEffect(() => {
    Promise.all([
      getGraphStats().then(r => setStats(r.data)).catch(() => {}),
      getInfluencers(10).then(r => setInfluencers(r.data.influencers || [])).catch(() => {}),
      getAnomalies().then(r => setAlerts(r.data.alerts || [])).catch(() => {}),
    ])
  }, [])

  const handleRunAnalytics = async () => {
    setRunning(true)
    try {
      await runAnalytics()
      toast.success('Analytics pipeline complete!')
      getInfluencers(10).then(r => setInfluencers(r.data.influencers || []))
      getAnomalies().then(r => setAlerts(r.data.alerts || []))
    } catch {
      toast.error('Analytics failed — is the backend running?')
    } finally {
      setRunning(false)
    }
  }

  const chartData = influencers.slice(0, 8).map(i => ({
    name: (i.name || 'Unknown').slice(0, 12),
    pagerank: +(i.pagerank * 1000).toFixed(2),
    risk: i.risk_level,
  }))

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Intelligence Dashboard</h1>
          <p className="text-slate-400 text-sm">Criminal network analysis overview</p>
        </div>
        <button
          onClick={handleRunAnalytics}
          disabled={running}
          className="flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50 transition-colors"
        >
          <Zap size={16} />
          {running ? 'Running…' : 'Run Analytics'}
        </button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={Users}         label="Total Persons"     value={stats?.persons}       color="text-blue-400" />
        <StatCard icon={Network}       label="Organizations"     value={stats?.organizations}  color="text-purple-400" />
        <StatCard icon={MapPin}        label="Locations"         value={stats?.locations}      color="text-green-400" />
        <StatCard icon={Phone}         label="Phone Numbers"     value={stats?.phones}         color="text-yellow-400" />
        <StatCard icon={Car}           label="Vehicles"          value={stats?.vehicles}       color="text-cyan-400" />
        <StatCard icon={TrendingUp}    label="Total Relations"   value={stats?.total_edges}    color="text-pink-400" />
        <StatCard icon={AlertTriangle} label="Critical Risk"     value={stats?.critical_risk}  color="text-red-400" />
        <StatCard icon={AlertTriangle} label="High Risk"         value={stats?.high_risk}      color="text-orange-400" />
      </div>

      {/* Bottom grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Influencers Chart */}
        <div className="card">
          <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
            <TrendingUp size={18} className="text-accent" />
            Top Influencers (PageRank)
          </h2>
          {chartData.length ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={chartData} layout="vertical" margin={{ left: 10 }}>
                <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <YAxis dataKey="name" type="category" tick={{ fill: '#e2e8f0', fontSize: 11 }} width={90} />
                <Tooltip
                  contentStyle={{ background: '#1e293b', border: '1px solid #334155', color: '#e2e8f0' }}
                  formatter={v => [v, 'PageRank ×1000']}
                />
                <Bar dataKey="pagerank" radius={[0, 4, 4, 0]}>
                  {chartData.map((d, i) => (
                    <Cell key={i} fill={RISK_COLORS[d.risk] || '#3b82f6'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="text-slate-500 text-sm text-center py-12">
              No data — ingest documents and run analytics first.
            </div>
          )}
        </div>

        {/* Alert Feed */}
        <div className="card">
          <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
            <AlertTriangle size={18} className="text-accent" />
            Anomaly Alerts
            {alerts.length > 0 && (
              <span className="ml-auto bg-red-600 text-white text-xs px-2 py-0.5 rounded-full">
                {alerts.length}
              </span>
            )}
          </h2>
          <div className="space-y-3 max-h-64 overflow-y-auto">
            {alerts.length ? alerts.slice(0, 8).map((a, i) => (
              <div key={i} className="flex items-start gap-3 p-3 bg-slate-800/50 rounded-lg border border-slate-700">
                <AlertTriangle size={16} className={clsx(
                  'mt-0.5 flex-shrink-0',
                  a.severity === 'CRITICAL' ? 'text-red-400' :
                  a.severity === 'HIGH'     ? 'text-orange-400' : 'text-yellow-400'
                )} />
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-sm font-medium text-white truncate">{a.entity_name}</span>
                    <RiskBadge level={a.severity} />
                  </div>
                  <p className="text-xs text-slate-400 line-clamp-2">{a.description}</p>
                </div>
              </div>
            )) : (
              <div className="text-slate-500 text-sm text-center py-8">
                No alerts — run analytics to detect anomalies.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Influencers Table */}
      {influencers.length > 0 && (
        <div className="card">
          <h2 className="text-white font-semibold mb-4">Key Influencers Leaderboard</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-400 border-b border-border">
                  <th className="text-left py-2 pr-4">#</th>
                  <th className="text-left py-2 pr-4">Name</th>
                  <th className="text-left py-2 pr-4">Type</th>
                  <th className="text-right py-2 pr-4">PageRank</th>
                  <th className="text-right py-2 pr-4">Betweenness</th>
                  <th className="text-right py-2">Risk</th>
                </tr>
              </thead>
              <tbody>
                {influencers.map((inf, i) => (
                  <tr key={i} className="border-b border-border/50 hover:bg-slate-700/30">
                    <td className="py-2 pr-4 text-slate-500">{i + 1}</td>
                    <td className="py-2 pr-4 font-medium text-white">{inf.name}</td>
                    <td className="py-2 pr-4 text-slate-400">{(inf.labels || [])[0] || '—'}</td>
                    <td className="py-2 pr-4 text-right text-blue-300">{(inf.pagerank * 1000).toFixed(2)}</td>
                    <td className="py-2 pr-4 text-right text-purple-300">{((inf.betweenness_centrality || 0) * 100).toFixed(1)}%</td>
                    <td className="py-2 text-right"><RiskBadge level={inf.risk_level || 'LOW'} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
