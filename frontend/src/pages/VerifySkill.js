import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../services/api';

export default function VerifySkill() {
  const { skillId } = useParams();
  const navigate = useNavigate();

  const [stage, setStage] = useState('loading'); // loading | quiz | submitting | result | error
  const [quiz, setQuiz] = useState(null);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get(`/student/get_quiz/${skillId}`)
      .then((res) => {
        setQuiz(res.data);
        setStage('quiz');
      })
      .catch((err) => {
        setError(err.response?.data?.error || 'Could not load quiz');
        setStage('error');
      });
  }, [skillId]);

  const selectAnswer = (questionId, optionLetter) => {
    setAnswers({ ...answers, [questionId]: optionLetter });
  };

  const allAnswered = quiz && quiz.questions.every((q) => answers[q.id]);

  const handleSubmit = async () => {
    setStage('submitting');
    try {
      const res = await api.post(`/student/submit_quiz/${skillId}`, { answers });
      setResult(res.data);
      setStage('result');
    } catch (err) {
      setError(err.response?.data?.error || 'Submission failed');
      setStage('error');
    }
  };

  const optionLetters = ['A', 'B', 'C', 'D'];

  return (
    <div className="min-h-screen px-6 py-10 max-w-2xl mx-auto">
      <button
        onClick={() => navigate(-1)}
        className="text-white/40 hover:text-white text-sm mb-6"
      >
        ← Back
      </button>

      <div className="glass p-8">
        {stage === 'loading' && (
          <div className="text-center py-12">
            <div className="inline-block w-8 h-8 border-2 border-accent-400/30 border-t-accent-400 rounded-full animate-spin mb-4" />
            <p className="text-white/60">Preparing your quiz...</p>
          </div>
        )}

        {stage === 'error' && (
          <div className="text-center py-12">
            <p className="text-red-400 mb-2">Something went wrong</p>
            <p className="text-white/40 text-sm">{error}</p>
          </div>
        )}

        {(stage === 'quiz' || stage === 'submitting') && quiz && (
          <>
            <h1 className="font-heading text-2xl font-semibold mb-1 capitalize">
              {quiz.skill_name} verification
            </h1>
            <p className="text-white/50 text-sm mb-8">
              {quiz.question_count} questions · Answer honestly for an accurate score
            </p>

            <div className="space-y-6">
              {quiz.questions.map((q, idx) => (
                <div key={q.id} className="border-b border-white/10 pb-6 last:border-0">
                  <p className="font-medium mb-3">
                    {idx + 1}. {q.question}
                  </p>
                  <div className="grid grid-cols-1 gap-2">
                    {optionLetters.map((letter) => {
                      const optionText = q[`option_${letter.toLowerCase()}`];
                      const selected = answers[q.id] === letter;
                      return (
                        <button
                          key={letter}
                          onClick={() => selectAnswer(q.id, letter)}
                          className={`text-left px-4 py-3 rounded-xl border transition-all text-sm
                            ${selected
                              ? 'bg-accent-500/15 border-accent-400/50 text-accent-300'
                              : 'bg-white/5 border-white/10 text-white/70 hover:border-white/20'}`}
                        >
                          <span className="font-medium mr-2">{letter}.</span>
                          {optionText}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>

            <button
              onClick={handleSubmit}
              disabled={!allAnswered || stage === 'submitting'}
              className="btn-primary mt-8 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {stage === 'submitting' ? 'Scoring...' : 'Submit Answers'}
            </button>
          </>
        )}

        {stage === 'result' && result && (
          <div className="text-center py-8">
            <p className="text-white/50 text-sm mb-2">Verification complete</p>
            <p className="font-heading text-5xl font-semibold text-accent-400 mb-4">
              {Math.round(result.verification_score * 100)}%
            </p>
            <p className="text-white/60 text-sm mb-1">
              You got {result.correct_count} out of {result.total_questions} correct
              ({result.quiz_score_percent}%)
            </p>
            <p className="text-white/40 text-xs mb-8">
              This score combines your quiz performance with resume evidence strength
            </p>
            <button onClick={() => navigate('/dashboard')} className="btn-primary">
              Back to Dashboard
            </button>
          </div>
        )}
      </div>
    </div>
  );
}