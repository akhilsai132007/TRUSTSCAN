import { useState, useEffect } from 'react';
import OfficerDashboard from './components/OfficerDashboard';
import LoginScreen from './components/LoginScreen';
import { ShieldAlert, Loader2 } from 'lucide-react';

function App() {
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null);
  const [errorDetails, setErrorDetails] = useState<string>("");
  const [token, setToken] = useState<string | null>(localStorage.getItem('trustscan_token'));

  const handleLoginSuccess = (newToken: string) => {
    localStorage.setItem('trustscan_token', newToken);
    setToken(newToken);
  };

  const handleLogout = () => {
    localStorage.removeItem('trustscan_token');
    setToken(null);
  };

  useEffect(() => {
    const checkHealth = async () => {
      try {
        // Read the API URL from environment variables, fallback to localhost for dev
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        const response = await fetch(`${apiUrl}/api/v1/system/health`);
        
        if (response.ok) {
          setIsHealthy(true);
        } else {
          // It's a 503 or similar
          const errorData = await response.json();
          setErrorDetails(JSON.stringify(errorData.detail, null, 2));
          setIsHealthy(false);
        }
      } catch (error: any) {
        // Network error / connection refused
        setErrorDetails(error.message);
        setIsHealthy(false);
      }
    };

    checkHealth();
  }, []);

  if (isHealthy === null) {
    return (
      <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center text-slate-100 font-sans selection:bg-blue-200">
        <Loader2 size={48} className="animate-spin text-emerald-500 mb-6" />
        <h1 className="text-2xl font-bold tracking-widest text-slate-100 uppercase">INITIALIZING TRUSTSCAN SYSTEMS</h1>
        <p className="text-slate-500 font-mono text-sm mt-2 animate-pulse">Running diagnostic checks on AI Core...</p>
      </div>
    );
  }

  if (isHealthy === false) {
    return (
      <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center p-6 text-slate-100 font-sans">
        <div className="max-w-2xl w-full bg-rose-950/30 border border-rose-500/50 p-8 rounded-sm flex flex-col items-center text-center">
          <ShieldAlert size={64} className="text-rose-500 mb-6" />
          <h1 className="text-3xl font-bold tracking-tight text-rose-500 mb-2">SYSTEM CORE UNREACHABLE</h1>
          <p className="text-slate-300 mb-6">
            TRUSTSCAN cannot proceed because the backend AI services are offline or degraded. 
            Routing traffic to this node has been suspended.
          </p>
          
          <div className="w-full bg-black/50 p-4 rounded-sm border border-slate-800 text-left overflow-x-auto">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block mb-2">Diagnostic Output</span>
            <pre className="text-rose-400 font-mono text-xs">
              {errorDetails || "Error: Connection Refused"}
            </pre>
          </div>
          
          <button 
            onClick={() => window.location.reload()}
            className="mt-8 bg-slate-800 hover:bg-slate-700 text-slate-100 px-6 py-2.5 text-sm font-semibold shadow-sm transition-colors rounded-sm border border-slate-600 focus:outline-none"
          >
            RETRY CONNECTION
          </button>
        </div>
      </div>
    );
  }

  if (!token) {
    return <LoginScreen onLoginSuccess={handleLoginSuccess} />
  }

  return (
    <OfficerDashboard token={token} onLogout={handleLogout} />
  )
}

export default App
