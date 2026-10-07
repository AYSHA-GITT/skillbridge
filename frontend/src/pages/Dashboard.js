import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import AppLayout from '../components/AppLayout';
import api from '../services/api';
import skillService from '../services/skillService';
import {
  TbTarget,
  TbFileUpload,
  TbUserCheck,
  TbRoute,
  TbCoin,
  TbAward,
  TbArrowRight,
  TbChartRadar,
  TbClipboardCheck,
  TbSparkles,
  TbShieldCheck,
  TbBriefcase,
  TbInfoCircle
} from 'react-icons/tb';

export default function Dashboard() {
  const navigate = useNavigate();
  const [student, setStudent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [topCareer, setTopCareer] = useState(null);
  const [careerDetailsOpen, setCareerDetailsOpen] = useState(false);
  const [privacyDetailsOpen, setPrivacyDetailsOpen] = useState(false);

  useEffect(() => {
    Promise.all([
      api.get('/auth/me'),
      skillService.getCareerRecommendations().catch(() => ({}))
    ])
      .then(([meRes, recsRes]) => {
        setStudent(meRes.data.student);
        if (recsRes.top_recommendation) {
          setTopCareer(recsRes.top_recommendation);
        }
      })
      .catch(() => navigate('/login'))
      .finally(() => setLoading(false));
  }, [navigate]);

  const handleSetCareer = async (e) => {
    e.preventDefault();
    const career = e.target.career.value.trim();
    if (!career) return;
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
      <div className="space-y-7">
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
          <div className="flex gap-2">
            <button
              onClick={() => navigate('/upload-resume')}
              className="btn-primary text-xs py-2.5 px-4 flex items-center justify-center space-x-2 shadow-glow"
            >
              <TbFileUpload className="w-4 h-4" />
              <span>Upload Resume</span>
            </button>
            <button
              onClick={() => navigate('/careers')}
              className="btn-ghost text-xs py-2.5 px-4 flex items-center justify-center space-x-2"
            >
              <TbBriefcase className="w-4 h-4" />
              <span>Career Recommendations</span>
            </button>
          </div>
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
                Measured against verified requirements for{' '}
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

        {/* Intelligence Cards: Progressive Disclosure with Animation */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Card 1: Career Intelligence Spotlight */}
          <div className="glass p-6 sm:p-7 rounded-3xl border border-accent-400/30 hover:border-accent-400/50 transition-all duration-300 flex flex-col justify-between relative overflow-hidden group">
            <div className="glow-teal absolute -right-8 -top-8 w-40 h-40 opacity-20 group-hover:opacity-35 transition-opacity" />

            <div className="space-y-4 relative">
              <div className="flex items-center justify-between">
                <span className="flex items-center space-x-1.5 text-xs font-semibold text-accent-300 bg-accent-500/15 px-3 py-1 rounded-full border border-accent-400/30">
                  <TbSparkles className="w-3.5 h-3.5" />
                  <span>Career Intelligence</span>
                </span>
                <span className="text-xs font-mono text-emerald-400 font-semibold bg-emerald-500/10 px-2.5 py-1 rounded-lg border border-emerald-500/20">
                  ₹{topCareer?.estimated_salary_lpa || '6-12'} LPA
                </span>
              </div>

              <div>
                <span className="text-[11px] font-mono uppercase tracking-wider text-white/40">
                  Top Matched Track
                </span>
                <h3 className="font-heading text-2xl font-bold text-white mt-0.5">
                  {topCareer?.career || 'Data Analyst'}
                </h3>
                <p className="text-xs text-white/60 mt-1 line-clamp-2">
                  {topCareer?.recommendation_reason || 'Strong baseline match grounded in your verified technical skills.'}
                </p>
              </div>

              {/* Essential Progress Bar */}
              <div className="space-y-1.5 pt-1">
                <div className="flex justify-between text-xs">
                  <span className="text-white/50">Skill Match Level</span>
                  <span className="font-mono font-bold text-accent-300">
                    {topCareer?.match_percentage || 0}%
                  </span>
                </div>
                <div className="w-full h-2 rounded-full bg-base-800 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-accent-400 to-teal-500 transition-all duration-700"
                    style={{ width: `${topCareer?.match_percentage || 0}%` }}
                  />
                </div>
              </div>

              {/* Click to expand details */}
              {careerDetailsOpen && (
                <div className="surface p-4 rounded-2xl border border-base-700/80 space-y-2.5 animate-slide-up text-xs">
                  <div className="flex items-center space-x-1.5 font-semibold text-accent-300">
                    <TbInfoCircle className="w-4 h-4" />
                    <span>Why This Match:</span>
                  </div>
                  <ul className="text-white/70 space-y-1 pl-1 text-[11px]">
                    {topCareer?.explanation?.highlights?.map((h, i) => (
                      <li key={i} className="flex items-center space-x-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-accent-400" />
                        <span>{h}</span>
                      </li>
                    ))}
                  </ul>
                  {topCareer?.explanation?.action_recommendation && (
                    <p className="text-emerald-400 font-medium pt-1 border-t border-base-700/60 text-[11px]">
                      🎯 {topCareer.explanation.action_recommendation}
                    </p>
                  )}
                </div>
              )}
            </div>

            {/* Bottom Actions */}
            <div className="pt-5 mt-5 border-t border-base-800/80 flex items-center justify-between relative">
              <button
                type="button"
                onClick={() => setCareerDetailsOpen(!careerDetailsOpen)}
                className="text-xs text-accent-400 hover:text-accent-300 font-semibold underline underline-offset-4 flex items-center space-x-1"
              >
                <span>{careerDetailsOpen ? 'Hide Details ▲' : 'View Match Details ▼'}</span>
              </button>

              <button
                onClick={() => navigate('/careers')}
                className="btn-primary text-xs py-2 px-3.5 flex items-center space-x-1 shadow-glow"
              >
                <span>All Careers</span>
                <TbArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Card 2: Informational Privacy-Preserving Intelligence */}
          <div className="glass p-6 sm:p-7 rounded-3xl border border-teal-500/30 hover:border-teal-500/50 transition-all duration-300 flex flex-col justify-between relative overflow-hidden group">
            <div className="glow-teal absolute -left-8 -top-8 w-40 h-40 opacity-20 group-hover:opacity-35 transition-opacity" />

            <div className="space-y-4 relative">
              <div className="flex items-center justify-between">
                <span className="flex items-center space-x-1.5 text-xs font-semibold text-emerald-300 bg-emerald-500/15 px-3 py-1 rounded-full border border-emerald-500/30">
                  <TbShieldCheck className="w-3.5 h-3.5" />
                  <span>Privacy-Preserving Intelligence</span>
                </span>
                <span className="text-[11px] font-mono text-teal-300 bg-teal-500/10 px-2.5 py-1 rounded-lg border border-teal-400/20">
                  Data Sovereignty
                </span>
              </div>

              <div>
                <h3 className="font-heading text-xl font-bold text-white mt-0.5">
                  Your Career Data Is Protected
                </h3>
                <p className="text-xs text-white/60 mt-1">
                  Your career data is protected using privacy-preserving learning techniques.
                </p>
              </div>

              {/* Four Guarantees */}
              <div className="space-y-2 pt-1 text-xs text-white/80">
                <div className="flex items-center space-x-2">
                  <span className="text-emerald-400 font-bold">✓</span>
                  <span>Raw training data remains local</span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-emerald-400 font-bold">✓</span>
                  <span>Model updates are shared</span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-emerald-400 font-bold">✓</span>
                  <span>Federated aggregation is used</span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-emerald-400 font-bold">✓</span>
                  <span>Differential Privacy provides additional protection</span>
                </div>
              </div>

              {/* Click to expand details */}
              {privacyDetailsOpen && (
                <div className="surface p-4 rounded-2xl border border-teal-500/30 space-y-2 animate-slide-up text-[11px] text-white/70">
                  <p>🔒 <strong className="text-white">Local Data Sovereignty:</strong> Academic records and resumes never leave your university or browser.</p>
                  <p>⚡ <strong className="text-white">Federated Averaging:</strong> Algorithms train only on numerical weights, never sharing raw documents.</p>
                  <p>🛡️ <strong className="text-white">Differential Privacy:</strong> Calibrated Gaussian perturbation bounds mathematical privacy without compromising quality.</p>
                </div>
              )}
            </div>

            {/* Bottom Actions (Informational Only) */}
            <div className="pt-5 mt-5 border-t border-base-800/80 flex items-center justify-between relative">
              <button
                type="button"
                onClick={() => setPrivacyDetailsOpen(!privacyDetailsOpen)}
                className="text-xs text-emerald-400 hover:text-emerald-300 font-semibold underline underline-offset-4 flex items-center space-x-1"
              >
                <span>{privacyDetailsOpen ? 'Hide Security Details ▲' : 'Learn More ▼'}</span>
              </button>

              <span className="text-[11px] text-teal-300/60 font-mono">
                Institutional Compute Layer
              </span>
            </div>
          </div>
        </div>

        {/* Target Career & Quick Actions Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div className="glass p-6 rounded-2xl flex flex-col justify-between">
            <div>
              <div className="flex items-center space-x-2 text-white/40 text-xs mb-1">
                <TbTarget className="w-4 h-4 text-accent-400" />
                <span>Active Target Track</span>
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
                  Compare Career Demands
                </button>
              </div>
            )}
          </div>

          <div className="glass p-6 rounded-2xl flex flex-col justify-between space-y-4">
            <div>
              <span className="text-white/40 text-xs">Platform Modules</span>
              <h3 className="font-heading text-lg font-bold text-white mt-1">
                Quick Navigation
              </h3>
              <p className="text-xs text-white/50 mt-1">
                Verify detected skills, check salary simulations, or explore learning roadmaps.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-2">
              <button
                onClick={() => navigate('/profile')}
                className="surface p-3 rounded-xl text-left hover:border-accent-400/40 transition-all flex items-center space-x-2 text-xs"
              >
                <TbUserCheck className="w-4 h-4 text-accent-400 flex-shrink-0" />
                <span className="truncate">Verified Profile</span>
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