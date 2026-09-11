import { useState } from 'react';
import { ScanFace, Loader2, ShieldAlert } from 'lucide-react';

interface LoginScreenProps {
  onLoginSuccess: (token: string) => void;
}

export default function LoginScreen({ onLoginSuccess }: LoginScreenProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);
      
      const response = await fetch(`${apiUrl}/api/v1/login/access-token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: formData.toString()
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Login failed');
      }
      
      const data = await response.json();
      onLoginSuccess(data.access_token);
    } catch (err: any) {
      setError(err.message || 'Unable to connect to server.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center p-6 text-slate-100 font-sans selection:bg-blue-200">
      <div className="max-w-md w-full bg-slate-800 border border-slate-700 shadow-xl rounded-sm overflow-hidden">
        
        <div className="bg-slate-950 p-6 flex flex-col items-center border-b border-slate-800">
          <div className="bg-slate-800 p-3 text-emerald-500 rounded-sm mb-4 shadow-sm border border-slate-700">
            <ScanFace size={32} />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white leading-none">TRUSTSCAN</h1>
          <p className="text-xs text-slate-400 font-mono mt-2 tracking-widest uppercase">Identity Verification Core</p>
        </div>
        
        <div className="p-8">
          <h2 className="text-lg font-semibold text-slate-200 mb-6 uppercase tracking-wider">Officer Login</h2>
          
          {error && (
            <div className="bg-rose-950/50 border border-rose-500/50 p-3 rounded-sm mb-6 flex items-start gap-3">
              <ShieldAlert className="text-rose-500 shrink-0 mt-0.5" size={16} />
              <p className="text-rose-200 text-sm">{error}</p>
            </div>
          )}
          
          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            <div>
              <label className="block text-xs font-bold text-slate-400 uppercase mb-2">Username or ID</label>
              <input 
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-sm px-4 py-2.5 text-slate-200 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors"
                required
                autoComplete="username"
              />
            </div>
            
            <div>
              <label className="block text-xs font-bold text-slate-400 uppercase mb-2">Secure Password</label>
              <input 
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-sm px-4 py-2.5 text-slate-200 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors"
                required
                autoComplete="current-password"
              />
            </div>
            
            <button 
              type="submit"
              disabled={isLoading || !username || !password}
              className="mt-2 flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 disabled:text-slate-500 disabled:cursor-not-allowed text-white px-6 py-3 text-sm font-bold tracking-wider uppercase shadow-sm transition-colors rounded-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 focus:ring-offset-slate-900"
            >
              {isLoading ? <Loader2 size={18} className="animate-spin" /> : null}
              {isLoading ? 'Authenticating...' : 'Authenticate'}
            </button>
          </form>
        </div>
        
        <div className="bg-slate-900/50 p-4 border-t border-slate-800 text-center">
          <p className="text-xs text-slate-500 font-mono">UNAUTHORIZED ACCESS STRICTLY PROHIBITED</p>
        </div>
        
      </div>
    </div>
  );
}
