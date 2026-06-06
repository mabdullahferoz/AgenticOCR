import React, { useState } from 'react';
import { Image as ImageIcon, FileText, ChevronRight } from 'lucide-react';

export default function DocumentViewer({ graphState }) {
  const manifest = graphState?.raw_graph_state?.final_execution_log?.raw_geometry_manifest || [];
  const [selectedFile, setSelectedFile] = useState(manifest.length > 0 ? manifest[0] : null);
  const [imgDimensions, setImgDimensions] = useState({ width: 0, height: 0 });
  const [zoomLevel, setZoomLevel] = useState(1);
  const [isDragging, setIsDragging] = useState(false);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const imgRef = React.useRef(null);

  // Update selected file automatically if new manifest arrives and we have no selection
  React.useEffect(() => {
    if (manifest.length > 0 && (!selectedFile || !manifest.find(m => m.file_name === selectedFile.file_name))) {
      setSelectedFile(manifest[0]);
    }
  }, [manifest]);

  const updateDimensions = () => {
    if (imgRef.current && imgRef.current.complete) {
      setImgDimensions({
        width: imgRef.current.naturalWidth,
        height: imgRef.current.naturalHeight
      });
    }
  };

  React.useEffect(() => {
    updateDimensions();
    
    // Robust dimension checking for cached images or delayed rendering
    const observer = new ResizeObserver(() => {
      updateDimensions();
    });
    
    if (imgRef.current) {
      observer.observe(imgRef.current);
    }
    
    return () => {
      observer.disconnect();
    };
  }, [selectedFile]);

  const handleImageLoad = (e) => {
    updateDimensions();
  };

  return (
    <div className="flex flex-col h-full space-y-4">
      <div className="flex items-center gap-2.5 text-zinc-500 dark:text-zinc-400">
        <ImageIcon className="w-5 h-5 text-indigo-500 dark:text-indigo-400" strokeWidth={1.5} />
        <span className="text-xs font-semibold tracking-[0.2em] uppercase text-zinc-800 dark:text-zinc-300">Document Spatial Viewer</span>
      </div>

      <div className="flex-grow flex flex-col sm:flex-row gap-4 min-h-0">
        {/* Left Sidebar: Document List */}
        <div className="w-full sm:w-1/3 md:w-1/4 bg-white/50 dark:bg-white/[0.02] border border-zinc-200 dark:border-white/5 rounded-2xl p-2 sm:p-3 flex flex-col gap-2 overflow-y-auto custom-scrollbar">
          <p className="text-[10px] uppercase font-bold text-zinc-400 tracking-wider px-2 pt-1 pb-2">Indexed Results</p>
          {manifest.length === 0 ? (
            <div className="text-xs text-zinc-500 dark:text-zinc-600 italic px-2">No documents found for this query.</div>
          ) : (
            manifest.map((item, idx) => (
              <button
                key={idx}
                onClick={() => setSelectedFile(item)}
                className={`flex items-center justify-between p-2.5 rounded-xl text-left transition-all ${
                  selectedFile?.file_name === item.file_name
                    ? 'bg-indigo-500/10 border border-indigo-500/20 text-indigo-600 dark:text-indigo-400 shadow-sm'
                    : 'hover:bg-zinc-100 dark:hover:bg-white/5 border border-transparent text-zinc-600 dark:text-zinc-400'
                }`}
              >
                <div className="flex items-center gap-2 truncate">
                  <FileText className="w-4 h-4 shrink-0" strokeWidth={1.5} />
                  <span className="text-xs font-medium truncate">
                    Book: {item.file_name} - Page {item.page}
                  </span>
                </div>
                {selectedFile?.file_name === item.file_name && <ChevronRight className="w-4 h-4 shrink-0 opacity-50" />}
              </button>
            ))
          )}
        </div>

        {/* Right Canvas: Image & Overlays */}
        <div className="w-full sm:w-2/3 md:w-3/4 flex-grow bg-zinc-100/50 dark:bg-black/40 border border-zinc-200 dark:border-white/5 rounded-2xl overflow-hidden relative shadow-inner flex flex-col">
          {!selectedFile ? (
            <div className="flex-grow flex flex-col items-center justify-center text-zinc-400 dark:text-zinc-600 space-y-3">
              <ImageIcon className="w-8 h-8 opacity-40 dark:opacity-20 mx-auto" strokeWidth={1} />
              <p className="italic text-xs font-medium">Select a document to view its layout</p>
            </div>
          ) : (
            <div className="flex flex-col h-full w-full">
              {/* Zoom Controls & Title Banner */}
              <div className="flex items-center justify-between bg-white/90 dark:bg-zinc-800 border-b border-zinc-200 dark:border-zinc-700 p-2 z-50 shrink-0 shadow-sm px-4">
                <div className="text-xs font-semibold text-zinc-700 dark:text-zinc-200 truncate pr-4">
                  Book: {selectedFile.file_name} <span className="opacity-40 mx-2">|</span> Page: {selectedFile.page}
                </div>
                <div className="flex items-center justify-center gap-4">
                  <button 
                    onClick={() => setZoomLevel(prev => Math.max(0.5, prev - 0.25))}
                    className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-700 text-zinc-600 dark:text-zinc-300 transition-colors font-bold"
                  >-</button>
                  <span className="text-xs font-medium w-12 text-center text-zinc-600 dark:text-zinc-300">{Math.round(zoomLevel * 100)}%</span>
                  <button 
                    onClick={() => setZoomLevel(prev => Math.min(4, prev + 0.25))}
                    className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-700 text-zinc-600 dark:text-zinc-300 transition-colors font-bold"
                  >+</button>
                  <button 
                    onClick={() => {
                      setZoomLevel(1);
                      setPosition({ x: 0, y: 0 });
                    }}
                    className="text-[10px] font-bold tracking-wider uppercase px-3 py-1.5 ml-2 hover:bg-indigo-50 dark:hover:bg-indigo-500/10 rounded-lg text-indigo-500 transition-colors"
                  >Reset View</button>
                </div>
              </div>

              {/* Draggable Canvas Area */}
              <div 
                className="flex-grow overflow-hidden relative cursor-grab active:cursor-grabbing flex items-center justify-center bg-white/20 dark:bg-black/20"
                onMouseDown={(e) => {
                  setIsDragging(true);
                  setDragStart({ x: e.clientX - position.x, y: e.clientY - position.y });
                }}
                onMouseMove={(e) => {
                  if (isDragging) {
                    setPosition({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
                  }
                }}
                onMouseUp={() => setIsDragging(false)}
                onMouseLeave={() => setIsDragging(false)}
              >
                <div 
                  className="relative inline-block leading-none origin-center"
                  style={{ 
                    transform: `translate(${position.x}px, ${position.y}px) scale(${zoomLevel})`,
                    transition: isDragging ? 'none' : 'transform 0.1s ease-out'
                  }}
                >
                  <img
                    ref={imgRef}
                    src={`http://127.0.0.1:8000/api/view-page/${selectedFile.file_name}/${selectedFile.page_file_name}`}
                    alt="Document Layout"
                    className="block rounded-lg shadow-lg pointer-events-none"
                    style={{ maxWidth: '100%', maxHeight: '70vh' }}
                    onLoad={handleImageLoad}
                    draggable="false"
                  />
                
                {/* Render Spatial Overlays dynamically if image dimensions are loaded */}
                {imgDimensions.width > 0 && imgDimensions.height > 0 && selectedFile.tblr_coordinates?.map((matchSegment, segmentIdx) => (
                  <React.Fragment key={segmentIdx}>
                    {matchSegment.map((box, boxIdx) => {
                      const topPct = (Number(box.top) / imgDimensions.height) * 100;
                      const leftPct = (Number(box.left) / imgDimensions.width) * 100;
                      const widthPct = ((Number(box.right) - Number(box.left)) / imgDimensions.width) * 100;
                      const heightPct = ((Number(box.bottom) - Number(box.top)) / imgDimensions.height) * 100;

                      return (
                        <div
                          key={`${segmentIdx}-${boxIdx}`}
                          style={{
                            position: 'absolute',
                            zIndex: 50,
                            top: `${topPct}%`,
                            left: `${leftPct}%`,
                            width: `${widthPct}%`,
                            height: `${heightPct}%`,
                            outline: `${Math.max(1, 3 / zoomLevel)}px solid #ef4444`,
                            background: 'none',
                            pointerEvents: 'none'
                          }}
                        />
                      );
                    })}
                  </React.Fragment>
                ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
