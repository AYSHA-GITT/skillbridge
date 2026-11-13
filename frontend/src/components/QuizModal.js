import React, { useState, useEffect } from 'react';
import {
  TbX,
  TbCheck,
  TbAlertCircle,
  TbBulb,
  TbLoader2,
  TbChevronDown,
  TbChevronUp,
  TbSparkles,
  TbCircleCheck,
  TbCircleX
} from 'react-icons/tb';
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

  const handleExplainMistakes = async (submittedResult = result) => {
    const activeResult = submittedResult || result;
    if (!activeResult || !activeResult.review) return;

    const wrongList = activeResult.review.filter((r) => !r.is_correct);
    if (wrongList.length === 0) return;

    // Build payload with question text, options, student choice, and correct choice
    const wrongAnswers = wrongList.map((r) => {
      const qObj = quizData?.questions?.find((q) => q.id === r.question_id);
      const opts = r.options || (qObj ? {
        A: qObj.option_a,
        B: qObj.option_b,
        C: qObj.option_c,
        D: qObj.option_d,
      } : {});

      return {
        question: r.question,
        your_answer: r.your_answer,
        your_answer_text: r.your_option_text || (r.your_answer ? opts[r.your_answer] : 'No answer'),
        correct_answer: r.correct_answer,
        correct_answer_text: r.correct_option_text || opts[r.correct_answer] || r.correct_answer,
        options: opts,
        difficulty: r.difficulty,
      };
    });

    setLoadingExplanations(true);
    setExplanationError('');
    try {
      const res = await skillService.getQuizExplanation(skill.id || skill.skill_id, wrongAnswers);
      const explList = res.explanations || [];
      setExplanations(explList);

      // Auto-expand all explanations
      const expandAll = {};
      explList.forEach((_, idx) => { expandAll[idx] = true; });
      setExpandedExpl(expandAll);
    } catch (err) {
      setExplanationError(err.response?.data?.error || 'Failed to generate explanations. Please try again.');
    } finally {
      setLoadingExplanations(false);
    }
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
      // Automatically request rich explanations for incorrect answers
      const incorrectCount = (res.review || []).filter((r) => !r.is_correct).length;
      if (incorrectCount > 0) {
        handleExplainMistakes(res);
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Error submitting quiz.');
    } finally {
      setSubmitting(false);
    }
  };

  if (!skill) return null;

  const wrongCount = result ? (result.review?.filter((r) => !r.is_correct).length || 0) : 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
      <div className="glass w-full max-w-3xl max-h-[92vh] flex flex-col overflow-hidden shadow-2xl border-base-700 rounded-3xl">
        {/* Header */}
        <div className="px-6 py-4 border-b border-base-700/60 flex items-center justify-between bg-base-950/60">
          <div>
            <span className="text-xs font-mono uppercase tracking-wider text-accent-400">
              Technical Skill Assessment
            </span>
            <h2 className="text-lg font-bold text-white capitalize">
              {skill.skill_name} Verification
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-white/40 hover:text-white p-1.5 rounded-xl hover:bg-white/5 transition-colors"
          >
            <TbX className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          {error && (
            <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center space-x-2">
              <TbAlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {loading && (
            <div className="py-12 text-center text-white/50 text-xs flex flex-col items-center space-y-3">
              <div className="w-7 h-7 border-2 border-accent-400/30 border-t-accent-400 rounded-full animate-spin" />
              <span>Loading adaptive technical questions...</span>
            </div>
          )}

          {/* Result view */}
          {result && (
            <div className="space-y-6 animate-slide-up">
              {/* Score banner */}
              <div className="p-6 rounded-2xl bg-base-900/80 border border-base-700 flex flex-col sm:flex-row items-center sm:items-start space-y-4 sm:space-y-0 sm:space-x-6">
                <div className={`w-20 h-20 rounded-2xl flex items-center justify-center text-3xl font-bold font-mono flex-shrink-0 shadow-lg ${
                  result.quiz_score_percent >= 70
                    ? 'bg-emerald-500/15 border border-emerald-400/40 text-emerald-400'
                    : 'bg-rose-500/15 border border-rose-400/40 text-rose-400'
                }`}>
                  {result.quiz_score_percent >= 70 ? (
                    <TbCircleCheck className="w-10 h-10" />
                  ) : (
                    <TbCircleX className="w-10 h-10" />
                  )}
                </div>

                <div className="flex-1 text-center sm:text-left">
                  <h3 className="text-2xl font-bold text-white font-heading">
                    Score: {result.quiz_score_percent}%
                  </h3>
                  <p className="text-xs text-white/60 mt-1">
                    Answered {result.correct_count} of {result.total_questions} questions correctly.
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2 justify-center sm:justify-start">
                    <span className="px-3 py-1 rounded-full bg-accent-500/15 border border-accent-400/30 text-accent-300 text-xs font-mono font-semibold">
                      Verification Score: {Math.round(result.verification_score * 100)}%
                    </span>
                    {result.proficiency && (
                      <span className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-white/70 text-xs font-medium">
                        Level: {result.proficiency}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Wrong answers review */}
              {Array.isArray(result.review) && wrongCount > 0 && (
                <div className="space-y-5">
                  {/* Section header */}
                  <div className="flex items-center justify-between pb-2 border-b border-base-700/60">
                    <h4 className="text-sm font-bold text-white flex items-center space-x-2">
                      <span>Review Your Mistakes & Conceptual Breakdown</span>
                      <span className="text-xs font-mono px-2.5 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-400/30">
                        {wrongCount} incorrect
                      </span>
                    </h4>

                    {!loadingExplanations && (
                      <button
                        type="button"
                        onClick={() => handleExplainMistakes()}
                        className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-accent-500/15 border border-accent-400/30 text-accent-300 hover:bg-accent-500/25 transition-all shadow-glow"
                      >
                        <TbSparkles className="w-3.5 h-3.5" />
                        <span>Regenerate AI Explanations</span>
                      </button>
                    )}
                  </div>

                  {explanationError && (
                    <div className="p-3.5 rounded-xl bg-rose-950/40 border border-rose-500/30 text-rose-300 text-xs flex items-center space-x-2">
                      <TbAlertCircle className="w-4 h-4 flex-shrink-0" />
                      <span>{explanationError}</span>
                    </div>
                  )}

                  {/* Wrong answer cards */}
                  <div className="space-y-5">
                    {result.review.filter((r) => !r.is_correct).map((r, idx) => {
                      const expl = explanations ? explanations[idx] : null;
                      const isOpen = expandedExpl[idx] !== false; // default open
                      const qObj = quizData?.questions?.find((q) => q.id === r.question_id);
                      const allOptions = r.options || (qObj ? {
                        A: qObj.option_a,
                        B: qObj.option_b,
                        C: qObj.option_c,
                        D: qObj.option_d,
                      } : {});

                      return (
                        <div key={r.question_id} className="rounded-2xl border border-base-700/80 bg-base-900/60 overflow-hidden shadow-md">
                          {/* Question header */}
                          <div className="p-4 sm:p-5 border-b border-base-700/50 space-y-3">
                            <div className="flex items-start justify-between gap-3">
                              <p className="text-sm font-semibold text-white leading-relaxed flex-1">
                                {r.question}
                              </p>
                              {r.difficulty && (
                                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/5 border border-white/10 text-white/50 flex-shrink-0">
                                  {r.difficulty}
                                </span>
                              )}
                            </div>

                            {/* Full Options Display */}
                            <div className="space-y-2 pt-1">
                              <p className="text-[11px] font-mono uppercase tracking-wider text-white/40">
                                Options Comparison:
                              </p>
                              <div className="space-y-2">
                                {['A', 'B', 'C', 'D'].map((letter) => {
                                  const text = allOptions[letter];
                                  if (!text) return null;

                                  const isUserChoice = r.your_answer === letter;
                                  const isCorrectChoice = r.correct_answer === letter;

                                  let optionCardStyle = 'bg-base-950/40 border-base-800 text-white/60';
                                  let badge = null;

                                  if (isCorrectChoice) {
                                    optionCardStyle = 'bg-emerald-950/30 border-emerald-500/50 text-emerald-200';
                                    badge = (
                                      <span className="ml-auto inline-flex items-center space-x-1 text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-400/30 font-semibold flex-shrink-0">
                                        <TbCheck className="w-3 h-3" />
                                        <span>Correct Answer</span>
                                      </span>
                                    );
                                  } else if (isUserChoice) {
                                    optionCardStyle = 'bg-rose-950/30 border-rose-500/50 text-rose-200';
                                    badge = (
                                      <span className="ml-auto inline-flex items-center space-x-1 text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-400/30 font-semibold flex-shrink-0">
                                        <TbX className="w-3 h-3" />
                                        <span>Your Choice</span>
                                      </span>
                                    );
                                  }

                                  return (
                                    <div
                                      key={letter}
                                      className={`p-3 rounded-xl border flex items-start space-x-3 transition-colors ${optionCardStyle}`}
                                    >
                                      <span className={`w-5 h-5 rounded-md flex items-center justify-center font-mono text-[10px] flex-shrink-0 mt-0.5 font-bold ${
                                        isCorrectChoice
                                          ? 'bg-emerald-500 text-base-950'
                                          : isUserChoice
                                          ? 'bg-rose-500 text-white'
                                          : 'bg-base-800 text-white/40'
                                      }`}>
                                        {letter}
                                      </span>
                                      <span className="flex-1 text-xs break-words whitespace-normal leading-relaxed">
                                        {text}
                                      </span>
                                      {badge}
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          </div>

                          {/* AI Explanation Panel */}
                          <div className="bg-accent-950/20 border-t border-accent-500/20">
                            <button
                              type="button"
                              onClick={() => setExpandedExpl((prev) => ({ ...prev, [idx]: !isOpen }))}
                              className="w-full flex items-center justify-between px-4 sm:px-5 py-3 hover:bg-accent-950/30 transition-colors text-left"
                            >
                              <div className="flex items-center space-x-2 text-accent-300">
                                <TbBulb className="w-4 h-4 text-accent-400 flex-shrink-0" />
                                <span className="text-xs font-bold uppercase tracking-wide">
                                  AI Conceptual Explanation & Misconception Breakdown
                                </span>
                              </div>
                              {isOpen ? (
                                <TbChevronUp className="w-4 h-4 text-accent-400" />
                              ) : (
                                <TbChevronDown className="w-4 h-4 text-accent-400" />
                              )}
                            </button>

                            {isOpen && (
                              <div className="px-4 sm:px-5 pb-4 pt-1 border-t border-accent-500/10">
                                {expl ? (
                                  <div className="text-xs text-white/85 leading-relaxed whitespace-pre-line space-y-2 bg-base-950/50 p-4 rounded-xl border border-accent-400/20">
                                    {expl.explanation}
                                  </div>
                                ) : loadingExplanations ? (
                                  <div className="space-y-2 py-3">
                                    <div className="flex items-center space-x-2 text-xs text-accent-300 font-mono">
                                      <TbLoader2 className="w-3.5 h-3.5 animate-spin" />
                                      <span>Gemini is analyzing the question and formulating technical insights...</span>
                                    </div>
                                    <div className="h-3 bg-accent-400/10 rounded animate-pulse w-full" />
                                    <div className="h-3 bg-accent-400/10 rounded animate-pulse w-3/4" />
                                  </div>
                                ) : (
                                  <p className="text-xs text-white/50 py-2">
                                    No explanation generated. Click 'Regenerate AI Explanations' above.
                                  </p>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* All correct — perfect score */}
              {Array.isArray(result.review) && wrongCount === 0 && (
                <div className="p-5 rounded-2xl bg-emerald-950/20 border border-emerald-500/30 text-center text-xs text-emerald-300 space-y-1">
                  <div className="text-sm font-bold text-emerald-200">🎉 Outstanding Mastery!</div>
                  <p>All answers were correct. Your verified proficiency score has been updated in your profile.</p>
                </div>
              )}

              <div className="pt-2 text-center">
                <button
                  onClick={onClose}
                  className="btn-primary max-w-xs mx-auto text-xs py-3 px-8 shadow-glow"
                >
                  Done & Close Review
                </button>
              </div>
            </div>
          )}

          {/* Active Quiz Questions Taking View */}
          {!loading && !result && quizData && (
            <div className="space-y-6">
              <div className="flex items-center justify-between text-xs text-white/40 border-b border-base-800 pb-3">
                <span className="font-mono">{quizData.questions?.length || 0} Total Questions</span>
                <span>Select the single best answer for each question</span>
              </div>

              {quizData.questions?.map((q, qIndex) => (
                <div key={q.id} className="surface p-5 rounded-2xl space-y-4 border border-base-700/60">
                  <div className="flex items-start space-x-3">
                    <span className="w-6 h-6 rounded-full bg-accent-500/20 border border-accent-400/40 text-accent-300 text-xs flex items-center justify-center font-mono flex-shrink-0 mt-0.5 font-bold">
                      {qIndex + 1}
                    </span>
                    <p className="text-sm font-semibold text-white leading-relaxed flex-1">
                      {q.question}
                    </p>
                  </div>

                  {/* Options List - FULL TEXT VISIBLE, NO TRUNCATION */}
                  <div className="space-y-2.5 pt-1">
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
                          className={`w-full flex items-start p-3.5 rounded-xl border text-left transition-all ${
                            isSelected
                              ? 'bg-accent-500/20 border-accent-400/80 text-white shadow-glow'
                              : 'bg-base-900/60 border-base-700/60 text-white/80 hover:bg-white/5 hover:text-white'
                          }`}
                        >
                          <span className={`w-5 h-5 rounded-md flex items-center justify-center font-mono text-[11px] mr-3 flex-shrink-0 mt-0.5 ${
                            isSelected
                              ? 'bg-accent-400 text-base-950 font-bold'
                              : 'bg-base-800 text-white/50'
                          }`}>
                            {letter}
                          </span>
                          <span className="flex-1 break-words whitespace-normal leading-relaxed text-xs">
                            {optText}
                          </span>
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
          <div className="px-6 py-4 border-t border-base-700/60 flex items-center justify-between bg-base-950/60">
            <span className="text-xs text-white/50 font-mono">
              {Object.keys(answers).length} of {quizData?.questions?.length || 0} questions answered
            </span>
            <div className="flex space-x-3">
              <button onClick={onClose} className="btn-ghost text-xs py-2 px-4">
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                disabled={submitting || !quizData || (quizData.questions || []).some((q) => !answers[q.id])}
                className="btn-primary text-xs py-2 px-6 shadow-glow disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {submitting ? 'Scoring Answers...' : 'Submit Answers'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
