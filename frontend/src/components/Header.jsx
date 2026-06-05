import React, { useEffect, useState, useRef } from 'react';
import { agentApi } from '../services/api';
import { LayoutDashboard, BarChart2, CheckCircle2, Sun, Moon, Image as ImageIcon, UploadCloud, Loader2 } from 'lucide-react';

export default function Header({ activePanel, setActivePanel, theme, setTheme, isUploading, setIsUploading }) {
  const [metrics, setMetrics] = useState({ total_documents_indexed: 0, total_pages_cataloged: 0 });
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const fileInputRef = useRef(null);

  const refreshMetrics = () => {
    agentApi.getDatabaseAnalytics()
      .then(data => setMetrics(data))
      .catch(err => console.error("Error loading header stats:", err));
  };

  useEffect(() => {
    // Populate layout statistics instantly when the web dashboard mounts
    refreshMetrics();
  }, []);

  const handleDocumentUpload = async (e) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setIsUploading(true);
    setUploadSuccess(false);

    try {
      await agentApi.indexDocuments(files);
      setUploadSuccess(true);
      refreshMetrics(); // Refresh stats immediately after successful upload
      setTimeout(() => {
        setUploadSuccess(false);
      }, 3000); // revert to standard upload button after 3 seconds
    } catch (error) {
      console.error("Document upload failed", error);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <header className="glass-panel rounded-2xl md:rounded-3xl px-4 md:px-6 py-3 md:py-4 flex justify-between items-center w-full max-w-7xl mx-auto">
      <div className="flex items-center gap-3 md:gap-4">
        <div className="bg-indigo-500/10 p-2 md:p-2.5 rounded-xl md:rounded-2xl border border-indigo-500/20 shadow-inner shrink-0">
          <LayoutDashboard className="text-indigo-400 w-5 h-5 md:w-6 md:h-6" strokeWidth={1.5} />
        </div>
        <div className="min-w-0">
          <h1 className="text-sm md:text-base font-semibold tracking-wide text-zinc-800 dark:text-zinc-100 truncate">Document Intelligence</h1>
          <p className="hidden sm:block text-[10px] md:text-xs text-zinc-500 font-medium truncate">Multi-Agent Observability Dashboard</p>
        </div>
      </div>

      <div className="flex items-center gap-3 md:gap-6 shrink-0">
        {/* Dynamic Database Statistics Cards */}
        <div className="hidden lg:flex gap-3 text-xs font-medium">
          <div className="bg-zinc-100/80 dark:bg-white/[0.03] px-3 py-1.5 md:px-4 md:py-2 rounded-xl flex items-center gap-2 border border-zinc-200 dark:border-white/5">
            <CheckCircle2 className="text-emerald-500 dark:text-emerald-400 w-4 h-4" strokeWidth={2} />
            <span className="text-zinc-500 dark:text-zinc-400">Indexed: <strong className="text-zinc-700 dark:text-zinc-200 font-semibold">{metrics.total_documents_indexed}</strong></span>
          </div>
          <div className="bg-zinc-100/80 dark:bg-white/[0.03] px-3 py-1.5 md:px-4 md:py-2 rounded-xl flex items-center gap-2 border border-zinc-200 dark:border-white/5">
            <CheckCircle2 className="text-emerald-500 dark:text-emerald-400 w-4 h-4" strokeWidth={2} />
            <span className="text-zinc-500 dark:text-zinc-400">Pages: <strong className="text-zinc-700 dark:text-zinc-200 font-semibold">{metrics.total_pages_cataloged}</strong></span>
          </div>
        </div>

        {/* Document Indexing Upload */}
        <input 
          type="file" 
          multiple 
          ref={fileInputRef} 
          onChange={handleDocumentUpload} 
          accept="image/*" 
          className="hidden" 
        />
        <button
          onClick={() => fileInputRef.current.click()}
          disabled={isUploading}
          className={`glass-button p-2 md:p-2.5 rounded-xl transition-all ${
            isUploading ? 'text-indigo-400' : uploadSuccess ? 'text-emerald-500' : 'text-zinc-600 dark:text-zinc-300'
          }`}
          title="Index new documents"
        >
          {isUploading ? (
            <Loader2 className="w-4 h-4 md:w-5 md:h-5 animate-spin" strokeWidth={1.5} />
          ) : uploadSuccess ? (
            <CheckCircle2 className="w-4 h-4 md:w-5 md:h-5" strokeWidth={2} />
          ) : (
            <UploadCloud className="w-4 h-4 md:w-5 md:h-5" strokeWidth={1.5} />
          )}
        </button>

        {/* Theme Toggle Switch */}
        <button
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          className="glass-button p-2 md:p-2.5 rounded-xl text-zinc-600 dark:text-zinc-300"
          title="Toggle Theme"
        >
          {theme === 'dark' ? <Sun className="w-4 h-4 md:w-5 md:h-5" strokeWidth={1.5} /> : <Moon className="w-4 h-4 md:w-5 md:h-5" strokeWidth={1.5} />}
        </button>

        {/* View Images Toggle Switch */}
        <button
          onClick={() => setActivePanel(activePanel === 'viewer' ? 'none' : 'viewer')}
          className={`flex items-center justify-center gap-2 px-3 py-2 md:px-5 md:py-2.5 rounded-xl text-[11px] md:text-xs font-semibold transition-all duration-300 shadow-sm ${
            activePanel === 'viewer'
              ? 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20 hover:bg-indigo-500/20' 
              : 'glass-button text-zinc-600 dark:text-zinc-300'
          }`}
          title="Toggle Document Viewer"
        >
          <ImageIcon className="w-4 h-4" strokeWidth={2} />
          <span className="hidden sm:inline">View Images</span>
        </button>

        {/* Observability Toggle Switch */}
        <button
          onClick={() => setActivePanel(activePanel === 'telemetry' ? 'none' : 'telemetry')}
          className={`flex items-center justify-center gap-2 px-3 py-2 md:px-5 md:py-2.5 rounded-xl text-[11px] md:text-xs font-semibold transition-all duration-300 shadow-sm ${
            activePanel === 'telemetry' 
              ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20' 
              : 'glass-button text-zinc-600 dark:text-zinc-300'
          }`}
          title="Toggle Telemetry"
        >
          <BarChart2 className="w-4 h-4" strokeWidth={2} />
          <span className="hidden sm:inline">Telemetry</span>
        </button>
      </div>
    </header>
  );
}