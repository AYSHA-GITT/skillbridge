import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import AppLayout from '../components/AppLayout';
import { ProgressTrendLine } from '../components/Charts';
import ProgressBar from '../components/ProgressBar';
import AlertBanner from '../components/AlertBanner';
import skillService from '../services/skillService';
import {
  TbTrendingUp,
  TbRoute
} from 'react-icons/tb';

export default function Progress() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    skillService.getProgressHistory()
      .then((res) => setData(res))
      .catch(() => setError('Failed to load progress history.'))
      .finally(() => setLoading(false));
  }, []);

  const snapshots = data?.snapshots || [];
  const latestSnapshot = snapshots[snapshots.length - 1];

  return (
    <AppLayout>
      <div className="space-y-6">
        <div>
          <h1 className="font-heading text-2xl font-bold text-white">
            Progress & Milestones
          </h1>
          <p className="text-white/50 text-sm mt-1">
            Track your journey from initial resume upload to job-ready candidate over time.
          </p>
        </div>

        {error && <AlertBanner type="error" message={error} onClose={() => setError('')} />}

        {loading ? (
          <div className="py-16 text-center text-white/40">
            <div className="inline-block w-8 h-8 border-2 border-accent-400/30 border-t-accent-400 rounded-full animate-spin mb-3" />
            <p className="text-sm">Loading historical velocity...</p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Stat Highlights */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="glass p-5 rounded-2xl">
                <span className="text-white/40 text-xs">Roadmap Days Completed</span>
                <p className="font-heading text-3xl font-bold text-white mt-1">
                  {data?.completed_days || 0} / {data?.total_roadmap_days || 0}
                </p>
                <div className="mt-3">
                  <ProgressBar value={data?.roadmap_completion_pct || 0} showPercentage={false} />
                </div>
              </div>

              <div className="glass p-5 rounded-2xl">
                <span className="text-white/40 text-xs">Verified Skills Proven</span>
                <p className="font-heading text-3xl font-bold text-emerald-400 mt-1">
                  {latestSnapshot?.verified_skill_count || 0}
                </p>
                <p className="text-[11px] text-white/40 mt-1">Total skills: {latestSnapshot?.skill_count || 0}</p>
              </div>

              <div className="glass p-5 rounded-2xl">
                <span className="text-white/40 text-xs">Remaining Gaps to Close</span>
                <p className="font-heading text-3xl font-bold text-amber-400 mt-1">
                  {latestSnapshot?.skill_gap_count || 0}
                </p>
                <p className="text-[11px] text-white/40 mt-1">Decreases as roadmap advances</p>
              </div>
            </div>

            {/* Historical Growth Chart */}
            <div className="glass p-6 rounded-2xl">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-2">
                  <TbTrendingUp className="w-5 h-5 text-accent-400" />
                  <h3 className="font-heading font-semibold text-white text-base">
                    Readiness Trajectory
                  </h3>
                </div>
                <span className="text-xs font-mono text-white/40">
                  {snapshots.length} Snapshots Recorded
                </span>
              </div>
              <div className="pt-2">
                <ProgressTrendLine snapshots={snapshots} />
              </div>
            </div>

            {/* Quick Action to Continue Learning */}
            <div className="surface p-6 rounded-2xl flex flex-col sm:flex-row items-center justify-between gap-4 border-accent-400/20">
              <div>
                <h4 className="font-heading font-semibold text-white text-base">
                  Keep your momentum going!
                </h4>
                <p className="text-xs text-white/50 mt-0.5">
                  Complete today's suggested roadmap topic to raise your readiness score.
                </p>
              </div>
              <button
                onClick={() => navigate('/roadmap')}
                className="btn-primary text-xs py-2.5 px-5 flex items-center space-x-1.5 whitespace-nowrap"
              >
                <TbRoute className="w-4 h-4" />
                <span>Open Roadmap</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
