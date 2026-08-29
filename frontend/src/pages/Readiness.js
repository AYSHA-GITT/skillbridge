import React, { useState, useEffect } from 'react';
import AppLayout from '../components/AppLayout';
import { ReadinessRadar } from '../components/Charts';
import ProgressBar from '../components/ProgressBar';
import AlertBanner from '../components/AlertBanner';
import skillService from '../services/skillService';
import { TbChartRadar, TbBulb } from 'react-icons/tb';

export default function Readiness() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    skillService.getReadinessBreakdown()
      .then((res) => setData(res))
      .catch((err) => setError(err.response?.data?.error || 'Failed to load readiness.'))
      .finally(() => setLoading(false));
  }, []);

  const readiness = data?.readiness;
  const breakdown = readiness?.breakdown;
  const score = readiness?.readiness_score ?? 0;

  return (
    <AppLayout>
      <div className="space-y-6">
        <div>
          <h1 className="font-heading text-2xl font-bold text-white">
            Career Readiness Breakdown
          </h1>
          <p className="text-white/50 text-sm mt-1">
            Multi-dimensional evaluation of your real-world readiness for{' '}
            <span className="text-accent-400 capitalize">{data?.career || 'Target Role'}</span>.
          </p>
        </div>

        {error && <AlertBanner type="error" message={error} onClose={() => setError('')} />}

        {loading ? (
          <div className="py-16 text-center text-white/40">
            <div className="inline-block w-8 h-8 border-2 border-accent-400/30 border-t-accent-400 rounded-full animate-spin mb-3" />
            <p className="text-sm">Calculating multi-factor readiness score...</p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Top Score Banner */}
            <div className="glass p-6 rounded-3xl relative overflow-hidden flex flex-col md:flex-row items-center justify-between gap-6">
              <div className="glow-teal absolute -left-12 -top-12 w-48 h-48 opacity-25" />
              <div className="space-y-2 text-center md:text-left">
                <span className="text-xs font-mono uppercase tracking-wider text-accent-400">
                  Target: {data?.career}
                </span>
                <h2 className="font-heading text-5xl sm:text-6xl font-bold text-white tracking-tight">
                  {score}%
                </h2>
                <div className="flex items-center space-x-2 justify-center md:justify-start pt-1">
                  <span className="px-3 py-1 rounded-full text-xs font-semibold bg-accent-500/20 text-accent-300 border border-accent-400/40">
                    Tier: {readiness?.tier || 'Candidate'}
                  </span>
                  <span className="text-xs text-white/40">Weighted Composite</span>
                </div>
              </div>

              {/* Progress bars breakdown */}
              <div className="w-full md:w-80 space-y-3 bg-base-900/60 p-4 rounded-2xl border border-base-700/60">
                <ProgressBar
                  label="Required Skills (50%)"
                  value={breakdown?.required_skills_pct || 0}
                  colorGradient="from-accent-400 to-teal-500"
                />
                <ProgressBar
                  label="Quiz Proficiency (30%)"
                  value={breakdown?.quiz_proficiency_pct || 0}
                  colorGradient="from-emerald-400 to-teal-400"
                />
                <ProgressBar
                  label="Nice to Have (20%)"
                  value={breakdown?.nice_to_have_pct || 0}
                  colorGradient="from-cyan-400 to-blue-500"
                />
              </div>
            </div>

            {/* Radar & Recommendations Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Radar Chart */}
              <div className="glass p-6 rounded-2xl flex flex-col justify-between">
                <div className="flex items-center space-x-2 mb-4">
                  <TbChartRadar className="w-5 h-5 text-accent-400" />
                  <h3 className="font-heading font-semibold text-white text-base">
                    Competency vs Industry Benchmark
                  </h3>
                </div>
                <div className="py-2">
                  <ReadinessRadar />
                </div>
                <p className="text-[11px] text-white/40 text-center mt-2">
                  Dashed line shows the expected profile for junior to mid-level roles.
                </p>
              </div>

              {/* Actionable Recommendations */}
              <div className="glass p-6 rounded-2xl flex flex-col justify-between space-y-4">
                <div className="flex items-center space-x-2">
                  <TbBulb className="w-5 h-5 text-amber-400" />
                  <h3 className="font-heading font-semibold text-white text-base">
                    High-Impact Action Plan
                  </h3>
                </div>

                <div className="space-y-3">
                  {readiness?.recommendations?.map((rec, idx) => (
                    <div key={idx} className="surface p-3.5 rounded-xl flex items-start space-x-3 text-xs text-white/80 leading-relaxed">
                      <span className="w-5 h-5 rounded-full bg-accent-500/20 text-accent-400 font-mono flex items-center justify-center flex-shrink-0 mt-0.5">
                        {idx + 1}
                      </span>
                      <span>{rec}</span>
                    </div>
                  ))}

                  {(!readiness?.recommendations || readiness.recommendations.length === 0) && (
                    <p className="text-xs text-white/40">
                      Keep completing your personalized daily roadmap to sustain this level.
                    </p>
                  )}
                </div>

                <div className="pt-2 border-t border-base-800 flex items-center justify-between text-xs text-white/40">
                  <span>Privacy Mode: Active</span>
                  <span className="text-accent-400">Differential Privacy Guaranteed</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
