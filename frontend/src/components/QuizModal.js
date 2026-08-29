import React, { useState, useEffect } from 'react';
import { TbX, TbCheck, TbAlertCircle } from 'react-icons/tb';
import skillService from '../services/skillService';

export default function QuizModal({ skill, onClose, onQuizComplete }) {
  const [loading, setLoading] = useState(true);
  const [quizData, setQuizData] = useState(null);
  const [answers, setAnswers] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!skill) return;
    setLoading(true);
    setError('');

    skillService.getQuiz(skill.id || skill.skill_id)
      .then((data) => {
        setQuizData(data);
      })
      .catch((err) => {
        setError(err.response?.data?.error || 'Failed to load quiz questions.');
      })
      .finally(() => setLoading(false));
  }, [skill]);

  const handleSelectOption = (questionId, optionLetter) => {
    setAnswers((prev) => ({
      ...prev,
      [questionId]: optionLetter,
    }));
  };

  const handleSubmit = async () => {
    if (!quizData || Object.keys(answers).length === 0) return;
    setSubmitting(true);
    setError('');

    try {
      const res = await skillService.submitQuiz(skill.id || skill.skill_id, answers);
      setResult(res);
      if (onQuizComplete) {
        onQuizComplete(res);
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Error submitting quiz.');
    } finally {
      setSubmitting(false);
    }
  };

  if (!skill) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
      <div className="glass w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden shadow-2xl border-base-700">
        {/* Header */}
        <div className="px-6 py-4 border-b border-base-700/60 flex items-center justify-between">
          <div>
            <span className="text-xs font-mono uppercase tracking-wider text-accent-400">
              Skill Assessment
            </span>
            <h2 className="text-lg font-semibold text-white capitalize">
              {skill.skill_name} Verification
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-white/40 hover:text-white p-1 rounded-lg hover:bg-white/5"
          >
            <TbX className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading && (
            <div className="py-12 text-center">
              <div className="inline-block w-8 h-8 border-2 border-accent-400/30 border-t-accent-400 rounded-full animate-spin mb-3" />
              <p className="text-sm text-white/50">Generating adaptive questions...</p>
            </div>
          )}

          {error && (
            <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 flex items-center space-x-3 text-sm">
              <TbAlertCircle className="w-5 h-5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Result view */}
          {result && (
            <div className="py-8 text-center space-y-4">
              <div className={`w-16 h-16 mx-auto rounded-full flex items-center justify-center ${
                result.quiz_score_percent >= 60
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                  : 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
              }`}>
                {result.quiz_score_percent >= 60 ? (
                  <TbCheck className="w-8 h-8" />
                ) : (
                  <TbAlertCircle className="w-8 h-8" />
                )}
              </div>

              <div>
                <h3 className="text-2xl font-bold text-white">
                  Score: {result.quiz_score_percent}%
                </h3>
                <p className="text-sm text-white/50 mt-1">
                  Answered {result.correct_count} of {result.total_questions} questions correctly.
                </p>
                <div className="mt-3 inline-block px-4 py-1.5 rounded-full bg-accent-500/15 border border-accent-400/30 text-accent-300 text-xs font-mono">
                  Verification Score: {Math.round(result.verification_score * 100)}%
                </div>
              </div>

              <div className="pt-4">
                <button onClick={onClose} className="btn-primary max-w-xs mx-auto text-sm py-2.5">
                  Done & Close
                </button>
              </div>
            </div>
          )}

          {/* Questions list */}
          {!loading && !result && quizData && (
            <div className="space-y-6">
              <div className="flex items-center justify-between text-xs text-white/40 border-b border-base-800 pb-3">
                <span>{quizData.questions?.length || 0} Questions</span>
                <span>Choose the best answer for each question</span>
              </div>

              {quizData.questions?.map((q, qIndex) => (
                <div key={q.id} className="surface p-4 rounded-xl space-y-3">
                  <div className="flex items-start space-x-2.5">
                    <span className="w-6 h-6 rounded-full bg-base-700 text-white/70 text-xs flex items-center justify-center font-mono flex-shrink-0">
                      {qIndex + 1}
                    </span>
                    <p className="text-sm font-medium text-white leading-relaxed">
                      {q.question}
                    </p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-1 pl-8">
                    {['A', 'B', 'C', 'D'].map((letter) => {
                      const optKey = `option_${letter.toLowerCase()}`;
                      const optText = q[optKey];
                      if (!optText) return null;
                      const isSelected = answers[q.id] === letter;

                      return (
                        <button
                          key={letter}
                          type="button"
                          onClick={() => handleSelectOption(q.id, letter)}
                          className={`flex items-center p-3 rounded-lg border text-left text-xs transition-all ${
                            isSelected
                              ? 'bg-accent-500/20 border-accent-400/60 text-white shadow-glow'
                              : 'bg-base-900/60 border-base-700/60 text-white/70 hover:bg-white/5 hover:text-white'
                          }`}
                        >
                          <span className={`w-5 h-5 rounded-md flex items-center justify-center font-mono text-[10px] mr-2 flex-shrink-0 ${
                            isSelected
                              ? 'bg-accent-400 text-base-950 font-bold'
                              : 'bg-base-800 text-white/50'
                          }`}>
                            {letter}
                          </span>
                          <span className="flex-1 truncate">{optText}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer actions */}
        {!result && (
          <div className="px-6 py-4 border-t border-base-700/60 flex items-center justify-between bg-base-950/40">
            <span className="text-xs text-white/40">
              {Object.keys(answers).length} of {quizData?.questions?.length || 0} answered
            </span>
            <div className="flex space-x-3">
              <button onClick={onClose} className="btn-ghost text-xs">
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                disabled={submitting || Object.keys(answers).length === 0}
                className="btn-primary text-xs py-2 px-5 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {submitting ? 'Scoring...' : 'Submit Answers'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
