import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import AppLayout from '../components/AppLayout';
import ProgressBar from '../components/ProgressBar';
import AlertBanner from '../components/AlertBanner';
import skillService from '../services/skillService';
import { TbTarget, TbCheck, TbRoute } from 'react-icons/tb';

export default function SkillGap() {
  const navigate = useNavigate();
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [customCareer, setCustomCareer] = useState('');
  const [switching, setSwitching] = useState(false);

  const loadGapAnalysis = () => {
    setLoading(true);
    setError('');
    skillService.analyzeSkillGap()
      .then((data) => {
        setResult(data);
      })
      .catch((err) => {
        const msg = err.response?.data?.error || 'Unable to compute skill gap.';
        setError(msg);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadGapAnalysis();
  }, []);

  const handleUpdateCareer = async (e) => {
    e.preventDefault();
    if (!customCareer.trim()) return;
    setSwitching(true);
    setError('');
    try {
      await skillService.setTargetCareer(customCareer.trim());
      loadGapAnalysis();
      setCustomCareer('');
    } catch (err) {
      const msg = err.response?.data?.error || 'Could not update target career.';
      setError(msg);
    } finally {
      setSwitching(false);
    }
  };

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="font-heading text-2xl font-bold text-white capitalize">
              {result ? `${result.career} Gap Analysis` : 'Skill Gap Analysis'}
            </h1>
            <p className="text-white/50 text-sm mt-1">
              Strictly compares your verified competencies against industry expectations.
            </p>
          </div>

          <button
            onClick={() => navigate('/roadmap')}
            className="btn-primary text-xs py-2.5 px-4 flex items-center justify-center space-x-2 max-w-xs shadow-glow"
          >
            <TbRoute className="w-4 h-4" />
            <span>Generate / View Roadmap</span>
          </button>
        </div>

        {error && (
          <AlertBanner
            type="error"
            message={error}
            onClose={() => setError('')}
          />
        )}

        {/* Change Target Role inline form */}
        <div className="glass p-4 rounded-xl flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center space-x-2 text-white/70 text-xs">
            <TbTarget className="w-4 h-4 text-accent-400" />
            <span>Change Target Career:</span>
          </div>
          <form onSubmit={handleUpdateCareer} className="flex gap-2 w-full sm:w-auto">
            <input
              type="text"
              placeholder="e.g. Data Scientist, Cloud Engineer"
              value={customCareer}
              onChange={(e) => setCustomCareer(e.target.value)}
              className="input-field text-xs py-2 w-full sm:w-64"
            />
            <button
              type="submit"
              disabled={switching || !customCareer.trim()}
              className="btn-primary text-xs py-2 px-4 whitespace-nowrap disabled:opacity-40"
            >
              {switching ? 'Updating...' : 'Set Role'}
            </button>
          </form>
        </div>

        {loading ? (
          <div className="py-16 text-center text-white/40">
            <div className="inline-block w-8 h-8 border-2 border-accent-400/30 border-t-accent-400 rounded-full animate-spin mb-3" />
            <p className="text-sm">Calculating skill distance & requirements...</p>
          </div>
        ) : result ? (
          <div className="space-y-6">
            {/* Coverage Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="glass p-5 rounded-2xl relative overflow-hidden">
                <span className="text-white/40 text-xs">Overall Coverage</span>
                <p className="font-heading text-3xl font-bold text-accent-300 mt-1">
                  {Math.round(result.overall_coverage * 100)}%
                </p>
                <div className="mt-3">
                  <ProgressBar value={Math.round(result.overall_coverage * 100)} showPercentage={false} />
                </div>
              </div>

              <div className="glass p-5 rounded-2xl">
                <span className="text-white/40 text-xs">Core Required Skills</span>
                <p className="font-heading text-3xl font-bold text-emerald-400 mt-1">
                  {Math.round(result.required_coverage * 100)}%
                </p>
                <div className="mt-3">
                  <ProgressBar
                    value={Math.round(result.required_coverage * 100)}
                    colorGradient="from-emerald-400 to-teal-500"
                    showPercentage={false}
                  />
                </div>
              </div>

              <div className="glass p-5 rounded-2xl">
                <span className="text-white/40 text-xs">Nice-to-Have Skills</span>
                <p className="font-heading text-3xl font-bold text-teal-400 mt-1">
                  {Math.round(result.nice_to_have_coverage * 100)}%
                </p>
                <div className="mt-3">
                  <ProgressBar
                    value={Math.round(result.nice_to_have_coverage * 100)}
                    colorGradient="from-teal-400 to-cyan-500"
                    showPercentage={false}
                  />
                </div>
              </div>
            </div>

            {/* Core Required Section */}
            <div className="glass p-6 rounded-2xl space-y-4">
              <div className="flex items-center justify-between border-b border-base-700/60 pb-3">
                <div className="flex items-center space-x-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-accent-400" />
                  <h2 className="font-heading font-semibold text-lg text-white">
                    Core Required Skills
                  </h2>
                </div>
                <span className="text-xs font-mono text-white/40">
                  {result.matched_required?.length || 0} / {(result.matched_required?.length || 0) + (result.missing_required?.length || 0)} Acquired
                </span>
              </div>

              <div className="flex flex-wrap gap-2 pt-2">
                {result.matched_required?.map((s) => (
                  <span
                    key={s}
                    className="inline-flex items-center px-3 py-1.5 rounded-xl text-xs font-medium bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 capitalize"
                  >
                    <TbCheck className="w-3.5 h-3.5 mr-1.5 text-emerald-400" />
                    {s}
                  </span>
                ))}
                {result.missing_required?.map((s) => (
                  <span
                    key={s}
                    className="inline-flex items-center px-3 py-1.5 rounded-xl text-xs font-medium bg-red-500/10 text-red-300 border border-red-500/25 capitalize"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-red-400 mr-2" />
                    Missing: {s}
                  </span>
                ))}
              </div>
            </div>

            {/* Nice to have Section */}
            <div className="glass p-6 rounded-2xl space-y-4">
              <div className="flex items-center justify-between border-b border-base-700/60 pb-3">
                <div className="flex items-center space-x-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-teal-400" />
                  <h2 className="font-heading font-semibold text-lg text-white">
                    Competitive Advantage (Nice to Have)
                  </h2>
                </div>
                <span className="text-xs font-mono text-white/40">
                  {result.matched_nice_to_have?.length || 0} / {(result.matched_nice_to_have?.length || 0) + (result.missing_nice_to_have?.length || 0)} Acquired
                </span>
              </div>

              <div className="flex flex-wrap gap-2 pt-2">
                {result.matched_nice_to_have?.map((s) => (
                  <span
                    key={s}
                    className="inline-flex items-center px-3 py-1.5 rounded-xl text-xs font-medium bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 capitalize"
                  >
                    <TbCheck className="w-3.5 h-3.5 mr-1.5 text-emerald-400" />
                    {s}
                  </span>
                ))}
                {result.missing_nice_to_have?.map((s) => (
                  <span
                    key={s}
                    className="inline-flex items-center px-3 py-1.5 rounded-xl text-xs font-medium bg-white/5 text-white/40 border border-white/10 capitalize"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-white/30 mr-2" />
                    {s}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </AppLayout>
  );
}
