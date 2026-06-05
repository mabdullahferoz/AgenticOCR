import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import ChatWindow from './components/ChatWindow';
import TelemetryPanel from './components/TelemetryPanel';
import DocumentViewer from './components/DocumentViewer';

export default function App() {
  // Master layout panel visibility state toggle ('none', 'telemetry', 'viewer')
  const [activePanel, setActivePanel] = useState('none');
  
  // Real-time backend blackboard memory state feed
  const [graphState, setGraphState] = useState(null);

  // Theme Management
  const [theme, setTheme] = useState('dark');
  
  // Document Upload State
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [theme]);

  return (
    <div className="h-screen bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-zinc-100 via-zinc-200 to-zinc-300 dark:from-zinc-900 dark:via-zinc-950 dark:to-black text-zinc-900 dark:text-zinc-300 flex flex-col p-3 md:p-6 overflow-hidden font-sans transition-colors duration-500">
      {/* 1. Global Header Analytics Bar Layout */}
      <Header 
        activePanel={activePanel} 
        setActivePanel={setActivePanel} 
        theme={theme}
        setTheme={setTheme}
        isUploading={isUploading}
        setIsUploading={setIsUploading}
      />
      
      {/* 2. Responsive Split-Pane Panel Architecture Matrix */}
      <div className="flex-grow flex flex-col lg:flex-row gap-4 md:gap-6 mt-4 md:mt-6 overflow-hidden min-h-0 relative">
        
        {/* Left Workspace Panel: Automatically recalculates widths on state modification */}
        <div className={`glass-panel rounded-2xl md:rounded-3xl p-4 md:p-6 flex flex-col transition-all duration-500 ease-in-out min-h-0 ${
          activePanel !== 'none' ? 'h-1/2 lg:h-full lg:w-1/2 w-full' : 'h-full w-full max-w-5xl mx-auto'
        }`}>
          <ChatWindow setGraphState={setGraphState} isUploading={isUploading} />
        </div>

        {/* Right Panel Workspace: Mounts and slides smoothly into view */}
        {activePanel === 'telemetry' && (
          <div className="h-1/2 lg:h-full lg:w-1/2 w-full glass-panel rounded-2xl md:rounded-3xl p-4 md:p-6 flex flex-col animate-slide-up min-h-0">
            <TelemetryPanel graphState={graphState} />
          </div>
        )}
        
        {activePanel === 'viewer' && (
          <div className="h-1/2 lg:h-full lg:w-1/2 w-full glass-panel rounded-2xl md:rounded-3xl p-4 md:p-6 flex flex-col animate-slide-up min-h-0">
            <DocumentViewer graphState={graphState} />
          </div>
        )}
        
      </div>
    </div>
  );
}