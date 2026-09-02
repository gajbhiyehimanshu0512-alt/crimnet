import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth/AuthContext'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import GraphView from './pages/GraphView'
import InvestigatorSearch from './pages/InvestigatorSearch'
import Timeline from './pages/Timeline'
import Reports from './pages/Reports'
import DataIngestion from './pages/DataIngestion'
import Cases from './pages/Cases'
import Login from './pages/Login'

function ProtectedRoute({ children }) {
  const { token } = useAuth()
  if (!token) return <Navigate to="/login" replace />
  return children
}

function DashboardLayout() {
  return (
    <div className="flex h-screen overflow-hidden bg-surface">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/"          element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/graph"     element={<GraphView />} />
          <Route path="/search"    element={<InvestigatorSearch />} />
          <Route path="/timeline"  element={<Timeline />} />
          <Route path="/reports"   element={<Reports />} />
          <Route path="/ingest"    element={<DataIngestion />} />
          <Route path="/cases"     element={<Cases />} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/*" element={<ProtectedRoute><DashboardLayout /></ProtectedRoute>} />
      </Routes>
    </AuthProvider>
  )
}
