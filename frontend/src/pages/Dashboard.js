import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import AppLayout from '../components/AppLayout';
import api from '../services/api';
import {
  TbTarget,
  TbFileUpload,
  TbUserCheck,
  TbRoute,
  TbCoin,
  TbAward,
  TbArrowRight,
  TbChartRadar,
  TbClipboardCheck
} from 'react-icons/tb';

export default function Dashboard() {
  const navigate = useNavigate();
  const [student, setStudent] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/auth/me')
      .then((res) => setStudent(res.data.student))
      .catch(() => navigate('/login'))
      .finally(() => setLoading(false));
  }, [navigate]);

  const handleSetCareer = async (e) => {
    e.preventDefault();
    const career = e.target.career.value.trim();
    await api.post('/student/set_target_career', { target_career: career });
    const me = await api.get('/auth/me');
    setStudent(me.data.student);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-white/40 font-mono text-sm">
        <div className="inline-block w-6 h-6 border-2 border-accent-400/30 border-t-accent-400 rounded-full animate-spin mr-3" />
        Loading your workspace...
      </div>
    );
  }

  const score = student?.readiness_score ?? 0;

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Greeting Banner */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="font-heading text-2xl sm:text-3xl font-bold text-white">
              Welcome back, {student?.name?.split(' ')[0]}
            </h1>
            <p className="text-white/40 text-sm mt-1">
              {student?.college} · {student?.course} {student?.year ? `(${student.year})` : ''}
            </p>
          </div>
          <button
            onClick={() => navigate('/upload-resume')}
            className="btn-primary text-xs py-2.5 px-4 flex items-center justify-center space-x-2 max-w-xs shadow-glow"
          >
            <TbFileUpload className="w-4 h-4" />
            <span>Upload Resume</span>
          </button>
        </div>

        {/* Readiness Card */}
        <div className="glass p-6 sm:p-8 rounded-3xl relative overflow-hidden">
          <div className="glow-teal absolute -left-10 -top-10 w-48 h-48 opacity-30" />
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6 relative">
            <div>
              <span className="text-xs font-mono uppercase tracking-wider text-accent-400">
                Target Readiness Indicator
              </span>
              <p className="font-heading text-5xl sm:text-6xl font-bold text-white mt-1">
                {score}%
              </p>
              <p className="text-xs text-white/50 mt-1">
                Measured against required skills for{' '}
                <span className="text-accent-300 font-semibold capitalize">
                  {student?.target_career || 'Target Role'}
                </span>
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={() => navigate('/readiness')}
                className="btn-primary text-xs py-2.5 px-4 flex items-center justify-center space-x-1.5"
              >
                <TbChartRadar className="w-4 h-4" />
                <span>Readiness Breakdown</span>
              </button>
              <button
                onClick={() => navigate('/roadmap')}
                className="btn-ghost text-xs py-2.5 px-4 flex items-center justify-center space-x-1.5"
              >
                <TbRoute className="w-4 h-4" />
                <span>View Roadmap</span>
              </button>
            </div>
          </div>

          <div className="w-full h-2 rounded-full bg-base-800 border border-base-700/60 overflow-hidden mt-6 relative">
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{ width: `${score}%`, background: 'linear-gradient(90deg, #2dd4bf, #14b8a6)' }}
            />
          </div>
        </div>

        {/* Target Career & Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div className="glass p-6 rounded-2xl flex flex-col justify-between">
            <div>
              <div className="flex items-center space-x-2 text-white/40 text-xs mb-1">
                <TbTarget className="w-4 h-4 text-accent-400" />
                <span>Target Career Track</span>
              </div>

              {student?.target_career ? (
                <div>
                  <p className="font-heading text-2xl font-bold text-white capitalize mt-1">
                    {student.target_career}
                  </p>
                  <p className="text-xs text-white/50 mt-1">
                    Track your gap and access tailored tutorials.
                  </p>
                </div>
              ) : (
                <div className="mt-2">
                  <p className="text-xs text-white/50 mb-3">
                    Set a target career to get custom gap analysis and roadmaps.
                  </p>
                  <form onSubmit={handleSetCareer} className="space-y-2">
                    <input
                      name="career"
                      placeholder="e.g. Software Engineer, Data Scientist"
                      className="input-field text-xs py-2"
                    />
                    <button type="submit" className="btn-primary text-xs py-2">
                      Save Career Target
                    </button>
                  </form>
                </div>
              )}
            </div>

            {student?.target_career && (
              <div className="pt-4 border-t border-base-800 flex items-center space-x-4">
                <button
                  onClick={() => navigate('/skill-gap')}
                  className="text-xs font-semibold text-accent-400 hover:text-accent-300 flex items-center space-x-1"
                >
                  <span>Skill Gap Analysis</span>
                  <TbArrowRight className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => navigate('/careers')}
                  className="text-xs text-white/40 hover:text-white"
                >
                  Explore Other Careers
                </button>
              </div>
            )}
          </div>

          <div className="glass p-6 rounded-2xl flex flex-col justify-between space-y-4">
            <div>
              <span className="text-white/40 text-xs">Platform Modules</span>
              <h3 className="font-heading text-lg font-bold text-white mt-1">
                Continue Learning & Evaluation
              </h3>
              <p className="text-xs text-white/50 mt-1">
                Verify detected skills, check salary simulations, or review federated privacy.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-2">
              <button
                onClick={() => navigate('/profile')}
                className="surface p-3 rounded-xl text-left hover:border-accent-400/40 transition-all flex items-center space-x-2 text-xs"
              >
                <TbUserCheck className="w-4 h-4 text-accent-400 flex-shrink-0" />
                <span className="truncate">Skills Profile</span>
              </button>

              <button
                onClick={() => navigate('/assessment')}
                className="surface p-3 rounded-xl text-left hover:border-accent-400/40 transition-all flex items-center space-x-2 text-xs"
              >
                <TbClipboardCheck className="w-4 h-4 text-teal-400 flex-shrink-0" />
                <span className="truncate">Quizzes</span>
              </button>

              <button
                onClick={() => navigate('/salary-sim')}
                className="surface p-3 rounded-xl text-left hover:border-accent-400/40 transition-all flex items-center space-x-2 text-xs"
              >
                <TbCoin className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                <span className="truncate">Salary Sim</span>
              </button>

              <button
                onClick={() => navigate('/badges')}
                className="surface p-3 rounded-xl text-left hover:border-accent-400/40 transition-all flex items-center space-x-2 text-xs"
              >
                <TbAward className="w-4 h-4 text-amber-400 flex-shrink-0" />
                <span className="truncate">Badges</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}