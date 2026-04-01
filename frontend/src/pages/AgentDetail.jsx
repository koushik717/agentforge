import { useState } from 'react';
import { usePolling, useApi } from '../hooks';
import { api } from '../api';

export default function AgentDetail({ agentId, onNavigate }) {
  const { data: agent, loading, refetch: refetchAgent } = useApi(() => api.getAgent(agentId), [agentId]);
  const { data: runsData, refetch: refetchRuns } = usePolling(() => api.getRuns(agentId, 20), 3000, [agentId]);
  const [input, setInput] = useState('');
  const [running, setRunning] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const runs = runsData?.runs || [];

  const handleRun = async (sync) => {
    if (!input.trim()) return;
    setRunning(true);
    try {
      if (sync) {
        await api.createRunSync({ agent_id: agentId, input });
      } else {
        await api.createRun({ agent_id: agentId, input });
      }
      setInput('');
      refetchRuns();
    } catch (err) {
      alert(err.message);
    } finally {
      setRunning(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm('Delete this agent and all its runs?')) return;
    setDeleting(true);
    try {
      await api.deleteAgent(agentId);
      onNavigate('agents');
    } catch (err) {
      alert(err.message);
      setDeleting(false);
    }
  };

  if (loading || !agent) {
    return (
      <div className="loading-page">
        <div className="spinner"></div>
        Loading agent...
      </div>
    );
  }

  return (
    <>
      <div className="page-header">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-12" style={{ marginBottom: 4 }}>
              <button
                className="btn btn-sm btn-secondary"
                onClick={() => onNavigate('agents')}
                style={{ padding: '4px 12px', fontSize: 14 }}
              >
                Back
              </button>
              <h1 className="page-title">{agent.name}</h1>
            </div>
            <p className="page-subtitle">{agent.description || 'No description'}</p>
          </div>
          <button className="btn btn-sm btn-danger" onClick={handleDelete} disabled={deleting}>
            {deleting ? 'Deleting...' : 'Delete'}
          </button>
        </div>
      </div>

      <div className="page-content">
        {/* Agent Config */}
        <div className="grid-2" style={{ marginBottom: 24 }}>
          <div className="card">
            <h3 className="card-title" style={{ marginBottom: 16 }}>Configuration</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <ConfigRow label="Provider" value={agent.provider} badge />
              <ConfigRow label="Model" value={agent.model} mono />
              <ConfigRow label="Created" value={new Date(agent.created_at).toLocaleString()} />
              <ConfigRow label="ID" value={agent.id} mono small />
            </div>
            {agent.tools.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <span className="text-sm text-muted">Tools: </span>
                <div className="flex gap-8" style={{ marginTop: 6, flexWrap: 'wrap' }}>
                  {agent.tools.map(t => <span key={t} className="tool-tag">{t}</span>)}
                </div>
              </div>
            )}
          </div>

          <div className="card">
            <h3 className="card-title" style={{ marginBottom: 12 }}>System Prompt</h3>
            <div className="run-output" style={{ maxHeight: 180 }}>
              {agent.system_prompt}
            </div>
          </div>
        </div>

        {/* Run Input */}
        <div className="card" style={{ marginBottom: 24 }}>
          <h3 className="card-title" style={{ marginBottom: 12 }}>Execute Run</h3>
          <div className="flex gap-12">
            <textarea
              className="form-textarea"
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Enter your prompt here..."
              style={{ minHeight: 60, flex: 1 }}
            />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <button
                className="btn btn-primary"
                onClick={() => handleRun(true)}
                disabled={running || !input.trim()}
              >
                {running ? <span className="spinner" style={{ width: 16, height: 16 }}></span> : null}
                {running ? ' Running...' : 'Run Sync'}
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => handleRun(false)}
                disabled={running || !input.trim()}
              >
                Queue Async
              </button>
            </div>
          </div>
        </div>

        {/* Runs History */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Run History</h3>
            <span className="text-sm text-muted">{runsData?.total || 0} runs</span>
          </div>
          {runs.length === 0 ? (
            <div className="empty-state" style={{ padding: 30 }}>
              <div className="text-muted text-sm" style={{ marginTop: 8 }}>No runs yet for this agent</div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {runs.map(run => (
                <RunCard key={run.id} run={run} />
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function ConfigRow({ label, value, badge, mono, small }) {
  return (
    <div className="flex items-center justify-between" style={{ padding: '4px 0' }}>
      <span className="text-sm text-muted">{label}</span>
      {badge ? (
        <span className="badge badge-info">{value}</span>
      ) : (
        <span className={`text-sm ${mono ? 'mono' : ''} ${small ? 'text-xs text-muted' : ''}`}
              style={small ? { maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' } : {}}>
          {value}
        </span>
      )}
    </div>
  );
}

function RunCard({ run }) {
  const [expanded, setExpanded] = useState(false);
  const statusMap = {
    completed: 'badge-success',
    running: 'badge-info',
    pending: 'badge-warning',
    failed: 'badge-danger',
  };

  return (
    <div
      style={{
        background: 'var(--bg-input)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-md)',
        padding: 16,
        cursor: 'pointer',
        transition: 'border-color 0.2s',
      }}
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-center justify-between" style={{ marginBottom: expanded ? 12 : 0 }}>
        <div className="flex items-center gap-12">
          <span className={`badge ${statusMap[run.status] || 'badge-muted'}`}>
            {run.status === 'running' && <span className="badge-dot"></span>}
            {run.status}
          </span>
          <span className="text-sm truncate" style={{ maxWidth: 400 }}>{run.input}</span>
        </div>
        <div className="flex items-center gap-12">
          {run.tokens_used > 0 && <span className="text-xs mono text-muted">{run.tokens_used} tok</span>}
          {run.latency_ms > 0 && <span className="text-xs mono text-muted">{run.latency_ms.toFixed(0)}ms</span>}
          <span className="text-xs text-muted">{new Date(run.created_at).toLocaleTimeString()}</span>
        </div>
      </div>
      {expanded && (
        <div>
          <div className="text-xs text-muted" style={{ marginBottom: 6 }}>Output:</div>
          <div className="run-output">
            {run.output || (run.error ? `Error: ${run.error}` : 'Waiting for response...')}
          </div>
        </div>
      )}
    </div>
  );
}
