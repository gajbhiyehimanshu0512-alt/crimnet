import { Component } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo)
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center h-full p-8 text-center">
          <AlertTriangle size={48} className="text-red-400 mb-4" />
          <h2 className="text-xl font-bold text-white mb-2">Something went wrong</h2>
          <p className="text-slate-400 text-sm mb-6 max-w-md">
            {this.state.error?.message || 'An unexpected error occurred while rendering this page.'}
          </p>
          <button
            onClick={this.handleRetry}
            className="flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg text-sm font-medium hover:bg-red-700 transition-colors"
          >
            <RefreshCw size={16} />
            Try Again
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
