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
  TbNetwork,
  TbLock,
  TbCpu,
  TbBriefcase
} from 'react-icons/tb';

export default function Dashboard() {
  const navigate = useNavigate();
  const [student, setStudent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [topCareer, setTopCareer] = useState(null);
  const [flStatus, setFlStatus] = useState(null);

  useEffect(() => {
    Promise.all([
      api.get('/auth/me'),
      skillService.getCareerRecommendations().catch(() => ({})),
      skillService.getFederatedStatus().catch(() => ({}))
    ])
      .then(([meRes, recsRes, flRes]) => {
        setStudent(meRes.data.student);
        if (recsRes.top_recommendation) {
          setTopCareer(recsRes.top_recommendation);
        }
        if (flRes) {
          setFlStatus(flRes);
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

        {/* SECTION: Your Career Intelligence */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <TbSparkles className="w-5 h-5 text-accent-400" />
              <h3 className="font-heading text-lg font-bold text-white">
                Your Career Intelligence
              </h3>
            </div>
            <button
              onClick={() => navigate('/careers')}
              className="text-xs text-accent-400 hover:text-accent-300 font-semibold flex items-center space-x-1"
            >
              <span>Explore All Recommendations</span>
              <TbArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Top Recommended Career */}
            <div className="glass p-5 rounded-2xl flex flex-col justify-between border-accent-400/30">
              <div>
                <span className="text-[11px] font-mono text-accent-400 uppercase tracking-wider">
                  Top Recommended Career
                </span>
                <h4 className="font-heading text-xl font-bold text-white mt-1">
                  {topCareer?.career || 'Data Scientist'}
                </h4>
                <p className="text-xs text-white/60 mt-1 line-clamp-2">
                  {topCareer?.recommendation_reason || 'Strong baseline competency match based on verified skills.'}
                </p>
              </div>

              <div className="pt-4 mt-4 border-t border-base-800 flex items-center justify-between">
                <div>
                  <span className="text-[10px] text-white/40 block">Skill Match</span>
                  <span className="font-mono text-base font-bold text-accent-300">
                    {topCareer?.match_percentage || 0}%
                  </span>
                </div>
                <button
                  onClick={() => navigate('/careers')}
                  className="btn-primary text-xs py-1.5 px-3"
                >
                  View Track
                </button>
              </div>
            </div>

            {/* Next Recommended Skill */}
            <div className="glass p-5 rounded-2xl flex flex-col justify-between border-teal-500/30">
              <div>
                <span className="text-[11px] font-mono text-teal-400 uppercase tracking-wider">
                  Next Priority Skill
                </span>
                <h4 className="font-heading text-xl font-bold text-white mt-1 capitalize">
                  {topCareer?.explanation?.next_target_skill || 'Core Framework'}
                </h4>
                <p className="text-xs text-emerald-400 font-medium mt-1">
                  {topCareer?.explanation?.action_recommendation || 'Verifying this skill gives the highest match boost.'}
                </p>
              </div>

              <div className="pt-4 mt-4 border-t border-base-800 flex items-center justify-between">
                <div>
                  <span className="text-[10px] text-white/40 block">Projected Boost</span>
                  <span className="font-mono text-base font-bold text-emerald-400">
                    +{topCareer?.explanation?.expected_readiness_improvement || 12.5}%
                  </span>
                </div>
                <button
                  onClick={() => navigate('/roadmap')}
                  className="btn-ghost text-xs py-1.5 px-3"
                >
                  Start Learning
                </button>
              </div>
            </div>

            {/* Verified Skills Summary */}
            <div className="glass p-5 rounded-2xl flex flex-col justify-between border-base-700">
              <div>
                <span className="text-[11px] font-mono text-white/40 uppercase tracking-wider">
                  Skill Verification Status
                </span>
                <h4 className="font-heading text-xl font-bold text-white mt-1">
                  Active Proof Engine
                </h4>
                <p className="text-xs text-white/60 mt-1">
                  Only skills tested via technical assessment count toward your career readiness score.
                </p>
              </div>

              <div className="pt-4 mt-4 border-t border-base-800 flex items-center justify-between">
                <span className="text-xs text-white/40">Active Verification</span>
                <button
                  onClick={() => navigate('/profile')}
                  className="text-xs font-semibold text-accent-400 hover:text-accent-300 flex items-center space-x-1"
                >
                  <span>Verified Profile</span>
                  <TbArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* SECTION: Privacy-Preserving Career Intelligence */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <TbNetwork className="w-5 h-5 text-emerald-400" />
              <h3 className="font-heading text-lg font-bold text-white">
                Privacy-Preserving Career Intelligence
              </h3>
            </div>
            <button
              onClick={() => navigate('/federated')}
              className="text-xs text-emerald-400 hover:text-emerald-300 font-semibold flex items-center space-x-1"
            >
              <span>View Federated Center</span>
              <TbArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="surface p-5 rounded-2xl border border-base-700/80 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-emerald-400">01</span>
                <TbLock className="w-4 h-4 text-emerald-400" />
              </div>
              <h4 className="text-sm font-bold text-white">Local Data Sovereignty</h4>
              <p className="text-xs text-white/50 leading-relaxed">
                Your resume and personal performance records remain strictly on-campus inside your college node.
              </p>
            </div>

            <div className="surface p-5 rounded-2xl border border-base-700/80 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-accent-400">02</span>
                <TbCpu className="w-4 h-4 text-accent-400" />
              </div>
              <h4 className="text-sm font-bold text-white">Federated Collaborative Learning</h4>
              <p className="text-xs text-white/50 leading-relaxed">
                Institutions train models locally and aggregate model weight tensors via Flower FedAvg across rounds.
              </p>
              <div className="pt-2 text-[11px] font-mono text-accent-300">
                Round #{flStatus?.total_rounds || 4} · {flStatus?.participating_institutions || 4} Campus Nodes
              </div>
            </div>

            <div className="surface p-5 rounded-2xl border border-base-700/80 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-teal-400">03</span>
                <TbShieldCheck className="w-4 h-4 text-teal-400" />
              </div>
              <h4 className="text-sm font-bold text-white">Differential Privacy Shield</h4>
              <p className="text-xs text-white/50 leading-relaxed">
                Gaussian noise perturbation mathematically prevents individual student attribute reconstruction.
              </p>
              <div className="pt-2 text-[11px] font-mono text-teal-300">
                ε = {flStatus?.differential_privacy?.epsilon || 0.85}, δ = 1e-5
              </div>
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
                Verify detected skills, check salary simulations, or review federated privacy.
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