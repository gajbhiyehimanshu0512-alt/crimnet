import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Network, Search, Clock,
  FileText, Upload, Shield, Briefcase, LogOut
} from 'lucide-react'
import clsx from 'clsx'
import { useAuth } from '../auth/AuthContext'

const NAV = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/graph',     icon: Network,         label: 'Network Graph' },
  { to: '/search',    icon: Search,          label: 'Investigator AI' },
  { to: '/timeline',  icon: Clock,           label: 'Timeline' },
  { to: '/reports',   icon: FileText,        label: 'Reports' },
  { to: '/ingest',    icon: Upload,          label: 'Data Ingestion' },
  { to: '/cases',     icon: Briefcase,       label: 'Cases' },
]

export default function Sidebar() {
  return (
    <aside className="w-64 flex-shrink-0 bg-card border-r border-border flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-border flex items-center gap-3">
        <Shield className="text-accent" size={28} />
        <div>
          <div className="font-bold text-white text-lg leading-tight">CrimNet</div>
          <div className="text-xs text-slate-400">Network Analyzer</div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all',
                isActive
                  ? 'bg-accent/20 text-accent font-medium border border-accent/30'
                  : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
              )
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* User + Logout */}
      <UserFooter />
    </aside>
  )
}


function UserFooter() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="p-4 border-t border-border">
      {user && (
        <div className="flex items-center justify-between mb-2">
          <div className="text-xs">
            <div className="text-white font-medium">{user.full_name || user.username}</div>
            <div className="text-slate-500">{user.role}</div>
          </div>
          <button
            onClick={handleLogout}
            className="text-slate-400 hover:text-accent transition-colors"
            title="Logout"
          >
            <LogOut size={16} />
          </button>
        </div>
      )}
      <div className="text-xs text-slate-500">v1.0.0 · For Law Enforcement Use Only</div>
    </div>
  )
}
