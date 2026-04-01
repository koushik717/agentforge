import { useState } from 'react';
import { usePolling } from '../hooks';
import { api } from '../api';

export default function Runs({ onNavigate }) {
  const { data, loading } = usePolling(() => api.getRuns(null, 100), 3000);
  const [filter, setFilter] = useState('all');

  const runs = data?.runs || [];
  const filtered = filter === 'all' ? runs : runs.filter(r => r.status === filter);

  const counts = {
    all: runs.length,
    completed: runs.filter(r => r.status === 'completed').length,
    running: runs.filter(r => r.status === 'running').length,
    pending: runs.filter(r => r.status === 'pending').length,
    failed: runs.filter(r => r.status === 'failed').length,
  };

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Runs</h1>
        <p className="page-subtitle">Agent execution history -- {data?.total || 0} total runs</p>
      </div>

      <div className="page-content">
        {/* Filter Tabs */}
        <div className="flex gap-8" style={{ marginBottom: 24 }}>
          {['all', 'completed', 'running', 'pending', 'failed'].map(status => (
            <button
              key={status}
              className={`btn btn-sm ${filter === status ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setFilter(status)}
            >
              {status.charAt(0).toUpperCase() + status.slice(1)}
              <span className="mono" style={{ marginLeft: 4, opacity: 0.7 }}>({counts[status]})</span>
            </button>
          ))}
        </div>

        {loading && runs.length === 0 ? (
          <div className="loading-page">
            <div className="spinner"></div>
            Loading runs...
          </div>
        ) : filtered.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-title">No runs found</div>
            <div className="empty-state-text">
              {filter === 'all'
                ? 'Execute a run from an agent detail page'
                : `No runs with status "${filter}"`}
            </div>
          </div>
        ) : (
          <div className="card">
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Status</th>
                    <th>Input</th>
                    <th>Output</th>
                    <th>Tokens</th>
                    <th>Latency</th>
                    <th>Time</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map(run => (
                    <tr key={run.id}>
                      <td><StatusBadge status={run.status} /></td>
                      <td className="truncate" style={{ maxWidth: 250 }}>{run.input}</td>
                      <td className="truncate text-sm" style={{ maxWidth: 300 }}>
                        {run.output || (run.error ? <span style={{ color: 'var(--danger)' }}>{run.error}</span> : '--')}
                      </td>
                      <td className="mono text-sm">{run.tokens_used || '--'}</td>
                      <td className="mono text-sm">
                        {run.latency_ms ? `${run.latency_ms.toFixed(0)}ms` : '--'}
                      </td>
                      <td className="text-sm text-muted" style={{ whiteSpace: 'nowrap' }}>
                        {new Date(run.created_at).toLocaleString()}
                      </td>
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
