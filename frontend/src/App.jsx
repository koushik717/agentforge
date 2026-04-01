import { useState } from 'react';
import { api } from './api';
import { usePolling, useApi } from './hooks';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import Agents from './pages/Agents';
import AgentDetail from './pages/AgentDetail';
import Runs from './pages/Runs';

export default function App() {
  const [page, setPage] = useState('dashboard');
  const [selectedAgentId, setSelectedAgentId] = useState(null);

  const navigate = (p, agentId) => {
    setPage(p);
    if (agentId) setSelectedAgentId(agentId);
  };

  const renderPage = () => {
    switch (page) {
      case 'dashboard':
        return <Dashboard onNavigate={navigate} />;
      case 'agents':
        return <Agents onNavigate={navigate} />;
      case 'agent-detail':
        return <AgentDetail agentId={selectedAgentId} onNavigate={navigate} />;
      case 'runs':
        return <Runs onNavigate={navigate} />;
      default:
        return <Dashboard onNavigate={navigate} />;
    }
  };

  return (
    <div className="app-layout">
      <Sidebar currentPage={page} onNavigate={navigate} />
      <main className="main-content">
        {renderPage()}
      </main>
    </div>
  );
}
