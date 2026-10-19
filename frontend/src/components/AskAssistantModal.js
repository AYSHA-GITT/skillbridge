import React, { useState, useRef, useEffect, useCallback } from 'react';
import skillService from '../services/skillService';
import {
  startSpeechRecognition,
  speakText,
  stopSpeaking,
  isSpeechRecognitionSupported,
  isSpeechSynthesisSupported
} from '../utils/voiceUtils';
import {
  TbSparkles,
  TbX,
  TbMinus,
  TbSend,
  TbBulb,
  TbShieldCheck,
  TbTrash,
  TbMicrophone,
  TbMicrophoneOff,
  TbVolume,
  TbVolumeOff,
  TbCpu,
  TbChevronDown
} from 'react-icons/tb';


const QUICK_PROMPTS = [
  'What should I learn next?',
  'Why was my top career recommended?',
  'What is my biggest skill gap?',
  'How can I improve my salary?'
];

function formatAssistantMessage(text) {
  if (!text) return null;
  const paragraphs = text.split('\n');
  return paragraphs.map((para, pIdx) => {
    if (!para.trim()) return <div key={pIdx} className="h-2" />;

    // Highlight source citations [Source X: Title]
    const citationParts = para.split(/(\[Source\s*\d+[^\]]*\])/gi);
    return (
      <p key={pIdx} className="mb-1.5 last:mb-0 leading-relaxed">
        {citationParts.map((cPart, cIdx) => {
          if (cPart.match(/^\[Source\s*\d+[^\]]*\]$/i)) {
            return (
              <span
                key={cIdx}
                className="inline-flex items-center text-[10px] font-mono px-1.5 py-0.5 rounded bg-accent-500/20 text-accent-300 border border-accent-400/30 mx-1 align-baseline cursor-pointer hover:bg-accent-500/30"
                title="RAG Verified Document Reference"
              >
                {cPart}
              </span>
            );
          }

          // Markdown bold styling
          const parts = cPart.split(/(\*\*[^*]+\*\*)/g);
          return parts.map((part, partIdx) => {
            if (part.startsWith('**') && part.endsWith('**')) {
              return (
                <strong key={partIdx} className="font-semibold text-accent-300">
                  {part.slice(2, -2)}
                </strong>
              );
            }
            return <span key={partIdx}>{part}</span>;
          });
        })}
      </p>
    );
  });
}

