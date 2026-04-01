const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok && res.status !== 204) {
    const error = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  // Health
  health: () => request('/health'),

  // Agents
  getAgents: (limit = 50, offset = 0) => request(`/agents?limit=${limit}&offset=${offset}`),
  getAgent: (id) => request(`/agents/${id}`),
  createAgent: (data) => request('/agents', { method: 'POST', body: JSON.stringify(data) }),
  deleteAgent: (id) => request(`/agents/${id}`, { method: 'DELETE' }),

  // Runs
  getRuns: (agentId, limit = 50) => {
    const params = agentId ? `?agent_id=${agentId}&limit=${limit}` : `?limit=${limit}`;
    return request(`/runs${params}`);
  },
  getRun: (id) => request(`/runs/${id}`),
  createRun: (data) => request('/runs', { method: 'POST', body: JSON.stringify(data) }),
  createRunSync: (data) => request('/runs/sync', { method: 'POST', body: JSON.stringify(data) }),

  // System
  getTools: () => request('/tools'),
  getProviders: () => request('/providers'),
};
