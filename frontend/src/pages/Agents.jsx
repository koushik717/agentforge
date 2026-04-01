import { useState } from 'react';
import { usePolling } from '../hooks';
import { api } from '../api';

export default function Agents({ onNavigate }) {
  const { data, loading, refetch } = usePolling(() => api.getAgents(), 5000);
  const [showCreate, setShowCreate] = useState(false);

  const agents = data?.agents || [];

  return (
    <>
      <div className="page-header">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="page-title">Agents</h1>
            <p className="page-subtitle">{data?.total || 0} agents configured</p>
          </div>
          <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
            + New Agent
          </button>
        </div>
      </div>

      <div className="page-content">
        {loading && agents.length === 0 ? (
          <div className="loading-page">
            <div className="spinner"></div>
            Loading agents...
          </div>
        ) : agents.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-title">No agents configured</div>
            <div className="empty-state-text">Create your first AI agent to get started</div>
            <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
              + New Agent
            </button>
          </div>
        ) : (
          <div className="agent-grid">
            {agents.map(agent => (
              <div
                key={agent.id}
                className="agent-card"
                onClick={() => onNavigate('agent-detail', agent.id)}
              >
                <div className="agent-card-name">{agent.name}</div>
                <div className="agent-card-desc">{agent.description || 'No description'}</div>
                <div className="agent-card-meta">
                  <span className="badge badge-info">{agent.provider}</span>
                  <span className="mono text-xs text-muted">{agent.model}</span>
                </div>
                {agent.tools.length > 0 && (
                  <div className="agent-card-tools">
                    {agent.tools.map(t => <span key={t} className="tool-tag">{t}</span>)}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {showCreate && (
        <CreateAgentModal
          onClose={() => setShowCreate(false)}
          onCreated={() => { setShowCreate(false); refetch(); }}
        />
      )}
    </>
  );
}

function CreateAgentModal({ onClose, onCreated }) {
  const [form, setForm] = useState({
    name: '',
    description: '',
    system_prompt: 'You are a helpful assistant.',
    provider: 'groq',
    model: 'llama-3.3-70b-versatile',
    tools: [],
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const toggleTool = (tool) => {
    setForm(f => ({
      ...f,
      tools: f.tools.includes(tool) ? f.tools.filter(t => t !== tool) : [...f.tools, tool],
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await api.createAgent(form);
      onCreated();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const models = {
    groq: ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant', 'mixtral-8x7b-32768'],
    gemini: ['gemini-2.0-flash', 'gemini-1.5-pro'],
    openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-3.5-turbo'],
    ollama: ['llama3.2', 'mistral', 'codellama'],
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">New Agent</h2>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Name *</label>
            <input
              className="form-input"
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              placeholder="Research Assistant"
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Description</label>
            <input
              className="form-input"
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              placeholder="An agent that helps with research tasks"
            />
          </div>

          <div className="grid-2">
            <div className="form-group">
              <label className="form-label">Provider</label>
              <select
                className="form-select"
                value={form.provider}
                onChange={e => setForm(f => ({
                  ...f,
                  provider: e.target.value,
                  model: models[e.target.value]?.[0] || '',
                }))}
              >
                <option value="groq">Groq</option>
                <option value="gemini">Gemini</option>
                <option value="openai">OpenAI</option>
                <option value="ollama">Ollama</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Model</label>
              <select
                className="form-select"
                value={form.model}
                onChange={e => setForm(f => ({ ...f, model: e.target.value }))}
              >
                {(models[form.provider] || []).map(m => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">System Prompt</label>
            <textarea
              className="form-textarea"
              value={form.system_prompt}
              onChange={e => setForm(f => ({ ...f, system_prompt: e.target.value }))}
              rows={4}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Tools</label>
            <div className="flex gap-8" style={{ marginTop: 6 }}>
              {['web_search', 'calculator'].map(tool => (
                <label key={tool} className="flex items-center gap-8" style={{ cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={form.tools.includes(tool)}
                    onChange={() => toggleTool(tool)}
                    style={{ accentColor: 'var(--accent)' }}
                  />
                  <span className="text-sm">{tool}</span>
                </label>
              ))}
            </div>
          </div>

          {error && (
            <div className="badge badge-danger" style={{ marginBottom: 16, padding: '8px 14px', width: '100%' }}>
              {error}
            </div>
          )}

          <div className="flex gap-12" style={{ justifyContent: 'flex-end' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? <><span className="spinner" style={{ width: 16, height: 16 }}></span> Creating...</> : 'Create Agent'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
