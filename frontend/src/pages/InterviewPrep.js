import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import AppLayout from '../components/AppLayout';
import AlertBanner from '../components/AlertBanner';
import ProgressBar from '../components/ProgressBar';
import skillService from '../services/skillService';
import {
  startSpeechRecognition,
  speakText,
  stopSpeaking,
  isSpeechRecognitionSupported,
  isSpeechSynthesisSupported
} from '../utils/voiceUtils';
import {
  TbMicrophone,
  TbMicrophoneOff,
  TbVolume,
  TbVolumeOff,
  TbSend,
  TbSparkles,
  TbCheck,
  TbX,
  TbAlertCircle,
  TbClock,
  TbHistory,
  TbArrowRight,
  TbRotateClockwise,
  TbAward,
  TbChevronDown,
  TbChevronUp
} from 'react-icons/tb';

const CATEGORY_LABELS = {
  technical: { label: 'Technical Competency', color: 'bg-blue-500/15 text-blue-300 border-blue-500/30' },
  behavioral: { label: 'Behavioral & Situational (STAR)', color: 'bg-amber-500/15 text-amber-300 border-amber-500/30' },
  problem_solving: { label: 'Problem Solving & Architecture', color: 'bg-purple-500/15 text-purple-300 border-purple-500/30' },
  system_design: { label: 'System Design & Scalability', color: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30' },
  cultural_fit: { label: 'Cultural & Team Alignment', color: 'bg-teal-500/15 text-teal-300 border-teal-500/30' }
};

export default function InterviewPrep() {
  const [searchParams] = useSearchParams();

  // Mode: 'setup', 'interviewing', 'summary', 'history'
  const [mode, setMode] = useState('setup');
  const [alert, setAlert] = useState(null);

  // Setup Form State
  const initialRole = searchParams.get('role') || 'Full Stack Software Engineer';
  const initialJobId = searchParams.get('job_id') ? parseInt(searchParams.get('job_id'), 10) : null;
  const [targetRole, setTargetRole] = useState(initialRole);
  const jobId = initialJobId;
  const [questionCount, setQuestionCount] = useState(5);
  const [starting, setStarting] = useState(false);


  // Active Session State
  const [session, setSession] = useState(null);
  const [currentQIndex, setCurrentQIndex] = useState(0);
  const [userAnswer, setUserAnswer] = useState('');
  const [submittingAnswer, setSubmittingAnswer] = useState(false);
  const [currentEvaluation, setCurrentEvaluation] = useState(null);
  const [evaluatedAnswers, setEvaluatedAnswers] = useState([]);
  const [showSampleAnswer, setShowSampleAnswer] = useState(false);

  // Voice Interaction State
  const [isRecording, setIsRecording] = useState(false);
  const [isSpeakingQuestion, setIsSpeakingQuestion] = useState(false);
  const recognitionRef = useRef(null);
  const baseAnswerRef = useRef('');

  // Past History State
  const [historyList, setHistoryList] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [selectedHistorySession, setSelectedHistorySession] = useState(null);

  // Clean up speech synthesis on unmount
  useEffect(() => {
    return () => {
      stopSpeaking();
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, []);

  // Load Past History
  const loadHistory = useCallback(async () => {
    setLoadingHistory(true);
    try {
      const res = await skillService.getInterviewHistory();
      setHistoryList(res.history || []);
    } catch {
      setAlert({ type: 'error', message: 'Could not load interview history.' });
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  // Start Interview Flow
  const handleStartInterview = async () => {
    if (!targetRole.trim()) {
      setAlert({ type: 'warning', message: 'Please specify a target role.' });
      return;
    }

    setStarting(true);
    setAlert(null);
    try {
      const res = await skillService.startInterview({
        jobId: jobId,
        targetRole: targetRole.trim(),
        questionCount: questionCount
      });

      setSession(res?.session || res);
      setCurrentQIndex(0);
      setUserAnswer('');
      setCurrentEvaluation(null);
      setEvaluatedAnswers([]);
      setMode('interviewing');
    } catch {
      setAlert({ type: 'error', message: 'Could not generate interview questions.' });
    } finally {
      setStarting(false);
    }
  };

  // TTS: Speak question text
  const handleSpeakQuestion = (text) => {
    if (isSpeakingQuestion) {
      stopSpeaking();
      setIsSpeakingQuestion(false);
    } else {
      setIsSpeakingQuestion(true);
      speakText(
        text,
        () => setIsSpeakingQuestion(true),
        () => setIsSpeakingQuestion(false)
      );
    }
  };

  // STT: Speech to text recording
  const handleToggleRecord = () => {
    if (!isSpeechRecognitionSupported()) {
      setAlert({
        type: 'warning',
        message: 'Speech recognition is not supported in this browser. Please type your answer.'
      });
      return;
    }

    if (isRecording) {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      setIsRecording(false);
    } else {
      setIsRecording(true);
      baseAnswerRef.current = userAnswer.trim();
      recognitionRef.current = startSpeechRecognition(
        (transcript) => {
          const base = baseAnswerRef.current;
          const clean = (transcript || '').trim();
          setUserAnswer(base ? `${base} ${clean}` : clean);
        },
        (err) => {
          if (err && err !== 'no-speech') {
            setAlert({ type: 'error', message: err });
          }
          setIsRecording(false);
        },
        () => {
          setIsRecording(false);
        }
      );
    }
  };

  // Submit Answer to current question
  const handleSubmitAnswer = async () => {
    if (!userAnswer.trim()) {
      setAlert({ type: 'warning', message: 'Please type or speak an answer before submitting.' });
      return;
    }

    stopSpeaking();
    setIsSpeakingQuestion(false);
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      setIsRecording(false);
    }

    const currentQ = session?.questions?.[currentQIndex];
    if (!currentQ) return;

    setSubmittingAnswer(true);
    setAlert(null);
    try {
      const activeSessionId = session?.id || session?.session_id;
      const res = await skillService.submitInterviewAnswer({
        sessionId: activeSessionId,
        questionIndex: currentQ.question_index || (currentQIndex + 1),
        questionId: currentQ.id,
        answer: userAnswer.trim()
      });

      const evalData = res.evaluation || res;
      setCurrentEvaluation(evalData);
      setEvaluatedAnswers((prev) => [
        ...prev,
        {
          question: currentQ,
          answer: userAnswer.trim(),
          evaluation: evalData
        }
      ]);
    } catch {
      setAlert({ type: 'error', message: 'Evaluation failed. Please try again.' });
    } finally {
      setSubmittingAnswer(false);
    }
  };

  // Next Question or Finish
  const handleNextQuestion = () => {
    stopSpeaking();
    setIsSpeakingQuestion(false);
    setShowSampleAnswer(false);

    if (currentQIndex + 1 < (session?.questions?.length || 0)) {
      setCurrentQIndex((prev) => prev + 1);
      setUserAnswer('');
      setCurrentEvaluation(null);
    } else {
      setMode('summary');
    }
  };

  // Calculate session summary stats
  const calculateSummary = () => {
    if (evaluatedAnswers.length === 0) return { avgScore: 0, categoryScores: {} };

    const totalScore = evaluatedAnswers.reduce(
      (sum, item) => sum + (item.evaluation?.overall_score || 0),
      0
    );
    const avgScore = Math.round(totalScore / evaluatedAnswers.length);

    const categoryScores = {};
    evaluatedAnswers.forEach((item) => {
      const cat = item.question?.category || 'general';
      if (!categoryScores[cat]) {
        categoryScores[cat] = { total: 0, count: 0 };
      }
      categoryScores[cat].total += item.evaluation?.overall_score || 0;
      categoryScores[cat].count += 1;
    });

    return { avgScore, categoryScores };
  };

  const currentQuestion = session?.questions?.[currentQIndex];
  const catConfig = currentQuestion
    ? CATEGORY_LABELS[currentQuestion.category] || {
        label: currentQuestion.category,
        color: 'bg-base-800 text-white/70 border-base-700'
      }
    : null;

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Top Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="font-heading text-2xl font-bold text-white">
                Job-Specific Interview Simulator
              </h1>
              <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-teal-500/15 text-teal-300 border border-teal-500/30">
                4-Pillar Rubric AI
              </span>
            </div>
            <p className="text-white/50 text-sm mt-1">
              Practice realistic multi-category interviews with voice interaction, real-time rubric scoring, and missing key points feedback.
            </p>
          </div>

          <div className="flex items-center gap-2">
            {mode === 'history' ? (
              <button
                onClick={() => setMode('setup')}
                className="btn-ghost text-xs py-2 px-3 flex items-center space-x-1.5"
              >
                <span>← Back to Practice</span>
              </button>
            ) : (
              <button
                onClick={() => {
                  loadHistory();
                  setMode('history');
                }}
                className="btn-ghost text-xs py-2 px-3 flex items-center space-x-1.5"
              >
                <TbHistory className="w-4 h-4 text-accent-300" />
                <span>Session History</span>
              </button>
            )}
          </div>
        </div>

        {alert && (
          <AlertBanner
            type={alert.type}
            message={alert.message}
            onClose={() => setAlert(null)}
          />
        )}

        {/* ============================================================ */}
        {/* MODE: SETUP */}
        {/* ============================================================ */}
        {mode === 'setup' && (
          <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
            <div className="surface p-6 rounded-3xl border border-base-700/60 space-y-5">
              <div className="flex items-center space-x-3 pb-3 border-b border-base-800">
                <div className="w-10 h-10 rounded-2xl bg-accent-500/15 border border-accent-400/30 flex items-center justify-center text-accent-300">
                  <TbMicrophone className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-heading text-base font-semibold text-white">
                    Configure Interview Simulation
                  </h3>
                  <p className="text-xs text-white/50">
                    Questions are tailored to role requirements across 5 distinct evaluation categories.
                  </p>
                </div>
              </div>

              {/* Target Role Input */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-white/80">Target Role Title</label>
                <input
                  type="text"
                  value={targetRole}
                  onChange={(e) => setTargetRole(e.target.value)}
                  placeholder="e.g. Senior Backend Engineer, Data Scientist, Cloud Architect"
                  className="input-field text-xs py-2.5 px-3.5 w-full bg-base-950/80 border-base-700/80 rounded-xl text-white"
                />
                {jobId && (
                  <p className="text-[11px] text-accent-300/80 flex items-center space-x-1">
                    <TbCheck className="w-3.5 h-3.5" />
                    <span>Linked to discovered job opportunity #{jobId}</span>
                  </p>
                )}
              </div>

              {/* Question Count Selector */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-white/80">Question Count</label>
                <div className="grid grid-cols-2 gap-3">
                  {[3, 5].map((cnt) => (
                    <button
                      key={cnt}
                      type="button"
                      onClick={() => setQuestionCount(cnt)}
                      className={`p-3 rounded-xl border text-xs font-semibold transition-all ${
                        questionCount === cnt
                          ? 'bg-accent-500/15 text-accent-300 border-accent-400/50 shadow-glow'
                          : 'bg-base-950/50 text-white/60 border-base-800 hover:text-white'
                      }`}
                    >
                      {cnt} Questions {cnt === 5 ? '(Full 5 Categories)' : '(Quick Round)'}
                    </button>
                  ))}
                </div>
              </div>

              {/* Category Breakdown Callout */}
              <div className="bg-base-950/60 p-4 rounded-2xl border border-base-800 space-y-2">
                <div className="text-xs font-semibold text-white/70">5-Part Evaluation Coverage:</div>
                <div className="flex flex-wrap gap-1.5 text-[10px]">
                  {Object.values(CATEGORY_LABELS).map((cat, idx) => (
                    <span
                      key={idx}
                      className={`px-2.5 py-1 rounded-lg border font-medium ${cat.color}`}
                    >
                      {cat.label}
                    </span>
                  ))}
                </div>
              </div>

              {/* Start Button */}
              <button
                onClick={handleStartInterview}
                disabled={starting}
                className="btn-primary w-full py-3 flex items-center justify-center space-x-2 shadow-glow text-xs"
              >
                {starting ? (
                  <>
                    <div className="w-4 h-4 border-2 border-base-950/30 border-t-base-950 rounded-full animate-spin" />
                    <span>Generating Tailored Interview Questions...</span>
                  </>
                ) : (
                  <>
                    <TbMicrophone className="w-4 h-4" />
                    <span>Start Interview Practice</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* ============================================================ */}
        {/* MODE: INTERVIEWING */}
        {/* ============================================================ */}
        {mode === 'interviewing' && currentQuestion && (
          <div className="max-w-3xl mx-auto space-y-5 animate-slide-up">
            {/* Progress Top Bar */}
            <div className="surface p-4 rounded-2xl border border-base-700/60 flex items-center justify-between">
              <div className="space-y-1">
                <div className="text-xs text-white/50">
                  Question <strong className="text-white">{currentQIndex + 1}</strong> of{' '}
                  <strong className="text-white">{session?.questions?.length}</strong>
                </div>
                <div className="text-xs font-semibold text-accent-300">
                  {session?.target_role}
                </div>
              </div>

              <div className="w-36">
                <ProgressBar
                  progress={Math.round(
                    ((currentQIndex + (currentEvaluation ? 1 : 0)) /
                      (session?.questions?.length || 1)) *
                      100
                  )}
                  size="sm"
                />
              </div>
            </div>

            {/* Question Display Card */}
            <div className="surface p-6 rounded-3xl border border-base-700/60 space-y-4">
              <div className="flex items-center justify-between">
                <span className={`text-[10px] font-mono px-2.5 py-0.5 rounded-full border ${catConfig?.color}`}>
                  {catConfig?.label}
                </span>

                {isSpeechSynthesisSupported() && (
                  <button
                    onClick={() => handleSpeakQuestion(currentQuestion.question_text)}
                    className={`p-2 rounded-xl border text-xs flex items-center space-x-1.5 transition-all ${
                      isSpeakingQuestion
                        ? 'bg-rose-500/20 text-rose-300 border-rose-500/40 animate-pulse'
                        : 'border-base-700 text-white/70 hover:text-white hover:bg-white/5'
                    }`}
                    title={isSpeakingQuestion ? 'Stop audio' : 'Listen to question'}
                  >
                    {isSpeakingQuestion ? (
                      <>
                        <TbVolumeOff className="w-4 h-4" />
                        <span>Stop Voice</span>
                      </>
                    ) : (
                      <>
                        <TbVolume className="w-4 h-4" />
                        <span>Listen</span>
                      </>
                    )}
                  </button>
                )}
              </div>

              <h2 className="font-heading text-lg sm:text-xl font-bold text-white leading-snug">
                "{currentQuestion.question_text}"
              </h2>

              {currentQuestion.intent && (
                <p className="text-xs text-white/40 italic">
                  Interviewer Intent: {currentQuestion.intent}
                </p>
              )}
            </div>

            {/* Answer Input Section (if not yet submitted) */}
            {!currentEvaluation && (
              <div className="surface p-6 rounded-3xl border border-base-700/60 space-y-4">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-white/80">
                    Your Response (Type or Speak)
                  </label>

                  {/* Mic Toggle Button */}
                  {isSpeechRecognitionSupported() && (
                    <button
                      type="button"
                      onClick={handleToggleRecord}
                      className={`px-3 py-1.5 rounded-xl border text-xs flex items-center space-x-1.5 transition-all ${
                        isRecording
                          ? 'bg-rose-500/25 text-rose-300 border-rose-500/50 shadow-glow animate-pulse'
                          : 'border-teal-500/40 bg-teal-950/30 text-teal-300 hover:bg-teal-900/40'
                      }`}
                    >
                      {isRecording ? (
                        <>
                          <TbMicrophoneOff className="w-3.5 h-3.5" />
                          <span>Stop Recording</span>
                        </>
                      ) : (
                        <>
                          <TbMicrophone className="w-3.5 h-3.5" />
                          <span>Dictate Answer</span>
                        </>
                      )}
                    </button>
                  )}
                </div>

                <textarea
                  rows={6}
                  value={userAnswer}
                  onChange={(e) => setUserAnswer(e.target.value)}
                  placeholder="Structure your answer clearly. For behavioral questions, consider the STAR framework (Situation, Task, Action, Result)..."
                  className="input-field text-xs p-3.5 w-full bg-base-950/80 border-base-700/80 rounded-2xl text-white leading-relaxed resize-none focus:border-accent-400"
                  disabled={submittingAnswer}
                />

                <div className="flex justify-end">
                  <button
                    onClick={handleSubmitAnswer}
                    disabled={submittingAnswer || !userAnswer.trim()}
                    className="btn-primary text-xs py-2.5 px-5 flex items-center space-x-2 shadow-glow"
                  >
                    {submittingAnswer ? (
                      <>
                        <div className="w-3.5 h-3.5 border-2 border-base-950/30 border-t-base-950 rounded-full animate-spin" />
                        <span>Evaluating 4-Part Rubric...</span>
                      </>
                    ) : (
                      <>
                        <TbSend className="w-3.5 h-3.5" />
                        <span>Submit Answer for Evaluation</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}

            {/* Evaluation Results Card (Shown after answer submission) */}
            {currentEvaluation && (
              <div className="surface p-6 rounded-3xl border border-accent-400/30 space-y-5 animate-scale-in">
                {/* Header score */}
                <div className="flex items-center justify-between pb-3 border-b border-base-800">
                  <div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-accent-500/20 text-accent-300 border border-accent-400/30">
                      Evaluated Answer
                    </span>
                    <h3 className="font-heading text-lg font-bold text-white mt-1">
                      Performance Feedback
                    </h3>
                  </div>

                  <div className="text-right">
                    <div className="text-[10px] text-white/40">Overall Score</div>
                    <div
                      className={`font-heading text-3xl font-bold ${
                        currentEvaluation.overall_score >= 75
                          ? 'text-emerald-400'
                          : currentEvaluation.overall_score >= 50
                          ? 'text-amber-400'
                          : 'text-rose-400'
                      }`}
                    >
                      {currentEvaluation.overall_score}%
                    </div>
                  </div>
                </div>

                {/* 4 Rubric Component Scores */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
                  <div className="bg-base-950/70 p-3 rounded-xl border border-base-800 space-y-1">
                    <div className="text-[10px] text-white/40">Relevance</div>
                    <div className="font-bold text-white font-mono">
                      {currentEvaluation.rubric_scores?.relevance_score || 0}%
                    </div>
                    <ProgressBar
                      progress={currentEvaluation.rubric_scores?.relevance_score || 0}
                      size="sm"
                    />
                  </div>

                  <div className="bg-base-950/70 p-3 rounded-xl border border-base-800 space-y-1">
                    <div className="text-[10px] text-white/40">Tech Depth</div>
                    <div className="font-bold text-white font-mono">
                      {currentEvaluation.rubric_scores?.technical_depth_score || 0}%
                    </div>
                    <ProgressBar
                      progress={currentEvaluation.rubric_scores?.technical_depth_score || 0}
                      size="sm"
                    />
                  </div>

                  <div className="bg-base-950/70 p-3 rounded-xl border border-base-800 space-y-1">
                    <div className="text-[10px] text-white/40">Structure</div>
                    <div className="font-bold text-white font-mono">
                      {currentEvaluation.rubric_scores?.structure_score || 0}%
                    </div>
                    <ProgressBar
                      progress={currentEvaluation.rubric_scores?.structure_score || 0}
                      size="sm"
                    />
                  </div>

                  <div className="bg-base-950/70 p-3 rounded-xl border border-base-800 space-y-1">
                    <div className="text-[10px] text-white/40">Communication</div>
                    <div className="font-bold text-white font-mono">
                      {currentEvaluation.rubric_scores?.communication_score || 0}%
                    </div>
                    <ProgressBar
                      progress={currentEvaluation.rubric_scores?.communication_score || 0}
                      size="sm"
                    />
                  </div>
                </div>

                {/* Qualitative Feedback */}
                <div className="bg-base-950/60 p-4 rounded-2xl border border-base-800 space-y-1 text-xs">
                  <div className="font-semibold text-white/80">Evaluator Insights:</div>
                  <p className="text-white/70 leading-relaxed">
                    {currentEvaluation.feedback}
                  </p>
                </div>

                {/* Missing Points Callout */}
                {currentEvaluation.missing_points?.length > 0 && (
                  <div className="bg-rose-950/20 p-4 rounded-2xl border border-rose-500/30 space-y-2 text-xs">
                    <div className="font-semibold text-rose-300 flex items-center space-x-1.5">
                      <TbAlertCircle className="w-4 h-4 flex-shrink-0" />
                      <span>Missing Key Points:</span>
                    </div>
                    <ul className="space-y-1 pl-4 list-disc text-white/70">
                      {currentEvaluation.missing_points.map((pt, idx) => (
                        <li key={idx}>{pt}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Expandable Benchmark Model Answer */}
                {currentEvaluation.sample_ideal_answer && (
                  <div className="border border-base-800 rounded-2xl overflow-hidden text-xs">
                    <button
                      type="button"
                      onClick={() => setShowSampleAnswer(!showSampleAnswer)}
                      className="w-full bg-base-950/80 px-4 py-3 flex items-center justify-between text-white/80 hover:text-white"
                    >
                      <span className="font-semibold flex items-center space-x-1.5">
                        <TbSparkles className="w-3.5 h-3.5 text-accent-400" />
                        <span>Inspect Benchmark Model Answer</span>
                      </span>
                      {showSampleAnswer ? <TbChevronUp className="w-4 h-4" /> : <TbChevronDown className="w-4 h-4" />}
                    </button>
                    {showSampleAnswer && (
                      <div className="p-4 bg-base-950/40 text-white/70 leading-relaxed border-t border-base-800">
                        {currentEvaluation.sample_ideal_answer}
                      </div>
                    )}
                  </div>
                )}

                {/* Next Button */}
                <div className="flex justify-end pt-2">
                  <button
                    onClick={handleNextQuestion}
                    className="btn-primary text-xs py-2.5 px-5 flex items-center space-x-2 shadow-glow"
                  >
                    <span>
                      {currentQIndex + 1 < (session?.questions?.length || 0)
                        ? 'Next Question'
                        : 'Complete Session & View Summary'}
                    </span>
                    <TbArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ============================================================ */}
        {/* MODE: SUMMARY */}
        {/* ============================================================ */}
        {mode === 'summary' && (
          <div className="max-w-2xl mx-auto space-y-6 animate-scale-in">
            {(() => {
              const { avgScore, categoryScores } = calculateSummary();
              return (
                <div className="surface p-6 rounded-3xl border border-accent-400/30 space-y-6">
                  <div className="text-center space-y-2">
                    <div className="w-14 h-14 rounded-2xl bg-accent-500/15 border border-accent-400/30 flex items-center justify-center mx-auto text-accent-300">
                      <TbAward className="w-7 h-7" />
                    </div>
                    <h2 className="font-heading text-xl font-bold text-white">
                      Interview Simulation Completed
                    </h2>
                    <p className="text-xs text-white/50">
                      Target Role: <strong>{session?.target_role}</strong>
                    </p>
                  </div>

                  {/* Big Score Card */}
                  <div className="bg-base-950/80 p-5 rounded-2xl border border-base-800 text-center space-y-1">
                    <div className="text-xs text-white/40">Average Performance Score</div>
                    <div
                      className={`font-heading text-4xl font-extrabold ${
                        avgScore >= 75
                          ? 'text-emerald-400'
                          : avgScore >= 50
                          ? 'text-amber-400'
                          : 'text-rose-400'
                      }`}
                    >
                      {avgScore}%
                    </div>
                    <p className="text-[11px] text-white/50">
                      Evaluated across {evaluatedAnswers.length} multi-category competency questions.
                    </p>
                  </div>

                  {/* Category Breakdown */}
                  <div className="space-y-2 text-xs">
                    <h4 className="font-semibold text-white/80">Category Performance Breakdown</h4>
                    <div className="space-y-2">
                      {Object.entries(categoryScores).map(([cat, data]) => {
                        const score = Math.round(data.total / data.count);
                        const label = CATEGORY_LABELS[cat]?.label || cat;
                        return (
                          <div
                            key={cat}
                            className="bg-base-950/60 p-3 rounded-xl border border-base-800 space-y-1"
                          >
                            <div className="flex justify-between items-center">
                              <span className="text-white/80">{label}</span>
                              <span className="font-mono font-bold text-accent-300">{score}%</span>
                            </div>
                            <ProgressBar progress={score} size="sm" />
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-3 pt-2">
                    <button
                      onClick={() => setMode('setup')}
                      className="btn-primary text-xs py-2.5 px-4 flex-1 flex items-center justify-center space-x-1.5 shadow-glow"
                    >
                      <TbRotateClockwise className="w-4 h-4" />
                      <span>Practice Another Session</span>
                    </button>
                    <button
                      onClick={() => {
                        loadHistory();
                        setMode('history');
                      }}
                      className="btn-ghost text-xs py-2.5 px-4 flex items-center space-x-1.5"
                    >
                      <TbHistory className="w-4 h-4" />
                      <span>View History</span>
                    </button>
                  </div>
                </div>
              );
            })()}
          </div>
        )}

        {/* ============================================================ */}
        {/* MODE: HISTORY */}
        {/* ============================================================ */}
        {mode === 'history' && (
          <div className="space-y-4 animate-fade-in">
            {loadingHistory ? (
              <div className="py-16 text-center space-y-2">
                <div className="w-6 h-6 border-2 border-accent-400/30 border-t-accent-400 rounded-full animate-spin mx-auto" />
                <p className="text-xs text-white/50">Loading interview records...</p>
              </div>
            ) : historyList.length === 0 ? (
              <div className="surface p-12 text-center rounded-2xl border border-base-800 space-y-2">
                <TbHistory className="w-8 h-8 text-white/20 mx-auto" />
                <p className="text-xs text-white/60">No past interview sessions found.</p>
                <button
                  onClick={() => setMode('setup')}
                  className="btn-primary text-xs py-2 px-4 shadow-glow"
                >
                  Start Your First Interview
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {historyList.map((hist) => (
                  <div
                    key={hist.id}
                    className="surface p-5 rounded-2xl border border-base-700/60 space-y-3"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <h4 className="font-heading text-sm font-bold text-white">
                          {hist.target_role}
                        </h4>
                        <div className="text-[11px] text-white/40 flex items-center space-x-2 mt-0.5">
                          <TbClock className="w-3 h-3" />
                          <span>
                            {hist.created_at ? new Date(hist.created_at).toLocaleDateString() : 'Recent'}
                          </span>
                        </div>
                      </div>

                      <div className="text-right">
                        <span
                          className={`font-mono font-bold text-base ${
                            (hist.overall_score || 0) >= 70
                              ? 'text-emerald-400'
                              : 'text-amber-400'
                          }`}
                        >
                          {hist.overall_score || 0}%
                        </span>
                        <div className="text-[10px] text-white/40">Average</div>
                      </div>
                    </div>

                    <div className="text-xs text-white/60 flex items-center justify-between pt-2 border-t border-base-800">
                      <span>{hist.total_questions || 5} questions answered</span>
                      <button
                        onClick={async () => {
                          try {
                            const res = await skillService.getInterviewSession(hist.id);
                            setSelectedHistorySession(res.session);
                          } catch {
                            setAlert({ type: 'error', message: 'Could not load session details.' });
                          }
                        }}
                        className="text-accent-300 hover:text-accent-200 text-xs font-semibold"
                      >
                        Inspect Details →
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Session Detail Drawer / Modal */}
            {selectedHistorySession && (
              <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
                <div className="surface max-w-2xl w-full rounded-3xl border border-accent-400/30 p-6 max-h-[85vh] overflow-y-auto space-y-4 animate-scale-in">
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="font-heading text-base font-bold text-white">
                        {selectedHistorySession.target_role}
                      </h3>
                      <p className="text-xs text-white/50">
                        Average Score: {selectedHistorySession.overall_score || 0}%
                      </p>
                    </div>
                    <button
                      onClick={() => setSelectedHistorySession(null)}
                      className="p-1 rounded-lg text-white/40 hover:text-white"
                    >
                      <TbX className="w-4 h-4" />
                    </button>
                  </div>

                  <div className="space-y-3 pt-2">
                    {(selectedHistorySession.questions || []).map((q, idx) => (
                      <div
                        key={idx}
                        className="bg-base-950/70 p-3.5 rounded-xl border border-base-800 space-y-2 text-xs"
                      >
                        <div className="flex justify-between items-center">
                          <span className="font-mono text-[10px] text-accent-300 uppercase">
                            {q.category}
                          </span>
                          <span className="font-mono font-bold text-emerald-400">
                            Score: {q.overall_score || 0}%
                          </span>
                        </div>
                        <p className="font-semibold text-white">"{q.question_text}"</p>
                        {q.user_answer && (
                          <div className="text-white/60 bg-base-900/50 p-2.5 rounded-lg border border-base-800 italic">
                            Your response: "{q.user_answer}"
                          </div>
                        )}
                        {q.feedback && (
                          <p className="text-white/70 text-[11px] leading-relaxed">
                            <strong>Feedback:</strong> {q.feedback}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
