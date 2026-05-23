import { Component } from 'react'
import type { ReactNode } from 'react'

interface State {
  error: Error | null
}

export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  constructor(props: { children: ReactNode }) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error: Error) {
    return { error }
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex items-center justify-center h-full p-6">
          <div className="card p-6 max-w-lg w-full space-y-3">
            <div className="text-red-400 font-semibold">Render error</div>
            <pre className="text-xs text-slate-400 bg-slate-950 rounded p-3 overflow-auto max-h-48 whitespace-pre-wrap">
              {this.state.error.message}
              {'\n'}
              {this.state.error.stack?.split('\n').slice(1, 6).join('\n')}
            </pre>
            <button
              className="btn-ghost text-sm"
              onClick={() => this.setState({ error: null })}
            >
              Dismiss
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
