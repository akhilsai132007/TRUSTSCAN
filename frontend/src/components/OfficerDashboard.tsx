import { useState, useRef, useEffect } from 'react';
import { 
  ShieldAlert, ShieldCheck, AlertTriangle, CheckCircle, 
  XCircle, ChevronDown, ChevronUp, Focus, ScanFace,
  Loader2, Play, Upload, LogOut, History, User, Bot
} from 'lucide-react';

interface OfficerDashboardProps {
  token: string;
  onLogout: () => void;
}

export default function OfficerDashboard({ token, onLogout }: OfficerDashboardProps) {
  const [isExplanationOpen, setIsExplanationOpen] = useState(true);
  const [isAuditOpen, setIsAuditOpen] = useState(false);
  const [auditEvents, setAuditEvents] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [activeSvg, setActiveSvg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isActionLoading, setIsActionLoading] = useState(false);

  // --- Initial Empty State ---
  const [sessionData, setSessionData] = useState<any | null>(null);

  const loadDemoCase = async (caseType: string) => {
    setIsLoading(true);
    setActiveSvg(`/demo-samples/${caseType}.svg`);
    
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/scan/demo`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ case_type: caseType })
      });
      
      if (response.status === 401 || response.status === 403) {
        alert("Session expired or unauthorized.");
        onLogout();
        return;
      }
      
      const data = await response.json();
      formatAndSetData(data, `Loaded ${caseType.toUpperCase()} demo.`);
    } catch (error) {
      console.error("Failed to load demo case:", error);
      alert("Failed to reach backend API. Is it running?");
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsLoading(true);
    setActiveSvg(URL.createObjectURL(file));

    const formData = new FormData();
    formData.append("document_image", file);

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/scan/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData, // fetch automatically sets the correct multipart boundary
      });

      if (response.status === 401 || response.status === 403) {
        alert("Session expired or unauthorized.");
        onLogout();
        return;
      }

      if (!response.ok) {
         const errorData = await response.json();
         throw new Error(errorData.detail || "Upload failed");
      }

      const data = await response.json();
      formatAndSetData(data, `Uploaded ${file.name}`);
    } catch (error: any) {
      console.error("Upload Error:", error);
      alert(`Error processing document: ${error.message}`);
      setActiveSvg(null);
      setSessionData(null);
    } finally {
      setIsLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const formatAndSetData = (data: any, actionNotes: string) => {
    const formattedData = {
      id: data.session_id,
      timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19) + ' UTC',
      document_type: "PASSPORT (ICAO TD3)",
      risk_level: data.risk_decision.risk_level,
      risk_explanation: data.risk_decision.explanation,
      extracted: {
        "MRZ Validity": { vz: "N/A", mrz: data.pipeline_data.mrz_valid ? "VALID" : "INVALID", match: data.pipeline_data.mrz_valid },
        "Face Match": { vz: "Live Face", mrz: `${(data.pipeline_data.face_match_score * 100).toFixed(0)}%`, match: data.pipeline_data.face_match_score > 0.75 },
        "Tamper Confidence": { vz: "Image", mrz: `${(data.pipeline_data.tamper_score * 100).toFixed(0)}%`, match: data.pipeline_data.tamper_score < 0.40 },
      },
      human_verification_status: "PENDING_REVIEW",
      audit_trail: [
        { time: new Date().toLocaleTimeString(), actor: "System", action: "Session Initiated", notes: actionNotes },
        { time: new Date().toLocaleTimeString(), actor: "AI Core", action: "Pipeline Executed", notes: `Risk assigned: ${data.risk_decision.risk_level}` }
      ]
    };
    setSessionData(formattedData);
  };

  const handleDecision = async (decision: string) => {
    if (!sessionData) return;
    setIsActionLoading(true);
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const endpointMap: Record<string, string> = {
        'APPROVE': 'approve',
        'ESCALATE': 'escalate',
        'REJECT': 'reject'
      };
      
      const response = await fetch(`${apiUrl}/api/v1/verification/${sessionData.id}/${endpointMap[decision]}`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
      });
      
      if (response.status === 401 || response.status === 403) {
        alert("Session expired or unauthorized. Only authorized officers can perform this action.");
        if (response.status === 401) onLogout();
        return;
      }
      
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || `Failed to ${decision.toLowerCase()} scan.`);
      }
      
      const updatedData = await response.json();
      setSessionData((prev: any) => prev ? { ...prev, ...updatedData } : null);
      setIsActionLoading(false);
      fetchAuditHistory(sessionData.id); // Refresh audit log
    } catch (error: any) {
      alert(error.message);
      setIsActionLoading(false);
    } finally {
      setIsActionLoading(false);
    }
  };

  const fetchAuditHistory = async (scanId: string) => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/scans/${scanId}/audit`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setAuditEvents(data.events || []);
      }
    } catch (e) {
      console.error("Failed to fetch audit history", e);
    }
  };

  useEffect(() => {
    if (sessionData && isAuditOpen) {
      fetchAuditHistory(sessionData.id);
    }
  }, [sessionData?.id, isAuditOpen]);

  const getSystemOrOfficerIcon = (eventType: string) => {
    if (eventType.startsWith('AUTH_') || eventType.startsWith('SCAN_APPROV') || eventType.startsWith('SCAN_REJECT') || eventType.startsWith('SCAN_ESCALAT')) {
      return <User size={14} className="text-blue-500" />;
    }
    return <Bot size={14} className="text-slate-500" />;
  };


  return (
    <div className="min-h-screen bg-slate-100 text-slate-900 font-sans p-6 flex flex-col gap-6 selection:bg-blue-200">
      
      {/* --- HEADER & ACTION ROW --- */}
      <header className="flex justify-between items-center bg-white border border-slate-300 p-4 shadow-sm rounded-sm">
        <div className="flex items-center gap-4">
          <div className="bg-slate-800 p-2 text-white rounded-sm">
            <ScanFace size={24} />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-800 leading-none">TRUSTSCAN</h1>
            <div className="flex items-center gap-2 mt-1">
               <p className="text-xs text-slate-500 font-mono">
                 {sessionData ? `ID: ${sessionData.id} | ${sessionData.timestamp}` : "AWAITING SCAN..."}
               </p>
               <span className="text-[10px] font-bold text-emerald-600 bg-emerald-100 px-1.5 py-0.5 rounded-sm uppercase tracking-widest border border-emerald-200">
                 AUTHORIZED
               </span>
               <button onClick={onLogout} className="text-[10px] text-slate-400 hover:text-rose-500 ml-2" title="Logout">
                 <LogOut size={12} />
               </button>
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-6">
          {/* REAL FILE UPLOAD */}
          <div className="flex items-center gap-2 bg-slate-100 p-1 border border-slate-300 rounded-sm mr-2">
             <input 
                type="file" 
                ref={fileInputRef} 
                className="hidden" 
                accept="image/jpeg, image/png, application/pdf"
                onChange={handleFileUpload}
             />
             <button 
                onClick={() => fileInputRef.current?.click()}
                className="flex items-center text-xs font-bold text-slate-700 uppercase px-3 py-1.5 hover:bg-slate-200 transition-colors"
             >
                <Upload size={14} className="inline mr-2" /> Upload Document
             </button>
          </div>

          {/* DEMO DROPDOWN */}
          <div className="flex items-center gap-2 bg-slate-100 p-1 border border-slate-300 rounded-sm">
            <span className="text-xs font-bold text-slate-500 uppercase px-2"><Play size={12} className="inline mr-1"/> Run Demo:</span>
            <select 
              className="bg-white border border-slate-300 text-sm py-1 px-2 text-slate-700 outline-none cursor-pointer focus:ring-1 focus:ring-slate-500"
              onChange={(e) => {
                if(e.target.value) loadDemoCase(e.target.value);
                e.target.value = "";
              }}
              defaultValue=""
            >
              <option value="" disabled>Select a case...</option>
              <option value="clean">🟢 Clean (Low Risk)</option>
              <option value="borderline">🟡 Borderline (Medium Risk)</option>
              <option value="tampered">🔴 Tampered (High Risk)</option>
            </select>
          </div>

          <div className="w-px h-8 bg-slate-300"></div>

          {sessionData && sessionData.human_verification_status !== "PENDING_REVIEW" ? (
             <div className="px-4 py-2 font-bold text-sm bg-slate-800 text-white rounded-sm">
               STATUS: {sessionData.human_verification_status}
             </div>
          ) : (
            <>
              <button disabled={!sessionData || isActionLoading} onClick={() => handleDecision('APPROVE')} className="flex items-center gap-2 bg-emerald-700 hover:bg-emerald-800 disabled:bg-slate-300 disabled:cursor-not-allowed text-white px-6 py-2.5 text-sm font-semibold shadow-sm transition-colors rounded-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-1">
                {isActionLoading ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle size={16} />} APPROVE
              </button>
              <button disabled={!sessionData || isActionLoading} onClick={() => handleDecision('ESCALATE')} className="flex items-center gap-2 bg-amber-600 hover:bg-amber-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white px-6 py-2.5 text-sm font-semibold shadow-sm transition-colors rounded-sm focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-1">
                {isActionLoading ? <Loader2 size={16} className="animate-spin" /> : <AlertTriangle size={16} />} ESCALATE
              </button>
              <button disabled={!sessionData || isActionLoading} onClick={() => handleDecision('REJECT')} className="flex items-center gap-2 bg-rose-700 hover:bg-rose-800 disabled:bg-slate-300 disabled:cursor-not-allowed text-white px-6 py-2.5 text-sm font-semibold shadow-sm transition-colors rounded-sm focus:outline-none focus:ring-2 focus:ring-rose-500 focus:ring-offset-1">
                {isActionLoading ? <Loader2 size={16} className="animate-spin" /> : <XCircle size={16} />} REJECT
              </button>
            </>
          )}
        </div>
      </header>

      {/* --- MAIN SPLIT VIEW --- */}
      {isLoading ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="flex flex-col items-center gap-4 text-slate-500">
            <Loader2 size={48} className="animate-spin text-slate-400" />
            <p className="font-mono text-sm tracking-widest animate-pulse">EXECUTING AI PIPELINE...</p>
          </div>
        </div>
      ) : !sessionData ? (
        <div className="flex-1 flex items-center justify-center border-2 border-dashed border-slate-300 bg-slate-50 rounded-sm">
           <p className="font-mono text-slate-400">PLEASE INITIATE A SCAN OR LOAD A DEMO CASE.</p>
        </div>
      ) : (
        <div className="flex flex-col lg:flex-row gap-6 flex-1">
          
          {/* LEFT PANEL: Document Image View */}
          <div className="flex-1 flex flex-col gap-4">
            <div className="bg-white border border-slate-300 shadow-sm rounded-sm flex-1 flex flex-col">
              <div className="bg-slate-100 border-b border-slate-300 p-3 flex justify-between items-center">
                <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">Document Scan</h2>
                <Focus size={16} className="text-slate-500" />
              </div>
              
              <div className="flex-1 p-6 flex items-center justify-center bg-slate-50 relative overflow-hidden">
                {activeSvg ? (
                  <img src={activeSvg} alt="Document Scan" className="w-full max-w-lg shadow-md border border-slate-300" />
                ) : (
                  <div className="relative w-full max-w-lg aspect-[1.42/1] bg-slate-200 border border-slate-400 shadow-md flex flex-col items-center justify-center text-slate-400">
                    <span className="font-mono text-sm">[ DOCUMENT IMAGE RENDER ]</span>
                  </div>
                )}
              </div>
              
              <div className="bg-slate-800 text-slate-300 text-xs font-mono p-3 flex justify-between border-t border-slate-700 rounded-b-sm">
                <span>RESOLUTION: 1920x1080</span>
                <span>DPI: 300</span>
                <span>ENCRYPTION: SHA-256</span>
              </div>
            </div>
          </div>

          {/* RIGHT PANEL: Data & Analysis */}
          <div className="flex-1 flex flex-col gap-6">
            
            <div className="bg-slate-800 text-white p-3 rounded-sm border border-slate-700 flex justify-between items-center text-sm font-semibold">
               <span>The AI provides screening evidence. Final action requires authorized human review.</span>
            </div>

            {/* Risk Badge & Explanation */}
            <div className={`border rounded-sm shadow-sm ${sessionData.risk_level === 'HIGH' ? 'bg-rose-50 border-rose-200' : sessionData.risk_level === 'MEDIUM' ? 'bg-amber-50 border-amber-200' : 'bg-emerald-50 border-emerald-200'}`}>
              <div 
                className="p-4 flex justify-between items-center cursor-pointer"
                onClick={() => setIsExplanationOpen(!isExplanationOpen)}
              >
                <div className="flex items-center gap-3">
                  {sessionData.risk_level === 'HIGH' ? (
                    <ShieldAlert className="text-rose-600" size={28} />
                  ) : sessionData.risk_level === 'MEDIUM' ? (
                    <AlertTriangle className="text-amber-600" size={28} />
                  ) : (
                    <ShieldCheck className="text-emerald-600" size={28} />
                  )}
                  <div>
                    <h2 className={`text-lg font-bold ${sessionData.risk_level === 'HIGH' ? 'text-rose-700' : sessionData.risk_level === 'MEDIUM' ? 'text-amber-700' : 'text-emerald-700'}`}>
                      {sessionData.risk_level} RISK DETECTED
                    </h2>
                    <p className="text-sm text-slate-600">AI Fusion Engine Assessment</p>
                  </div>
                </div>
                {isExplanationOpen ? <ChevronUp className="text-slate-500" /> : <ChevronDown className="text-slate-500" />}
              </div>
              
              {isExplanationOpen && (
                <div className="px-4 pb-4 pt-2 border-t border-slate-200/50">
                  <div className={`bg-white p-3 border rounded-sm ${sessionData.risk_level === 'HIGH' ? 'border-rose-200' : sessionData.risk_level === 'MEDIUM' ? 'border-amber-200' : 'border-emerald-200'}`}>
                    <p className="text-sm text-slate-800 font-mono leading-relaxed">
                      {sessionData.risk_explanation}
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Structured Data Comparison */}
            <div className="bg-white border border-slate-300 shadow-sm rounded-sm flex-1 flex flex-col">
              <div className="bg-slate-100 border-b border-slate-300 p-3">
                <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">AI Confidence Metrics</h2>
              </div>
              <div className="p-0 overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="bg-slate-50 border-b border-slate-200 text-xs uppercase text-slate-500">
                    <tr>
                      <th className="px-4 py-3 font-semibold">Field</th>
                      <th className="px-4 py-3 font-semibold">Visual Zone (OCR)</th>
                      <th className="px-4 py-3 font-semibold">MRZ Parsed</th>
                      <th className="px-4 py-3 font-semibold text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono">
                    {Object.entries(sessionData.extracted).map(([key, data]: [string, any]) => (
                      <tr key={key} className={!data.match ? 'bg-rose-50/50' : 'hover:bg-slate-50'}>
                        <td className="px-4 py-3 font-medium text-slate-700 font-sans">{key}</td>
                        <td className="px-4 py-3 text-slate-600">{data.vz}</td>
                        <td className="px-4 py-3 text-slate-600">{data.mrz}</td>
                        <td className="px-4 py-3 text-center">
                          {data.match ? (
                            <span className="inline-block px-2 py-1 bg-emerald-100 text-emerald-800 text-[10px] font-bold rounded-sm border border-emerald-200">PASS</span>
                          ) : (
                            <span className="inline-block px-2 py-1 bg-rose-100 text-rose-800 text-[10px] font-bold rounded-sm border border-rose-200">FAIL</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Audit Trail Panel */}
            <div className="bg-white border border-slate-300 shadow-sm rounded-sm h-64 flex flex-col mt-6 mb-8">
              <div 
                className="px-4 py-3 bg-slate-800/80 border-b border-slate-700 flex justify-between items-center cursor-pointer hover:bg-slate-700/50 transition-colors"
                onClick={() => setIsAuditOpen(!isAuditOpen)}
              >
                <div className="flex items-center gap-2">
                  <History className="text-slate-400" size={18} />
                  <h3 className="font-semibold text-slate-200">Verification History</h3>
                </div>
                <div className="flex items-center gap-4">
                  <button 
                    onClick={(e) => { e.stopPropagation(); fetchAuditHistory(sessionData.id); }} 
                    className="text-[10px] text-slate-300 hover:text-white uppercase tracking-wider border border-slate-500 px-2 py-0.5 rounded-sm bg-slate-700/50"
                  >
                    Refresh
                  </button>
                  <button className="text-slate-400 hover:text-slate-200 focus:outline-none">
                    {isAuditOpen ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                  </button>
                </div>
              </div>
              {isAuditOpen && (
                <div className="p-0 overflow-y-auto flex-1 font-mono text-xs">
                {auditEvents.length === 0 ? (
                  <div className="p-4 text-slate-400 text-center flex flex-col items-center justify-center h-full">
                    <Loader2 size={24} className="animate-spin mb-2 opacity-50" />
                    Fetching secure audit logs...
                  </div>
                ) : (
                  <table className="w-full text-left">
                    <thead className="bg-slate-50 sticky top-0 border-b border-slate-200 shadow-sm">
                      <tr>
                        <th className="px-3 py-2 text-[10px] uppercase text-slate-500 font-bold">Time (UTC)</th>
                        <th className="px-3 py-2 text-[10px] uppercase text-slate-500 font-bold">Event</th>
                        <th className="px-3 py-2 text-[10px] uppercase text-slate-500 font-bold">Actor</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {auditEvents.map((event, idx) => (
                        <tr key={idx} className="hover:bg-slate-50">
                          <td className="px-3 py-2 text-slate-400 shrink-0 align-top">
                            {new Date(event.timestamp).toISOString().replace('T', ' ').substring(0, 19)}
                          </td>
                          <td className="px-3 py-2 align-top">
                            <div className="font-bold text-slate-700 flex items-center gap-1.5">
                              {getSystemOrOfficerIcon(event.event_type)}
                              {event.event_type}
                            </div>
                            {event.metadata && Object.keys(event.metadata).length > 0 && (
                              <div className="mt-1 text-[10px] text-slate-500">
                                {Object.entries(event.metadata).map(([k, v]) => (
                                  <div key={k}><span className="text-slate-400">{k}:</span> {String(v)}</div>
                                ))}
                              </div>
                            )}
                          </td>
                          <td className="px-3 py-2 align-top">
                            {event.actor ? (
                              <span className="inline-block px-1.5 py-0.5 bg-blue-50 text-blue-700 border border-blue-200 rounded-sm">
                                {event.actor.substring(0, 8)}...
                              </span>
                            ) : (
                              <span className="inline-block px-1.5 py-0.5 bg-slate-100 text-slate-500 border border-slate-200 rounded-sm">
                                SYSTEM
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
             )}
            </div>

          </div>
        </div>
      )}
    </div>
  );
}
