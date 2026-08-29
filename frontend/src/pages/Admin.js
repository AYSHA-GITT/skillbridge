import React, { useState, useEffect } from 'react';
import AppLayout from '../components/AppLayout';
import AlertBanner from '../components/AlertBanner';
import skillService from '../services/skillService';
import {
  TbUsers,
  TbFileText,
  TbChecklist,
  TbChartBar,
  TbRefresh,
  TbServer
} from 'react-icons/tb';

export default function Admin() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [training, setTraining] = useState(false);
  const [alert, setAlert] = useState(null);

  const fetchStats = () => {
    setLoading(true);
    skillService.getAdminStats()
      .then((data) => setStats(data))
      .catch(() => {
        setAlert({ type: 'error', message: 'Failed to load administrative analytics.' });
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const handleTriggerFL = async () => {
    setTraining(true);
    setAlert(null);
    try {
      const res = await skillService.triggerFLRound();
      setAlert({
        type: 'success',
        message: `Federated round ${res.data.round_number} executed successfully! Global Accuracy: ${Math.round(res.data.global_accuracy * 100)}%`,
      });
      fetchStats();
    } catch (err) {
      setAlert({
        type: 'error',
        message: err.response?.data?.error || 'Failed to trigger FL round.',
      });
    } finally {
      setTraining(false);
    }
  };

  return (
    <AppLayout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="font-heading text-2xl font-bold text-white">
              Institutional Admin Portal
            </h1>
            <p className="text-white/50 text-sm mt-1">
              Cross-institution analytics and federated training orchestrator.
            </p>
          </div>

          <button
            onClick={handleTriggerFL}
            disabled={training}
            className="btn-primary text-xs py-2.5 px-4 flex items-center space-x-2 max-w-xs shadow-glow disabled:opacity-40"
          >
            <TbRefresh className={`w-4 h-4 ${training ? 'animate-spin' : ''}`} />
            <span>{training ? 'Training Nodes...' : 'Trigger FL Aggregation'}</span>
          </button>
        </div>

        {alert && (
          <AlertBanner
            type={alert.type}
            message={alert.message}
            onClose={() => setAlert(null)}
          />
        )}

        {loading ? (
          <div className="py-16 text-center text-white/40">
            <div className="inline-block w-8 h-8 border-2 border-accent-400/30 border-t-accent-400 rounded-full animate-spin mb-3" />
            <p className="text-sm">Aggregating platform metrics...</p>
          </div>
        ) : stats ? (
          <div className="space-y-6">
            {/* Top Metric Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="glass p-5 rounded-2xl">
                <div className="flex items-center space-x-2 text-white/40 text-xs">
                  <TbUsers className="w-4 h-4 text-accent-400" />
                  <span>Enrolled Students</span>
                </div>
                <p className="font-heading text-3xl font-bold text-white mt-1">
                  {stats.total_students}
                </p>
              </div>

              <div className="glass p-5 rounded-2xl">
                <div className="flex items-center space-x-2 text-white/40 text-xs">
                  <TbFileText className="w-4 h-4 text-teal-400" />
                  <span>Resumes Processed</span>
                </div>
                <p className="font-heading text-3xl font-bold text-white mt-1">
                  {stats.total_resumes}
                </p>
              </div>

              <div className="glass p-5 rounded-2xl">
                <div className="flex items-center space-x-2 text-white/40 text-xs">
                  <TbChecklist className="w-4 h-4 text-emerald-400" />
                  <span>Verifications Logged</span>
                </div>
                <p className="font-heading text-3xl font-bold text-emerald-400 mt-1">
                  {stats.total_verifications_completed}
                </p>
              </div>

              <div className="glass p-5 rounded-2xl">
                <div className="flex items-center space-x-2 text-white/40 text-xs">
                  <TbChartBar className="w-4 h-4 text-cyan-400" />
                  <span>Avg Platform Readiness</span>
                </div>
                <p className="font-heading text-3xl font-bold text-accent-300 mt-1">
                  {stats.average_readiness}%
                </p>
              </div>
            </div>

            {/* FL Status & Top Skill Gaps Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Federated Learning Status Card */}
              <div className="glass p-6 rounded-2xl space-y-4">
                <div className="flex items-center space-x-2">
                  <TbServer className="w-5 h-5 text-accent-400" />
                  <h3 className="font-heading font-semibold text-white text-base">
                    Federated Cluster Status
                  </h3>
                </div>

                <div className="space-y-3 pt-2">
                  <div className="surface p-3 rounded-xl flex justify-between items-center text-xs">
                    <span className="text-white/60">Flower Strategy:</span>
                    <span className="font-mono text-accent-300 font-semibold">PrivacyPreservingFedAvg</span>
                  </div>
                  <div className="surface p-3 rounded-xl flex justify-between items-center text-xs">
                    <span className="text-white/60">Total Rounds Completed:</span>
                    <span className="font-mono text-white font-semibold">
                      {stats.federated_learning?.total_rounds || 0}
                    </span>
                  </div>
                  <div className="surface p-3 rounded-xl flex justify-between items-center text-xs">
                    <span className="text-white/60">Current Global Accuracy:</span>
                    <span className="font-mono text-emerald-400 font-semibold">
                      {Math.round((stats.federated_learning?.current_global_accuracy || 0.78) * 100)}%
                    </span>
                  </div>
                  <div className="surface p-3 rounded-xl flex justify-between items-center text-xs">
                    <span className="text-white/60">Participating Campus Nodes:</span>
                    <span className="font-mono text-white font-semibold">
                      {stats.federated_learning?.participating_institutions || 4}
                    </span>
                  </div>
                </div>
              </div>

              {/* Most Frequent Gaps */}
              <div className="glass p-6 rounded-2xl space-y-4">
                <div className="flex items-center space-x-2">
                  <TbChartBar className="w-5 h-5 text-amber-400" />
                  <h3 className="font-heading font-semibold text-white text-base">
                    Top Skill Gaps in Student Body
                  </h3>
                </div>

                <div className="space-y-2 pt-2">
                  {stats.top_skill_gaps?.map((gap, index) => (
                    <div key={gap.skill} className="flex items-center justify-between p-2.5 rounded-lg bg-base-900 border border-base-700/60 text-xs">
                      <div className="flex items-center space-x-2.5">
                        <span className="w-5 h-5 rounded bg-base-800 text-white/50 font-mono text-[11px] flex items-center justify-center">
                          {index + 1}
                        </span>
                        <span className="font-medium text-white capitalize">{gap.skill}</span>
                      </div>
                      <span className="text-accent-300 font-mono font-semibold">
                        {gap.count} {gap.count === 1 ? 'student' : 'students'}
                      </span>
                    </div>
                  ))}

                  {(!stats.top_skill_gaps || stats.top_skill_gaps.length === 0) && (
                    <p className="text-xs text-white/40 py-4 text-center">
                      No skill gaps recorded yet.
                    </p>
                  )}
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </AppLayout>
  );
}
