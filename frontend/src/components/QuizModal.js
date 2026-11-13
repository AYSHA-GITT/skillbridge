import React, { useState, useEffect } from 'react';
import { TbX, TbCheck, TbAlertCircle, TbBulb, TbLoader2, TbChevronDown, TbChevronUp } from 'react-icons/tb';
import skillService from '../services/skillService';

export default function QuizModal({ skill, onClose, onQuizComplete }) {
  const [loading, setLoading] = useState(true);
  const [quizData, setQuizData] = useState(null);
  const [answers, setAnswers] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  // Post-quiz explanation state
  const [explanations, setExplanations] = useState(null);
  const [loadingExplanations, setLoadingExplanations] = useState(false);
  const [explanationError, setExplanationError] = useState('');
  const [expandedExpl, setExpandedExpl] = useState({});

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
    if (!quizData || (quizData.questions || []).some((q) => !answers[q.id])) {
      setError('Please answer every question before submitting.');
      return;
    }
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

  const handleExplainMistakes = async () => {
    if (!result || !result.review) return;

    // Build payload with the question text, the student's wrong choice, and the correct choice text
    const wrongAnswers = result.review
      .filter((r) => !r.is_correct)
      .map((r) => ({
        question: r.question,
        your_answer_text: r.your_answer
          ? quizData?.questions?.find((q) => q.id === r.question_id)?.[`option_${r.your_answer.toLowerCase()}`] || r.your_answer
          : 'No answer selected',
        correct_answer_text: r.correct_option_text || r.correct_answer,
        difficulty: r.difficulty,
      }));

    if (wrongAnswers.length === 0) return;

    setLoadingExplanations(true);
    setExplanationError('');
    try {
      const res = await skillService.getQuizExplanation(skill.id || skill.skill_id, wrongAnswers);
      setExplanations(res.explanations || []);
      // Auto-expand first explanation
      if (res.explanations?.length > 0) {
        setExpandedExpl({ 0: true });
      }
    } catch (err) {
      setExplanationError(err.response?.data?.error || 'Failed to generate explanations. Please try again.');
    } finally {
      setLoadingExplanations(false);
    }
  };

  if (!skill) return null;

  const wrongCount = result ? result.review?.filter((r) => !r.is_correct).length : 0;

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

          {/* ── Result view ── */}
          {result && (
            <div className="space-y-6">
              {/* Score summary */}
              <div className="text-center space-y-3 py-4">
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
                  {result.proficiency && (
                    <p className="text-xs text-white/60 mt-2">Demonstrated level: {result.proficiency}</p>
                  )}
                </div>
              </div>

              {/* Wrong answers review */}
              {Array.isArray(result.review) && wrongCount > 0 && (
                <div className="space-y-4">
                  {/* Section header with Explain button */}
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold text-white/80 flex items-center space-x-2">
                      <span>Review Your Mistakes</span>
                      <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-400/30">
                        {wrongCount} incorrect
                      </span>
                    </h4>

                    {!explanations && (
                      <button
                        type="button"
                        onClick={handleExplainMistakes}
                        disabled={loadingExplanations}
                        className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-accent-500/15 border border-accent-400/30 text-accent-300 hover:bg-accent-500/25 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {loadingExplanations ? (
                          <>
                            <TbLoader2 className="w-3.5 h-3.5 animate-spin" />
                            <span>Generating...</span>
                          </>
                        ) : (
                          <>
                            <TbBulb className="w-3.5 h-3.5" />
                            <span>Explain My Mistakes</span>
                          </>
                        )}
                      </button>
                    )}
                  </div>

                  {explanationError && (
                    <div className="p-3 rounded-xl bg-rose-950/30 border border-rose-500/30 text-rose-300 text-xs flex items-center space-x-2">
                      <TbAlertCircle className="w-4 h-4 flex-shrink-0" />
                      <span>{explanationError}</span>
                    </div>
                  )}

                  {/* Wrong answer cards */}
                  <div className="space-y-3">
                    {result.review.filter((r) => !r.is_correct).map((r, idx) => {
                      const expl = explanations ? explanations[idx] : null;
                      const isOpen = !!expandedExpl[idx];
                      return (
                        <div key={r.question_id} className="rounded-xl border border-base-700/60 overflow-hidden">
                          {/* Question row */}
                          <div className="bg-base-950/60 p-4 space-y-2">
                            <p className="text-xs font-medium text-white/90 leading-relaxed">{r.question}</p>
                            <div className="flex flex-col sm:flex-row sm:items-center gap-1.5 text-[11px] font-mono">
                              <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-lg bg-rose-950/50 border border-rose-500/30 text-rose-300">
                                <TbX className="w-3 h-3" />
                                <span>Your answer: {r.your_answer || '—'}</span>
                              </span>
                              <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-lg bg-emerald-950/50 border border-emerald-500/30 text-emerald-300">
                                <TbCheck className="w-3 h-3" />
                                <span>Correct: {r.correct_answer}{r.correct_option_text ? ` — ${r.correct_option_text}` : ''}</span>
                              </span>
                              {r.difficulty && (
                                <span className="text-white/30 px-1">
                                  {r.difficulty}
                                </span>
                              )}
                            </div>
                          </div>

                          {/* AI Explanation panel */}
                          {expl && (
                            <div className="border-t border-base-700/40">
                              <button
                                type="button"
                                onClick={() => setExpandedExpl((prev) => ({ ...prev, [idx]: !isOpen }))}
                                className="w-full flex items-center justify-between px-4 py-2.5 bg-accent-950/20 hover:bg-accent-950/30 transition-colors text-left"
                              >
                                <div className="flex items-center space-x-2">
                                  <TbBulb className="w-3.5 h-3.5 text-accent-400" />
                                  <span className="text-xs font-semibold text-accent-300">AI Explanation</span>
                                </div>
                                {isOpen
                                  ? <TbChevronUp className="w-3.5 h-3.5 text-white/40" />
                                  : <TbChevronDown className="w-3.5 h-3.5 text-white/40" />
                                }
                              </button>
                              {isOpen && (
                                <div className="px-4 py-3 bg-accent-950/10 border-t border-accent-400/10">
                                  <p className="text-xs text-white/75 leading-relaxed">{expl.explanation}</p>
                                </div>
                              )}
                            </div>
                          )}

                          {/* Loading shimmer for explanation */}
                          {loadingExplanations && !expl && (
                            <div className="border-t border-base-700/40 px-4 py-3 bg-accent-950/10">
                              <div className="h-3 bg-accent-400/10 rounded animate-pulse w-3/4 mb-1.5" />
                              <div className="h-3 bg-accent-400/10 rounded animate-pulse w-1/2" />
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>

                  {/* Prompt to explain if not yet triggered */}
                  {!explanations && !loadingExplanations && (
                    <p className="text-[11px] text-white/40 text-center">
                      Click <span className="text-accent-400 font-medium">Explain My Mistakes</span> above to get Gemini-powered explanations for each wrong answer.
                    </p>
                  )}
                </div>
              )}

              {/* All correct — no mistakes */}
              {Array.isArray(result.review) && wrongCount === 0 && (
                <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/20 text-center text-xs text-emerald-300">
                  🎉 Perfect score! No mistakes to explain — great work!
                </div>
              )}

              <div className="pt-2 text-center">
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
                disabled={submitting || !quizData || (quizData.questions || []).some((q) => !answers[q.id])}
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
