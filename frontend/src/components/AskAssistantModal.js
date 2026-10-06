import React, { useState, useRef, useEffect } from 'react';
import skillService from '../services/skillService';
import {
  TbSparkles,
  TbX,
  TbMinus,
  TbSend,
  TbBulb,
  TbShieldCheck,
  TbTrash
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
    const parts = para.split(/(\*\*[^*]+\*\*)/g);
    return (
      <p key={pIdx} className="mb-1.5 last:mb-0 leading-relaxed">
        {parts.map((part, partIdx) => {
          if (part.startsWith('**') && part.endsWith('**')) {
            return (
              <strong key={partIdx} className="font-semibold text-accent-300">
                {part.slice(2, -2)}
              </strong>
            );
          }
          return <span key={partIdx}>{part}</span>;
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

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [conversation, loading, isOpen]);

  const handleAsk = async (queryToAsk) => {
    const q = (queryToAsk || question).trim();
    if (!q) return;

    setLoading(true);
    setError('');

    const newConvo = [...conversation, { sender: 'user', text: q }];
    setConversation(newConvo);
    setQuestion('');
    setShowPrompts(false);

    try {
      const res = await skillService.askAssistant(q);
      setConversation([
        ...newConvo,
        {
          sender: 'assistant',
          text: res.answer,
          source: res.source,
          groundedOn: res.grounded_on
        }
      ]);
    } catch {
      setError('Could not reach the assistant. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setConversation([]);
    setError('');
    setShowPrompts(true);
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
    <div className="fixed bottom-6 right-6 z-50 w-[92vw] sm:w-[390px] h-[520px] max-h-[82vh] flex flex-col bg-base-900/95 border border-accent-400/40 rounded-3xl shadow-[0_15px_50px_rgba(0,0,0,0.85)] backdrop-blur-2xl overflow-hidden transition-all duration-300 animate-slide-up">
      {/* Top Header */}
      <div className="px-4 py-3.5 border-b border-base-800 bg-base-950/80 flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-accent-400 to-teal-500 flex items-center justify-center text-base-950 font-bold shadow-glow">
            <TbSparkles className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center space-x-1.5">
              <h3 className="font-heading text-xs font-bold text-white tracking-wide">
                SkillBridge AI
              </h3>
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            </div>
            <p className="text-[10px] text-white/40">Grounded on verified skills</p>
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

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 scrollbar-thin">
        {conversation.length === 0 ? (
          <div className="py-6 text-center space-y-4">
            <div className="w-12 h-12 rounded-2xl bg-accent-500/10 border border-accent-400/20 flex items-center justify-center mx-auto text-accent-300">
              <TbBulb className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-semibold text-white">Ask your Career AI</p>
              <p className="text-xs text-white/50 max-w-[260px] mx-auto mt-1">
                Get instant guidance on career readiness, skill gaps, or learning steps.
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
                  className={`p-3 rounded-2xl max-w-[88%] text-xs leading-relaxed ${
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
                {msg.sender === 'assistant' && msg.source && (
                  <div className="flex items-center space-x-1 text-[10px] text-white/40 mt-1 pl-1">
                    <TbShieldCheck className="w-3 h-3 text-emerald-400" />
                    <span>Grounded · {msg.source}</span>
                  </div>
                )}
              </div>
            ))}

            {/* Collapsible Suggestion Pills if conversation already started */}
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
          <div className="flex items-center space-x-2 text-xs text-white/60 surface p-3 rounded-2xl max-w-[75%] border border-base-700 animate-pulse">
            <div className="w-3.5 h-3.5 border-2 border-accent-400/30 border-t-accent-400 rounded-full animate-spin" />
            <span className="text-[11px]">Analyzing your verified skills...</span>
          </div>
        )}

        {error && <p className="text-xs text-rose-400 px-1">{error}</p>}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Field */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleAsk();
        }}
        className="p-3 border-t border-base-800 bg-base-950/80 flex items-center space-x-2"
      >
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask about careers, skills..."
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
