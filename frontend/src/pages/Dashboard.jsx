import { usePolling } from '../hooks';
import { api } from '../api';

export default function Dashboard({ onNavigate }) {
  const { data: health } = usePolling(() => api.health(), 5000);
  const { data: agentsData } = usePolling(() => api.getAgents(5), 5000);
  const { data: runsData } = usePolling(() => api.getRuns(null, 10), 5000);
  const { data: providers } = usePolling(() => api.getProviders(), 15000);
  const { data: tools } = usePolling(() => api.getTools(), 15000);

  const agents = agentsData?.agents || [];
  const runs = runsData?.runs || [];
  const totalAgents = agentsData?.total || 0;
  const totalRuns = runsData?.total || 0;
  const completedRuns = runs.filter(r => r.status === 'completed').length;

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Dashboard</h1>
        <p className="page-subtitle">Real-time overview of your agent runtime</p>
      </div>

      <div className="page-content">
        {/* Stats */}
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-label">Active Agents</div>
            <div className="stat-value">{totalAgents}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Total Runs</div>
            <div className="stat-value">{totalRuns}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Completed (recent)</div>
            <div className="stat-value">{completedRuns}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Uptime</div>
            <div className="stat-value">{health?.uptime_seconds ? formatUptime(health.uptime_seconds) : '--'}</div>
          </div>
        </div>

        <div className="grid-2">
          {/* System Status */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">System Status</h3>
              <span className={`badge ${health?.status === 'ok' ? 'badge-success' : 'badge-danger'}`}>
                <span className="badge-dot"></span>
                {health?.status || 'unknown'}
              </span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <StatusRow label="Database" connected={health?.db_connected} />
              <StatusRow label="Redis" connected={health?.redis_connected} />
              <StatusRow label="API Version" value={health?.version} />
              <StatusRow label="Environment" value={health?.environment} />
              <StatusRow label="LLM Providers" value={providers?.providers?.length || 0} />
              <StatusRow label="Tools Available" value={tools?.tools?.length || 0} />
            </div>
          </div>

          {/* Recent Runs */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Recent Runs</h3>
              <button className="btn btn-sm btn-secondary" onClick={() => onNavigate('runs')}>
                View All
              </button>
            </div>
            {runs.length === 0 ? (
              <div className="empty-state" style={{ padding: 30 }}>
                <div className="text-muted text-sm">No runs yet. Create an agent and start a run.</div>
              </div>
            ) : (
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Input</th>
                      <th>Status</th>
                      <th>Latency</th>
                    </tr>
                  </thead>
                  <tbody>
                    {runs.slice(0, 5).map(run => (
                      <tr key={run.id}>
                        <td className="truncate" style={{ maxWidth: 200 }}>{run.input}</td>
                        <td><StatusBadge status={run.status} /></td>
                        <td className="mono text-sm">{run.latency_ms ? `${run.latency_ms.toFixed(0)}ms` : '--'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Agents Overview */}
        {agents.length > 0 && (
          <div className="card" style={{ marginTop: 20 }}>
            <div className="card-header">
              <h3 className="card-title">Agents</h3>
              <button className="btn btn-sm btn-secondary" onClick={() => onNavigate('agents')}>
                Manage
              </button>
            </div>
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Provider</th>
                    <th>Model</th>
                    <th>Tools</th>
                    <th>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {agents.map(agent => (
                    <tr key={agent.id} onClick={() => onNavigate('agent-detail', agent.id)}>
                      <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{agent.name}</td>
                      <td><span className="badge badge-info">{agent.provider}</span></td>
                      <td className="mono text-sm">{agent.model}</td>
                      <td>
                        <div className="flex gap-4" style={{ flexWrap: 'wrap', gap: 4 }}>
                          {agent.tools.map(t => (
                            <span key={t} className="tool-tag">{t}</span>
                          ))}
                        </div>
                      </td>
                      <td className="text-sm text-muted">{new Date(agent.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

function StatusRow({ label, connected, value }) {
  return (
    <div className="flex items-center justify-between" style={{ padding: '6px 0' }}>
      <span className="text-sm text-muted">{label}</span>
      {connected !== undefined ? (
        <span className={`badge ${connected ? 'badge-success' : 'badge-danger'}`}>
          {connected ? 'Connected' : 'Disconnected'}
        </span>
      ) : (
        <span className="text-sm mono">{value}</span>
      )}
    </div>
  );
}

function StatusBadge({ status }) {
  const map = {
    completed: 'badge-success',
    running: 'badge-info',
    pending: 'badge-warning',
    failed: 'badge-danger',
  };
  return (
    <span className={`badge ${map[status] || 'badge-muted'}`}>
      {status === 'running' && <span className="badge-dot"></span>}
      {status}
    </span>
  );
}

function formatUptime(seconds) {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  if (seconds < 86400) return `${(seconds / 3600).toFixed(1)}h`;
  return `${(seconds / 86400).toFixed(1)}d`;
}
