import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

export default function SkillGapResults() {
  const navigate = useNavigate();
  const [stage, setStage] = useState('loading'); // loading | done | error | no-career
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.post('/student/analyze_skill_gap')
      .then((res) => {
        setResult(res.data);
        setStage('done');
      })
      .catch((err) => {
        const msg = err.response?.data?.error || 'Something went wrong';
        if (msg.includes('target career')) {
          setStage('no-career');
        } else {
          setError(msg);
          setStage('error');
        }
      });
  }, []);

  const CoverageBar = ({ label, value }) => (
    <div className="mb-4">
      <div className="flex justify-between text-sm mb-1.5">
        <span className="text-white/60">{label}</span>
        <span className="text-accent-400 font-medium">{Math.round(value * 100)}%</span>
      </div>
      <div className="w-full h-2 rounded-full bg-white/5 overflow-hidden">
        <div
          className="h-full bg-accent-400 rounded-full transition-all duration-700"
          style={{ width: `${value * 100}%` }}
        />
      </div>
    </div>
  );

  const SkillPill = ({ name, matched }) => (
    <span
      className={`inline-block px-3 py-1.5 rounded-lg text-sm mr-2 mb-2 capitalize
        ${matched
          ? 'bg-accent-500/15 text-accent-300 border border-accent-400/30'
          : 'bg-white/5 text-white/50 border border-white/10'}`}
    >
      {matched ? '✓ ' : '○ '}{name}
    </span>
  );

  return (
    <div className="min-h-screen px-6 py-10 max-w-3xl mx-auto">
      <button
        onClick={() => navigate('/dashboard')}
        className="text-white/40 hover:text-white text-sm mb-6"
      >
        ← Back to dashboard
      </button>

      <div className="glass p-8">
        {stage === 'loading' && (
          <div className="text-center py-12">
            <div className="inline-block w-8 h-8 border-2 border-accent-400/30 border-t-accent-400 rounded-full animate-spin mb-4" />
            <p className="text-white/60">Analyzing your skill gap...</p>
          </div>
        )}

        {stage === 'no-career' && (
          <div className="text-center py-12">
            <p className="text-white/60 mb-4">
              You haven't set a target career yet.
            </p>
            <button
              onClick={() => navigate('/dashboard')}
              className="btn-primary max-w-xs mx-auto"
            >
              Set target career on dashboard
            </button>
          </div>
        )}

        {stage === 'error' && (
          <div className="text-center py-12">
            <p className="text-red-400 mb-2">Something went wrong</p>
            <p className="text-white/40 text-sm">{error}</p>
          </div>
        )}

        {stage === 'done' && result && (
          <>
            <h1 className="font-heading text-2xl font-semibold mb-1 capitalize">
              {result.career} readiness
            </h1>
            <p className="text-white/50 text-sm mb-8">
              Based on your verified skills only
            </p>

            <div className="mb-8">
              <CoverageBar label="Overall coverage" value={result.overall_coverage} />
              <CoverageBar label="Required skills" value={result.required_coverage} />
              <CoverageBar label="Nice-to-have skills" value={result.nice_to_have_coverage} />
            </div>

            <div className="mb-6">
              <h2 className="font-heading text-lg font-semibold mb-3">
                Required skills
              </h2>
              <div>
                {result.matched_required.map((s) => (
                  <SkillPill key={s} name={s} matched={true} />
                ))}
                {result.missing_required.map((s) => (
                  <SkillPill key={s} name={s} matched={false} />
                ))}
              </div>
            </div>

            <div className="mb-8">
              <h2 className="font-heading text-lg font-semibold mb-3">
                Nice to have
              </h2>
              <div>
                {result.matched_nice_to_have.map((s) => (
                  <SkillPill key={s} name={s} matched={true} />
                ))}
                {result.missing_nice_to_have.map((s) => (
                  <SkillPill key={s} name={s} matched={false} />
                ))}
              </div>
            </div>

            <button onClick={() => navigate('/dashboard')} className="btn-primary">
              Back to Dashboard
            </button>
          </>
        )}
      </div>
    </div>
  );
}