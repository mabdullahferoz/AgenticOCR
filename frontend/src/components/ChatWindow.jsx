import React, { useState, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { agentApi } from '../services/api';
import { Send, Image as ImageIcon, Loader2, AlertCircle } from 'lucide-react';

export default function ChatWindow({ setGraphState }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [confirmationState, setConfirmationState] = useState({ active: false, word: null });
  const fileInputRef = useRef(null);

  const handleSubmit = async (textToSend, isConfirmationReply = false, confirmVal = null) => {
    const queryText = textToSend || input.trim();
    if (!queryText && !isConfirmationReply) return;

    // Always show the user's response in the chat, even if it's from a button click
    setMessages(prev => [...prev, { sender: 'YOU', text: queryText, isUser: true }]);
    if (!isConfirmationReply) {
      setInput('');
    }
    setLoading(true);

    try {
      // Execute REST pipeline call to FastAPI endpoint
      // We must pass the current confirmation state so the backend knows this is a reply to the fuzzy match
      const data = await agentApi.sendChatMessage(
        queryText, 
        confirmationState.active,
        confirmationState.active ? confirmationState.word : null
      );

      setMessages(prev => [...prev, { sender: 'DOCUMENT INTELLIGENCE AGENT', text: data.chatbot_response, isUser: false }]);
      setGraphState(data); // Push metrics sideways into telemetry container canvas

      // Evaluate if the Retrieval Agent has requested an active typo confirmation loop
      if (data.awaiting_confirmation) {
        setConfirmationState({ active: true, word: data.suggested_correction });
      } else {
        setConfirmationState({ active: false, word: null });
      }
    } catch (err) {
      setMessages(prev => [...prev, { sender: 'WORKFLOW ERROR', text: `Graph execution failed: ${err.message}`, isUser: false }]);
    } finally {
      setLoading(false);
    }
  };

  const handleImageUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Clear previous message state and text input buffer for a fresh vision run
    setInput('');
    setConfirmationState({ active: false, word: null });

    const imageBlobUrl = URL.createObjectURL(file);

    setMessages(prev => [...prev, { 
      sender: 'YOU', 
      text: `*Uploaded query snippet image:*`, 
      isUser: true,
      imageBlobUrl: imageBlobUrl
    }]);
    setLoading(true);

    try {
      const data = await agentApi.uploadQueryImage(file);
      setMessages(prev => [...prev, { sender: 'DOCUMENT INTELLIGENCE AGENT', text: data.chatbot_response, isUser: false }]);
      setGraphState(data);

      // Evaluate if the Retrieval Agent has requested an active typo confirmation loop from the image extraction
      if (data.awaiting_confirmation) {
        setConfirmationState({ active: true, word: data.suggested_correction });
      } else {
        setConfirmationState({ active: false, word: null });
      }
    } catch (err) {
      setMessages(prev => [...prev, { sender: 'VISION ERROR', text: `Vision processing failed: ${err.message}`, isUser: false }]);
    } finally {
      setLoading(false);
      // Reset input value so the same file can be uploaded again if needed
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <div className="flex flex-col h-full justify-between space-y-4">
      {/* Scrollable Chat Area */}
      <div className="flex-grow rounded-2xl p-4 overflow-y-auto space-y-6 min-h-0 scroll-smooth">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.isUser ? 'justify-end' : 'justify-start'} animate-slide-up`} style={{ animationDelay: `${i * 0.05}s` }}>
            <div className={`rounded-2xl p-5 max-w-[85%] sm:max-w-[75%] shadow-md backdrop-blur-md ${
              msg.isUser 
                ? 'bg-indigo-500/90 text-white rounded-br-sm' 
                : 'bg-zinc-100/90 dark:bg-white/5 text-zinc-800 dark:text-zinc-200 border border-zinc-200 dark:border-white/10 rounded-bl-sm'
            }`}>
              <span className={`block text-[10px] font-bold tracking-wider mb-2 uppercase ${msg.isUser ? 'text-indigo-200' : 'text-zinc-500 dark:text-zinc-500'}`}>{msg.sender}</span>
              <div className="prose prose-sm dark:prose-invert max-w-none leading-relaxed">
                {msg.imageBlobUrl && (
                  <img src={msg.imageBlobUrl} alt="Uploaded snippet" className="max-w-[200px] sm:max-w-[300px] w-full rounded-xl mb-3 shadow-sm border border-white/20" />
                )}
                <ReactMarkdown>{msg.text}</ReactMarkdown>
              </div>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex items-center gap-3 text-sm text-indigo-400 font-medium animate-pulse ml-2">
            <Loader2 className="animate-spin w-4 h-4" />
            <span>Agent network computing...</span>
          </div>
        )}
      </div>

      {/* Dynamic Multi-Turn Typo Auto-Correction Widget Option Panel Overlay */}
      {confirmationState.active && (
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-2xl p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 animate-fade-in shadow-lg">
          <div className="flex items-center gap-3 text-sm text-amber-400 font-medium">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span>Fuzzy lookup loop active. Confirm suggestion token <strong className="text-amber-300 bg-amber-500/20 px-2 py-0.5 rounded-md mx-1">{confirmationState.word}</strong>?</span>
          </div>
          <div className="flex gap-3">
            <button onClick={() => handleSubmit('Yes', true)} className="bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 border border-emerald-500/30 px-6 py-2 text-sm font-semibold rounded-xl transition-all">Yes</button>
            <button onClick={() => handleSubmit('No', true)} className="bg-rose-500/20 hover:bg-rose-500/30 text-rose-400 border border-rose-500/30 px-6 py-2 text-sm font-semibold rounded-xl transition-all">No</button>
          </div>
        </div>
      )}

      {/* Input Action Dock Toolbar */}
      <div className="flex items-center gap-3 pt-2 relative">
        <input type="file" ref={fileInputRef} onChange={handleImageUpload} accept="image/*" className="hidden" />
        <button onClick={() => fileInputRef.current.click()} disabled={loading} className="p-3.5 glass-button rounded-xl disabled:opacity-50 group flex-shrink-0" title="Upload Image">
          <ImageIcon className="w-5 h-5 text-zinc-400 group-hover:text-zinc-200 transition-colors" strokeWidth={1.5} />
        </button>
        <div className="relative flex-grow">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
            disabled={loading || confirmationState.active}
            placeholder={confirmationState.active ? "Please use correction buttons above..." : "Ask the intelligence agent..."}
            className="w-full bg-white dark:bg-white/5 border border-zinc-200 dark:border-white/10 text-zinc-800 dark:text-zinc-200 rounded-2xl pl-5 pr-14 py-4 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-transparent disabled:opacity-40 transition-all placeholder-zinc-400 dark:placeholder-zinc-500 shadow-inner"
          />
          <button 
            onClick={() => handleSubmit()} 
            disabled={loading || confirmationState.active || !input.trim()} 
            className="absolute right-2 top-1/2 -translate-y-1/2 p-2.5 bg-indigo-500 hover:bg-indigo-600 text-white rounded-xl disabled:opacity-50 disabled:hover:bg-indigo-500 transition-all shadow-md"
          >
            <Send className="w-4 h-4" strokeWidth={2} />
          </button>
        </div>
      </div>
    </div>
  );
}