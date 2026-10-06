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
      <p key={pIdx} className="mb-1.5 last:mb-0">
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
  };

  // If closed, display the convenient Floating Action Button (FAB) at bottom-right
  if (!isOpen) {
    return (
      <div className="fixed bottom-6 right-6 z-50">
        <button
          onClick={onOpen}
          className="group flex items-center space-x-2.5 px-4 py-3 rounded-full bg-gradient-to-r from-accent-400 via-teal-500 to-accent-500 text-base-950 font-bold shadow-2xl hover:scale-105 active:scale-95 transition-all border border-accent-300/50 shadow-glow"
          title="Open SkillBridge AI Career Assistant"
        >
          <div className="w-6 h-6 rounded-full bg-base-950/20 flex items-center justify-center">
            <TbSparkles className="w-4 h-4 text-base-950 animate-pulse" />
          </div>
          <span className="text-xs font-heading font-bold text-base-950 tracking-tight">
            Ask AI
          </span>
        </button>
      </div>
    );
  }

  // When open, display docked chat card in bottom-right corner
  return (
    <div className="fixed bottom-6 right-6 z-50 w-[92vw] sm:w-[420px] h-[560px] max-h-[85vh] flex flex-col bg-base-900/95 border border-accent-400/40 rounded-2xl shadow-2xl backdrop-blur-xl overflow-hidden animate-fade-in">
      {/* Header */}
      <div className="px-4 py-3 border-b border-base-800 bg-base-950/80 flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-accent-400 to-teal-600 flex items-center justify-center text-base-950 font-bold shadow-glow">
            <TbSparkles className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="font-heading text-xs font-bold text-white tracking-tight">
                SkillBridge AI Assistant
              </h3>
              <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse" title="Active & Grounded" />
            </div>
            <p className="text-[10px] text-white/50">
              Grounded on your verified skills & FL model
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-1">
          {conversation.length > 0 && (
            <button
              onClick={handleClear}
              className="p-1.5 rounded-lg text-white/40 hover:text-white hover:bg-white/10 transition-colors"
              title="Clear chat"
            >
              <TbTrash className="w-4 h-4" />
            </button>
          )}
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-white/40 hover:text-white hover:bg-white/10 transition-colors"
            title="Minimize"
          >
            <TbMinus className="w-4 h-4" />
          </button>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-white/40 hover:text-white hover:bg-white/10 transition-colors"
            title="Close"
          >
            <TbX className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Conversation Thread */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 pr-2 scrollbar-thin">
        {conversation.length === 0 ? (
          <div className="py-6 text-center space-y-3">
            <div className="w-12 h-12 rounded-2xl bg-accent-500/10 border border-accent-400/20 flex items-center justify-center mx-auto text-accent-300">
              <TbBulb className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs font-semibold text-white">How can I help you today?</p>
              <p className="text-[11px] text-white/50 max-w-[280px] mx-auto mt-0.5">
                Ask about readiness, next skills to learn, salary boost, or federated privacy.
              </p>
            </div>
            <div className="flex flex-col gap-1.5 pt-2 text-left">
              {QUICK_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => handleAsk(prompt)}
                  disabled={loading}
                  className="text-[11px] px-3 py-2 rounded-xl surface border border-base-700/80 text-accent-300 hover:border-accent-400/50 hover:bg-accent-500/10 transition-all text-left flex items-center justify-between group"
                >
                  <span>"{prompt}"</span>
                  <span className="text-white/30 group-hover:text-accent-300 transition-colors text-[10px]">→</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          conversation.map((msg, idx) => (
            <div
              key={idx}
              className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}
            >
              <div
                className={`p-3 rounded-2xl max-w-[90%] text-xs leading-relaxed ${
                  msg.sender === 'user'
                    ? 'bg-accent-500/20 text-white border border-accent-400/30 rounded-br-sm'
                    : 'bg-base-800/80 text-white/90 border border-base-700/80 rounded-bl-sm'
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
                  <span>Grounded on profile · {msg.source}</span>
                </div>
              )}
            </div>
          ))
        )}

        {loading && (
          <div className="flex items-center space-x-2 text-xs text-white/60 surface p-3 rounded-2xl max-w-[75%] border border-base-700">
            <div className="w-4 h-4 border-2 border-accent-400/30 border-t-accent-400 rounded-full animate-spin" />
            <span className="text-[11px]">Analyzing your verified skills...</span>
          </div>
        )}

        {error && <p className="text-xs text-rose-400 px-1">{error}</p>}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
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
          placeholder="Ask a career question..."
          className="input-field text-xs py-2 px-3 flex-1 bg-base-900 border border-base-700 focus:border-accent-400 rounded-xl text-white placeholder-white/30"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="p-2.5 rounded-xl bg-gradient-to-r from-accent-400 to-teal-500 text-base-950 disabled:opacity-40 hover:opacity-90 transition-opacity font-bold"
          title="Send"
        >
          <TbSend className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
}