export default function AskAssistantModal({ isOpen, onClose, onOpen }) {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversation, setConversation] = useState([]);
  const [error, setError] = useState('');
  const [showPrompts, setShowPrompts] = useState(true);
  const messagesEndRef = useRef(null);

  // Provider state
  const [providers, setProviders] = useState([]);
  const [selectedProvider, setSelectedProvider] = useState('auto');
  const [showProviderMenu, setShowProviderMenu] = useState(false);

  // Voice Interaction state
  const [isRecording, setIsRecording] = useState(false);
  const [speakingMsgIdx, setSpeakingMsgIdx] = useState(null);
  const recognitionRef = useRef(null);

  const fetchProviders = useCallback(async () => {
    try {
      const res = await skillService.getAIProviders();
      setProviders(res.providers || []);
    } catch {
      // Non-blocking fallback
    }
  }, []);

  useEffect(() => {
    fetchProviders();
  }, [fetchProviders]);

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
    return () => {
      stopSpeaking();
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, [conversation, loading, isOpen]);

  const handleAsk = async (queryToAsk) => {
    const q = (queryToAsk || question).trim();
    if (!q) return;

    stopSpeaking();
    setSpeakingMsgIdx(null);
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      setIsRecording(false);
    }

    setLoading(true);
    setError('');

    const newConvo = [...conversation, { sender: 'user', text: q }];
    setConversation(newConvo);
    setQuestion('');
    setShowPrompts(false);

    try {
      const providerParam = selectedProvider === 'auto' ? null : selectedProvider;
      const res = await skillService.askAssistant(q, providerParam);
      setConversation([
        ...newConvo,
        {
          sender: 'assistant',
          text: res.answer,
          source: res.source,
          groundedOn: res.grounded_on,
          sourcesRetrieved: res.sources_retrieved || []
        }
      ]);
    } catch {
      setError('Could not reach the assistant. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    stopSpeaking();
    setSpeakingMsgIdx(null);
    setConversation([]);
    setError('');
    setShowPrompts(true);
  };

  // STT Dictate Query
  const handleToggleRecord = () => {
    if (!isSpeechRecognitionSupported()) {
      setError('Speech recognition not supported in this browser.');
      return;
    }

    if (isRecording) {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      setIsRecording(false);
    } else {
      setIsRecording(true);
      setError('');
      recognitionRef.current = startSpeechRecognition(
        (transcript) => {
          setQuestion((prev) => {
            const trimmed = prev.trim();
            return trimmed ? `${trimmed} ${transcript}` : transcript;
          });
        },
        (err) => {
          setError(err);
          setIsRecording(false);
        },
        () => {
          setIsRecording(false);
        }
      );
    }
  };

  // TTS Read Message
  const handleToggleSpeakMessage = (text, idx) => {
    if (speakingMsgIdx === idx) {
      stopSpeaking();
      setSpeakingMsgIdx(null);
    } else {
      setSpeakingMsgIdx(idx);
      speakText(
        text,
        () => setSpeakingMsgIdx(idx),
        () => setSpeakingMsgIdx(null)
      );
    }
  };

  // Sleek floating launcher button (FAB) at bottom-right
  if (!isOpen) {
    return (
      <div className="fixed bottom-6 right-6 z-50 animate-fade-in">
        <button
          onClick={onOpen}
          className="group relative flex items-center justify-center w-14 h-14 rounded-full bg-gradient-to-tr from-accent-500 to-teal-400 text-base-950 shadow-[0_4px_25px_rgba(45,212,191,0.35)] hover:shadow-[0_6px_30px_rgba(45,212,191,0.5)] hover:scale-105 active:scale-95 transition-all duration-300 border border-accent-300/40"
          title="Ask SkillBridge AI"
        >
          <span className="absolute -inset-1 rounded-full bg-accent-400/20 animate-ping opacity-60" />
          <TbSparkles className="w-6 h-6 text-base-950 transition-transform duration-300 group-hover:rotate-12" />
        </button>
      </div>
    );
  }

  // Floating docked assistant window
  return (
    <div className="fixed bottom-6 right-6 z-50 w-[94vw] sm:w-[420px] h-[560px] max-h-[85vh] flex flex-col bg-base-900/95 border border-accent-400/40 rounded-3xl shadow-[0_15px_50px_rgba(0,0,0,0.85)] backdrop-blur-2xl overflow-hidden transition-all duration-300 animate-slide-up">
      {/* Top Header */}
      <div className="px-4 py-3 border-b border-base-800 bg-base-950/80 flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-accent-400 to-teal-500 flex items-center justify-center text-base-950 font-bold shadow-glow">
            <TbSparkles className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center space-x-1.5">
              <h3 className="font-heading text-xs font-bold text-white tracking-wide">
                SkillBridge AI Assistant
              </h3>
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            </div>
            <p className="text-[10px] text-white/40">RAG Dense Vector Search & Citations</p>
          </div>
        </div>

        <div className="flex items-center space-x-1">
          {conversation.length > 0 && (
            <button
              onClick={handleClear}
              className="p-1.5 rounded-lg text-white/40 hover:text-white hover:bg-white/10 transition-colors"
              title="Clear chat"
            >
              <TbTrash className="w-3.5 h-3.5" />
            </button>
          )}
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-white/40 hover:text-white hover:bg-white/10 transition-colors"
            title="Minimize"
          >
            <TbMinus className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-white/40 hover:text-white hover:bg-white/10 transition-colors"
            title="Close"
          >
            <TbX className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Provider Selector Subheader */}
      <div className="px-3.5 py-1.5 bg-base-950/90 border-b border-base-800/80 flex items-center justify-between text-[11px]">
        <div className="flex items-center space-x-1 text-white/50">
          <TbCpu className="w-3.5 h-3.5 text-accent-400" />
          <span>Provider:</span>
        </div>

        <div className="relative">
          <button
            type="button"
            onClick={() => setShowProviderMenu(!showProviderMenu)}
            className="flex items-center space-x-1 px-2 py-0.5 rounded-lg bg-base-900 border border-base-700 text-white/80 hover:text-accent-300 font-mono text-[10px]"
          >
            <span className="capitalize">{selectedProvider}</span>
            <TbChevronDown className="w-3 h-3 text-white/40" />
          </button>

          {showProviderMenu && (
            <div className="absolute right-0 top-full mt-1 w-44 rounded-xl bg-base-900 border border-base-700 shadow-xl py-1 z-50">
              <button
                type="button"
                onClick={() => {
                  setSelectedProvider('auto');
                  setShowProviderMenu(false);
                }}
                className={`w-full text-left px-3 py-1.5 text-[11px] flex items-center justify-between hover:bg-white/5 ${
                  selectedProvider === 'auto' ? 'text-accent-300 font-semibold' : 'text-white/70'
                }`}
              >
                <span>Auto (Cascading)</span>
                <span className="text-[9px] text-white/30">Default</span>
              </button>

              {providers.map((p) => (
                <button
                  key={p.name}
                  type="button"
                  onClick={() => {
                    setSelectedProvider(p.name);
                    setShowProviderMenu(false);
                  }}
                  className={`w-full text-left px-3 py-1.5 text-[11px] flex items-center justify-between hover:bg-white/5 ${
                    selectedProvider === p.name ? 'text-accent-300 font-semibold' : 'text-white/70'
                  }`}
                >
                  <span className="capitalize">{p.name}</span>
                  <span
                    className={`text-[9px] px-1 rounded ${
                      p.available ? 'text-emerald-400' : 'text-white/30'
                    }`}
                  >
                    {p.available ? 'Ready' : 'Not Set'}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 scrollbar-thin">
        {conversation.length === 0 ? (
          <div className="py-6 text-center space-y-4">
            <div className="w-12 h-12 rounded-2xl bg-accent-500/10 border border-accent-400/20 flex items-center justify-center mx-auto text-accent-300">
              <TbBulb className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-semibold text-white">Ask your Career AI</p>
              <p className="text-xs text-white/50 max-w-[280px] mx-auto mt-1">
                Grounded on your verified skills, benchmark curricula, and discoverable jobs with source citations.
              </p>
            </div>

            {/* Quick Prompt Chips */}
            <div className="flex flex-col gap-2 pt-1 text-left">
              {QUICK_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => handleAsk(prompt)}
                  disabled={loading}
                  className="text-xs px-3 py-2 rounded-xl bg-base-800/80 hover:bg-accent-500/15 border border-base-700 hover:border-accent-400/40 text-white/80 hover:text-accent-300 transition-all duration-200 flex items-center justify-between group"
                >
                  <span className="truncate">"{prompt}"</span>
                  <span className="text-white/30 group-hover:text-accent-300 text-xs">→</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {conversation.map((msg, idx) => (
              <div
                key={idx}
                className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'} animate-fade-in`}
              >
                <div
                  className={`p-3.5 rounded-2xl max-w-[90%] text-xs leading-relaxed ${
                    msg.sender === 'user'
                      ? 'bg-accent-500/25 text-white border border-accent-400/30 rounded-br-sm'
                      : 'bg-base-800/90 text-white/90 border border-base-700/80 rounded-bl-sm shadow-sm'
                  }`}
                >
                  {msg.sender === 'user' ? (
                    <p className="whitespace-pre-wrap">{msg.text}</p>
                  ) : (
                    <div>{formatAssistantMessage(msg.text)}</div>
                  )}
                </div>

                {/* Assistant footer: RAG Grounding + TTS speaker */}
                {msg.sender === 'assistant' && (
                  <div className="flex items-center justify-between w-[90%] text-[10px] text-white/40 mt-1 pl-1">
                    <div className="flex items-center space-x-1.5">
                      <TbShieldCheck className="w-3 h-3 text-emerald-400" />
                      <span>{msg.source || 'RAG Vector Grounded'}</span>
                    </div>

                    {isSpeechSynthesisSupported() && (
                      <button
                        onClick={() => handleToggleSpeakMessage(msg.text, idx)}
                        className={`p-1 rounded hover:text-white transition-colors flex items-center space-x-1 ${
                          speakingMsgIdx === idx ? 'text-accent-300 animate-pulse' : 'text-white/40'
                        }`}
                        title={speakingMsgIdx === idx ? 'Stop audio' : 'Listen to response'}
                      >
                        {speakingMsgIdx === idx ? (
                          <TbVolumeOff className="w-3.5 h-3.5" />
                        ) : (
                          <TbVolume className="w-3.5 h-3.5" />
                        )}
                      </button>
                    )}
                  </div>
                )}
              </div>
            ))}

            {/* Collapsible Suggestion Pills */}
            <div className="pt-2 text-center">
              <button
                onClick={() => setShowPrompts(!showPrompts)}
                className="text-[10px] text-white/40 hover:text-accent-300 transition-colors"
              >
                {showPrompts ? 'Hide suggested prompts ▲' : 'Show suggested prompts ▼'}
              </button>
              {showPrompts && (
                <div className="flex flex-wrap gap-1.5 justify-center pt-2">
                  {QUICK_PROMPTS.slice(0, 2).map((prompt) => (
                    <button
                      key={prompt}
                      onClick={() => handleAsk(prompt)}
                      disabled={loading}
                      className="text-[10px] px-2.5 py-1 rounded-lg bg-base-800/70 border border-base-700 text-accent-300/80 hover:text-accent-300 hover:border-accent-400/30 transition-all"
                    >
                      "{prompt}"
                    </button>
                  ))}
                </div>
              )}
            </div>
          </>
        )}

        {loading && (
          <div className="flex items-center space-x-2 text-xs text-white/60 surface p-3 rounded-2xl max-w-[80%] border border-base-700 animate-pulse">
            <div className="w-3.5 h-3.5 border-2 border-accent-400/30 border-t-accent-400 rounded-full animate-spin" />
            <span className="text-[11px]">Retrieving dense RAG context and answering...</span>
          </div>
        )}

        {error && <p className="text-xs text-rose-400 px-1">{error}</p>}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Field with STT Mic button */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleAsk();
        }}
        className="p-3 border-t border-base-800 bg-base-950/80 flex items-center space-x-2"
      >
        {isSpeechRecognitionSupported() && (
          <button
            type="button"
            onClick={handleToggleRecord}
            className={`p-2.5 rounded-xl border transition-all ${
              isRecording
                ? 'bg-rose-500/25 text-rose-300 border-rose-500/50 animate-pulse'
                : 'bg-base-900 border-base-700 text-white/50 hover:text-white'
            }`}
            title={isRecording ? 'Stop recording' : 'Speak your question'}
          >
            {isRecording ? (
              <TbMicrophoneOff className="w-4 h-4" />
            ) : (
              <TbMicrophone className="w-4 h-4" />
            )}
          </button>
        )}

        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={isRecording ? 'Listening to voice...' : 'Ask about careers, skills, jobs...'}
          className="input-field text-xs py-2 px-3.5 flex-1 bg-base-900 border border-base-700 focus:border-accent-400 rounded-xl text-white placeholder-white/30 transition-all"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="p-2.5 rounded-xl bg-gradient-to-r from-accent-400 to-teal-500 text-base-950 disabled:opacity-30 hover:scale-105 active:scale-95 transition-all font-bold shadow-sm"
          title="Send"
        >
          <TbSend className="w-3.5 h-3.5" />
        </button>
      </form>
    </div>
  );
}
