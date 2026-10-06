import React, { useState } from 'react';
import skillService from '../services/skillService';
import {
  TbSparkles,
  TbX,
  TbSend,
  TbBulb,
  TbShieldCheck
} from 'react-icons/tb';

const QUICK_PROMPTS = [
  'What should I learn next?',
  'Why was my top career recommended?',
  'What is my biggest skill gap?',
  'How can I improve my salary?'
];

export default function AskAssistantModal({ isOpen, onClose }) {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversation, setConversation] = useState([]);
  const [error, setError] = useState('');

  if (!isOpen) return null;

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

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="glass max-w-xl w-full p-6 sm:p-7 rounded-3xl border border-accent-400/40 shadow-glow flex flex-col max-h-[85vh] space-y-4">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-base-800 pb-3">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-xl bg-accent-500/20 text-accent-300 flex items-center justify-center border border-accent-400/30">
              <TbSparkles className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-heading text-lg font-bold text-white">
                Ask SkillBridge Assistant
              </h3>
              <p className="text-[11px] text-white/50">
                Grounded strictly on your verified skills & target career
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-white/40 hover:text-white hover:bg-white/10"
          >
            <TbX className="w-5 h-5" />
          </button>
        </div>

        {/* Conversation Thread */}
        <div className="flex-1 overflow-y-auto space-y-3 pr-1 min-h-[220px] max-h-[360px]">
          {conversation.length === 0 ? (
            <div className="py-8 text-center space-y-3">
              <TbBulb className="w-8 h-8 text-accent-400 mx-auto" />
              <p className="text-xs text-white/60 max-w-xs mx-auto">
                Ask anything about your readiness, missing skills, career recommendations, or next steps.
              </p>
              <div className="flex flex-wrap gap-1.5 justify-center pt-2">
                {QUICK_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => handleAsk(prompt)}
                    disabled={loading}
                    className="text-[11px] px-2.5 py-1.5 rounded-lg surface border border-base-700 text-accent-300 hover:border-accent-400/40 hover:bg-accent-500/10 transition-all text-left"
                  >
                    "{prompt}"
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
                  className={`p-3.5 rounded-2xl max-w-[88%] text-xs leading-relaxed ${
                    msg.sender === 'user'
                      ? 'bg-accent-500/20 text-white border border-accent-400/30'
                      : 'surface text-white/90 border border-base-700/80'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{msg.text}</p>
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
            <div className="flex items-center space-x-2 text-xs text-white/50 surface p-3 rounded-2xl max-w-[60%]">
              <div className="w-4 h-4 border-2 border-accent-400/30 border-t-accent-400 rounded-full animate-spin" />
              <span>Checking your verified profile...</span>
            </div>
          )}
        </div>

        {error && <p className="text-xs text-rose-400">{error}</p>}

        {/* Input Field */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleAsk();
          }}
          className="flex items-center space-x-2 pt-2 border-t border-base-800"
        >
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask a question about your career path..."
            className="input-field text-xs py-2.5 flex-1"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !question.trim()}
            className="btn-primary p-2.5 rounded-xl disabled:opacity-40"
          >
            <TbSend className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
