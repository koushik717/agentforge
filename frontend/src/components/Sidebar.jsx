import { usePolling } from '../hooks';
import { api } from '../api';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
const BACKEND_BASE = API_BASE.replace('/api/v1', '');
const GRAFANA_URL = import.meta.env.VITE_GRAFANA_URL || 'http://localhost:3001';

export default function Sidebar({ currentPage, onNavigate }) {
  const { data: health } = usePolling(() => api.health(), 10000);

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">AF</div>
        <div>
          <div className="sidebar-title">AgentForge</div>
          <div className="sidebar-version">v0.1.0</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-section-label">Overview</div>
        <button
          className={`nav-item ${currentPage === 'dashboard' ? 'active' : ''}`}
          onClick={() => onNavigate('dashboard')}
        >
          <span className="nav-item-icon">&bull;</span>
          Dashboard
        </button>

        <div className="nav-section-label">Manage</div>
        <button
          className={`nav-item ${currentPage === 'agents' ? 'active' : ''}`}
          onClick={() => onNavigate('agents')}
        >
          <span className="nav-item-icon">&bull;</span>
          Agents
        </button>
        <button
          className={`nav-item ${currentPage === 'runs' ? 'active' : ''}`}
          onClick={() => onNavigate('runs')}
        >
          <span className="nav-item-icon">&bull;</span>
          Runs
        </button>

        <div className="nav-section-label">System</div>
        <a
          className="nav-item"
          href={`${BACKEND_BASE}/docs`}
          target="_blank"
          rel="noopener"
        >
          <span className="nav-item-icon">&bull;</span>
          API Docs
        </a>
        <a
          className="nav-item"
          href={GRAFANA_URL}
          target="_blank"
          rel="noopener"
        >
          <span className="nav-item-icon">&bull;</span>
          Grafana
        </a>
      </nav>

      <div className="sidebar-footer">
        <div className="flex items-center gap-8" style={{ fontSize: 13 }}>
          <span style={{
            background: health?.status === 'ok' ? 'var(--success)' : 'var(--danger)',
            width: 8, height: 8, borderRadius: '50%', display: 'inline-block',
          }}></span>
          <span className="text-muted">
            {health?.status === 'ok' ? 'All systems operational' : 'Connecting...'}
          </span>
        </div>
      </div>
    </aside>
  );
}
