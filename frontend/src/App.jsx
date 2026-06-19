/**
 * App.jsx - Root application component with routing.
 */

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import Dashboard from './pages/Dashboard';
import WorkflowView from './pages/WorkflowView';
import LogExplorer from './pages/LogExplorer';
import IncidentPanel from './pages/IncidentPanel';
import Settings from './pages/Settings';
import useWebSocket from './hooks/useWebSocket';

function App() {
  // Establish WebSocket connection for real-time updates
  useWebSocket();

  return (
    <BrowserRouter>
      <div className="app-layout">
        <Sidebar />
        <div className="main-content">
          <Header />
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/workflow" element={<WorkflowView />} />
            <Route path="/logs" element={<LogExplorer />} />
            <Route path="/incidents" element={<IncidentPanel />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;
