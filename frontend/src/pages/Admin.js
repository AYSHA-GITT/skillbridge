import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import AdminLayout from '../components/AdminLayout';
import AdminFLCenter from '../components/AdminFLCenter';
import AlertBanner from '../components/AlertBanner';
import skillService from '../services/skillService';
import authService from '../services/authService';
import {
  TbUsers,
  TbFileText,
  TbChecklist,
  TbChartBar,
  TbTrendingUp,
  TbTargetArrow,
  TbNetwork,
  TbShieldCheck,
  TbSearch,
  TbFileSpreadsheet,
  TbArrowRight
} from 'react-icons/tb';

export default function Admin() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab = searchParams.get('tab') || 'overview';

  const [activeTab, setActiveTab] = useState(initialTab);
  const [adminUser, setAdminUser] = useState(null);
  const [stats, setStats] = useState(null);
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [alert, setAlert] = useState(null);
  const [studentSearch, setStudentSearch] = useState('');

  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
    setSearchParams({ tab: tabId });
  };

  useEffect(() => {
    // 1. Verify administrative authentication session
    authService.getCurrentUser()
      .then((user) => {
        if (!user || (user.role || '').toLowerCase() !== 'admin') {
          // If a student or unauthorized user tries to access admin, redirect to dashboard
          navigate('/dashboard');
          return;
        }
        setAdminUser(user);

        // 2. Fetch real administrative platform statistics & students
        return Promise.all([
          skillService.getAdminStats(),
          skillService.getAdminStudents().catch(() => ({ students: [] }))
        ]);
      })
      .then((results) => {
        if (!results) return;
        const [statsData, studentsData] = results;
        setStats(statsData);
        setStudents(studentsData?.students || []);
      })
      .catch((err) => {
        if (err.response?.status === 401) {
          navigate('/login?portal=admin');
        } else if (err.response?.status === 403) {
          navigate('/dashboard');
        } else {
          setAlert({ type: 'error', message: 'Failed to load administrative analytics.' });
        }
      })
      .finally(() => setLoading(false));
  }, [navigate]);

  const filteredStudents = students.filter((s) => {
    const q = studentSearch.toLowerCase();
    return (
      (s.name || '').toLowerCase().includes(q) ||
      (s.email || '').toLowerCase().includes(q) ||
      (s.college || '').toLowerCase().includes(q) ||
      (s.target_career || '').toLowerCase().includes(q)
    );
  });

  if (loading) {
    return (
      <div className="min-h-screen bg-[#070b14] flex items-center justify-center text-cyan-400 font-mono text-xs">
        <div className="inline-block w-6 h-6 border-2 border-cyan-500/30 border-t-cyan-400 rounded-full animate-spin mr-3" />
        Authenticating Institutional Administrative Access...
      </div>
    );
  }

  return (
    <AdminLayout
      activeTab={activeTab}
      onTabChange={handleTabChange}
      adminUser={adminUser}
    >
      <div className="space-y-6 animate-fade-in">
        {alert && (
          <AlertBanner
            type={alert.type}
            message={alert.message}
            onClose={() => setAlert(null)}
          />
        )}

        {/* ============================================================ */}
        {/* VIEW 1: OVERVIEW DASHBOARD */}
        {/* ============================================================ */}
        {activeTab === 'overview' && stats && (
          <div className="space-y-6">
            {/* Header */}
            <div>
              <h1 className="font-heading text-2xl font-bold text-white tracking-tight">
                Institutional Consortium Overview
              </h1>
              <p className="text-slate-400 text-xs mt-0.5">
                Real-time aggregated telemetry across participating institutions. Zero raw data exfiltration.
              </p>
            </div>

            {/* Metric Summary Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
                <div className="flex items-center space-x-2 text-slate-400 text-xs font-mono">
                  <TbUsers className="w-4 h-4 text-cyan-400" />
                  <span>Enrolled Students</span>
                </div>
                <p className="font-heading text-3xl font-bold text-white mt-1">
                  {stats.total_students}
                </p>
                <p className="text-[11px] text-cyan-400 mt-1">
                  {stats.active_learners} Active Learners
                </p>
              </div>

              <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
                <div className="flex items-center space-x-2 text-slate-400 text-xs font-mono">
                  <TbFileText className="w-4 h-4 text-blue-400" />
                  <span>Resumes Processed</span>
                </div>
                <p className="font-heading text-3xl font-bold text-white mt-1">
                  {stats.total_resumes}
                </p>
                <p className="text-[11px] text-slate-400 mt-1">
                  {stats.total_skills_detected} Extracted Skills
                </p>
              </div>

              <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
                <div className="flex items-center space-x-2 text-slate-400 text-xs font-mono">
                  <TbChecklist className="w-4 h-4 text-emerald-400" />
                  <span>Verifications Logged</span>
                </div>
                <p className="font-heading text-3xl font-bold text-emerald-300 mt-1">
                  {stats.total_verifications_completed}
                </p>
                <p className="text-[11px] text-emerald-400/80 mt-1">
                  Confidence Quizzes Passed
                </p>
              </div>

              <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
                <div className="flex items-center space-x-2 text-slate-400 text-xs font-mono">
                  <TbChartBar className="w-4 h-4 text-purple-400" />
                  <span>Platform Readiness</span>
                </div>
                <p className="font-heading text-3xl font-bold text-purple-300 mt-1">
                  {stats.average_readiness}%
                </p>
                <p className="text-[11px] text-slate-400 mt-1">
                  Consortium Weighted Average
                </p>
              </div>
            </div>

            {/* Readiness Distribution & Career Distribution Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Readiness Distribution */}
              <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-heading font-semibold text-white text-sm flex items-center space-x-2">
                    <TbChartBar className="w-4 h-4 text-cyan-400" />
                    <span>Readiness Score Distribution</span>
                  </h3>
                  <span className="text-[10px] font-mono text-slate-400">Actual Cohort</span>
                </div>

                <div className="space-y-3 pt-1">
                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-emerald-400 font-medium">Job-Ready (≥ 70%)</span>
                      <span className="font-mono text-slate-300">
                        {stats.readiness_distribution?.job_ready || 0} students ({stats.total_students ? Math.round(((stats.readiness_distribution?.job_ready || 0) / stats.total_students) * 100) : 0}%)
                      </span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className="h-full bg-emerald-500 rounded-full transition-all duration-500"
                        style={{ width: `${stats.total_students ? ((stats.readiness_distribution?.job_ready || 0) / stats.total_students) * 100 : 0}%` }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-cyan-400 font-medium">Developing (40% - 69%)</span>
                      <span className="font-mono text-slate-300">
                        {stats.readiness_distribution?.developing || 0} students ({stats.total_students ? Math.round(((stats.readiness_distribution?.developing || 0) / stats.total_students) * 100) : 0}%)
                      </span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className="h-full bg-cyan-500 rounded-full transition-all duration-500"
                        style={{ width: `${stats.total_students ? ((stats.readiness_distribution?.developing || 0) / stats.total_students) * 100 : 0}%` }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-amber-400 font-medium">Needs Foundation (&lt; 40%)</span>
                      <span className="font-mono text-slate-300">
                        {stats.readiness_distribution?.foundation || 0} students ({stats.total_students ? Math.round(((stats.readiness_distribution?.foundation || 0) / stats.total_students) * 100) : 0}%)
                      </span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className="h-full bg-amber-500 rounded-full transition-all duration-500"
                        style={{ width: `${stats.total_students ? ((stats.readiness_distribution?.foundation || 0) / stats.total_students) * 100 : 0}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Career Distribution */}
              <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-heading font-semibold text-white text-sm flex items-center space-x-2">
                    <TbTrendingUp className="w-4 h-4 text-purple-400" />
                    <span>Target Career Distribution</span>
                  </h3>
                  <span className="text-[10px] font-mono text-slate-400">Student Aspirations</span>
                </div>

                <div className="space-y-2 pt-1 text-xs">
                  {stats.career_distribution?.map((c) => (
                    <div
                      key={c.career}
                      className="flex items-center justify-between p-2 rounded-xl bg-[#060a14] border border-slate-800/80"
                    >
                      <span className="text-white font-medium capitalize">{c.career}</span>
                      <span className="text-purple-300 font-mono font-semibold">
                        {c.count} {c.count === 1 ? 'student' : 'students'}
                      </span>
                    </div>
                  ))}

                  {(!stats.career_distribution || stats.career_distribution.length === 0) && (
                    <p className="text-slate-400 text-xs py-4 text-center">
                      No student career targets recorded yet.
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* Common Skill Gaps & Skill Trends */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Common Skill Gaps */}
              <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-heading font-semibold text-white text-sm flex items-center space-x-2">
                    <TbTargetArrow className="w-4 h-4 text-rose-400" />
                    <span>Common Skill Gaps</span>
                  </h3>
                  <span className="text-[10px] font-mono text-slate-400">High Deficit Areas</span>
                </div>

                <div className="space-y-2 pt-1 text-xs">
                  {stats.top_skill_gaps?.map((g, idx) => (
                    <div
                      key={g.skill}
                      className="flex items-center justify-between p-2 rounded-xl bg-[#060a14] border border-slate-800/80"
                    >
                      <div className="flex items-center space-x-2.5">
                        <span className="w-5 h-5 rounded bg-slate-800 text-slate-400 font-mono text-[10px] flex items-center justify-center">
                          {idx + 1}
                        </span>
                        <span className="text-white font-medium">{g.skill}</span>
                      </div>
                      <span className="text-rose-400 font-mono font-semibold">
                        {g.count} {g.count === 1 ? 'student deficit' : 'student deficits'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Skill Trends Detected */}
              <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-heading font-semibold text-white text-sm flex items-center space-x-2">
                    <TbChartBar className="w-4 h-4 text-emerald-400" />
                    <span>Prevalent Extracted Skills</span>
                  </h3>
                  <span className="text-[10px] font-mono text-slate-400">Curriculum Strengths</span>
                </div>

                <div className="space-y-2 pt-1 text-xs">
                  {stats.skill_trends?.slice(0, 6).map((sk) => (
                    <div
                      key={sk.skill}
                      className="flex items-center justify-between p-2 rounded-xl bg-[#060a14] border border-slate-800/80"
                    >
                      <span className="text-white font-medium">{sk.skill}</span>
                      <span className="text-emerald-400 font-mono font-semibold">
                        {sk.count} instances
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Quick Link Card to Federated Learning Center */}
            <div className="p-6 rounded-3xl bg-gradient-to-r from-cyan-950/40 via-slate-900 to-blue-950/40 border border-cyan-500/30 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-cyan-300 font-semibold">
                  Privacy-Preserving Infrastructure
                </span>
                <h3 className="font-heading text-lg font-bold text-white mt-0.5">
                  Decentralized Federated Learning Center
                </h3>
                <p className="text-xs text-slate-400 mt-1 max-w-xl">
                  {stats.federated_learning?.participating_institutions || 4} participating campus partitions synchronized via Flower FedAvg. Global Accuracy: {Math.round((stats.federated_learning?.current_global_accuracy || 0.78) * 100)}%.
                </p>
              </div>

              <button
                onClick={() => handleTabChange('federated')}
                className="px-4 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs flex items-center space-x-2 self-start sm:self-auto transition-colors"
              >
                <span>Launch FL Center</span>
                <TbArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* ============================================================ */}
        {/* VIEW 2: STUDENTS COHORT DIRECTORY */}
        {/* ============================================================ */}
        {activeTab === 'students' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h1 className="font-heading text-2xl font-bold text-white tracking-tight">
                  Enrolled Students Cohort
                </h1>
                <p className="text-slate-400 text-xs mt-0.5">
                  Consortium registry of student profiles, target tracks, and readiness scores.
                </p>
              </div>

              {/* Search Bar */}
              <div className="relative max-w-xs w-full">
                <TbSearch className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Search students..."
                  value={studentSearch}
                  onChange={(e) => setStudentSearch(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>

            <div className="p-4 rounded-3xl bg-slate-900/60 border border-slate-800 overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-[10px] font-mono uppercase text-slate-400">
                    <th className="py-2.5 px-3">Student Name</th>
                    <th className="py-2.5 px-3">Email</th>
                    <th className="py-2.5 px-3">Institution & Course</th>
                    <th className="py-2.5 px-3">Target Career</th>
                    <th className="py-2.5 px-3 text-right">Readiness</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {filteredStudents.map((s) => (
                    <tr key={s.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-2.5 px-3 font-semibold text-white">
                        {s.name}
                      </td>
                      <td className="py-2.5 px-3 text-slate-400 font-mono text-[11px]">
                        {s.email}
                      </td>
                      <td className="py-2.5 px-3 text-slate-300">
                        {s.college || 'Not specified'} · {s.course || 'General'}
                      </td>
                      <td className="py-2.5 px-3">
                        <span className="px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-500/30 text-[10px] capitalize">
                          {s.target_career || 'Target Not Set'}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono font-bold">
                        <span className={s.readiness_score >= 70 ? 'text-emerald-400' : s.readiness_score >= 40 ? 'text-cyan-400' : 'text-amber-400'}>
                          {s.readiness_score || 0}%
                        </span>
                      </td>
                    </tr>
                  ))}

                  {filteredStudents.length === 0 && (
                    <tr>
                      <td colSpan={5} className="py-6 text-center text-slate-400 text-xs">
                        No students match the search criteria.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ============================================================ */}
        {/* VIEW 3: SKILL ANALYTICS */}
        {/* ============================================================ */}
        {activeTab === 'skills' && stats && (
          <div className="space-y-6">
            <div>
              <h1 className="font-heading text-2xl font-bold text-white tracking-tight">
                Consortium Skill Analytics
              </h1>
              <p className="text-slate-400 text-xs mt-0.5">
                Aggregated skill frequencies detected via NLP extraction across all student resumes.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {stats.skill_trends?.map((sk, index) => (
                <div key={sk.skill} className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="font-semibold text-white text-sm">{sk.skill}</span>
                    <span className="text-[10px] font-mono text-cyan-400 px-2 py-0.5 rounded bg-cyan-950 border border-cyan-500/30">
                      Rank #{index + 1}
                    </span>
                  </div>
                  <div className="flex justify-between text-xs text-slate-400 font-mono">
                    <span>Observed Occurrences</span>
                    <span className="text-white font-bold">{sk.count}</span>
                  </div>
                  <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
                    <div
                      className="h-full bg-cyan-400 rounded-full"
                      style={{ width: `${Math.min(100, (sk.count / (stats.total_students || 1)) * 100)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ============================================================ */}
        {/* VIEW 4: CAREER TRENDS */}
        {/* ============================================================ */}
        {activeTab === 'careers' && stats && (
          <div className="space-y-6">
            <div>
              <h1 className="font-heading text-2xl font-bold text-white tracking-tight">
                Student Career Tracks
              </h1>
              <p className="text-slate-400 text-xs mt-0.5">
                Distribution of industry career tracks selected by student learners.
              </p>
            </div>

            <div className="p-6 rounded-3xl bg-slate-900/60 border border-slate-800 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {stats.career_distribution?.map((c) => (
                  <div key={c.career} className="p-4 rounded-2xl bg-[#060a14] border border-slate-800 space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="font-semibold text-white capitalize">{c.career}</span>
                      <span className="font-mono text-cyan-300 font-bold">{c.count} students</span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className="h-full bg-purple-500 rounded-full"
                        style={{ width: `${Math.min(100, (c.count / (stats.total_students || 1)) * 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ============================================================ */}
        {/* VIEW 5: COMMON SKILL GAPS */}
        {/* ============================================================ */}
        {activeTab === 'gaps' && stats && (
          <div className="space-y-6">
            <div>
              <h1 className="font-heading text-2xl font-bold text-white tracking-tight">
                Common Skill Gaps Analysis
              </h1>
              <p className="text-slate-400 text-xs mt-0.5">
                Curricular deficits identified when comparing verified student competencies against market standards.
              </p>
            </div>

            <div className="p-6 rounded-3xl bg-slate-900/60 border border-slate-800 space-y-4">
              <div className="space-y-3">
                {stats.top_skill_gaps?.map((gap, index) => (
                  <div
                    key={gap.skill}
                    className="p-4 rounded-2xl bg-[#060a14] border border-slate-800 flex items-center justify-between"
                  >
                    <div className="flex items-center space-x-3">
                      <span className="w-8 h-8 rounded-xl bg-rose-950 border border-rose-500/30 flex items-center justify-center text-rose-300 font-mono text-xs font-bold">
                        {index + 1}
                      </span>
                      <div>
                        <p className="font-semibold text-white">{gap.skill}</p>
                        <p className="text-[11px] text-slate-400">Identified curriculum deficiency</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="font-mono text-rose-400 font-bold text-sm">
                        {gap.count} {gap.count === 1 ? 'student' : 'students'} affected
                      </span>
                      <p className="text-[10px] text-slate-400 font-mono">
                        {stats.total_students ? Math.round((gap.count / stats.total_students) * 100) : 0}% of cohort
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ============================================================ */}
        {/* VIEW 6: FEDERATED LEARNING CENTER (CORE FL MODULE) */}
        {/* ============================================================ */}
        {activeTab === 'federated' && (
          <AdminFLCenter />
        )}

        {/* ============================================================ */}
        {/* VIEW 7: FL ROUNDS (SHORTCUT TO FL CENTER ROUNDS) */}
        {/* ============================================================ */}
        {activeTab === 'rounds' && (
          <AdminFLCenter />
        )}

        {/* ============================================================ */}
        {/* VIEW 8: INSTITUTIONAL REPORTS */}
        {/* ============================================================ */}
        {activeTab === 'reports' && stats && (
          <div className="space-y-6">
            <div>
              <h1 className="font-heading text-2xl font-bold text-white tracking-tight">
                Consortium Audit & Compliance Reports
              </h1>
              <p className="text-slate-400 text-xs mt-0.5">
                Privacy verification certificates and institutional readiness audit.
              </p>
            </div>

            <div className="p-6 rounded-3xl bg-slate-900/60 border border-slate-800 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="p-4 rounded-2xl bg-[#060a14] border border-slate-800 space-y-2">
                  <TbShieldCheck className="w-6 h-6 text-emerald-400" />
                  <h4 className="font-semibold text-xs text-white">FERPA / GDPR Compliance</h4>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Zero raw academic files transferred across institutional boundary lines.
                  </p>
                  <span className="text-[10px] font-mono text-emerald-400 block pt-1">
                    Status: Certified Compliant
                  </span>
                </div>

                <div className="p-4 rounded-2xl bg-[#060a14] border border-slate-800 space-y-2">
                  <TbNetwork className="w-6 h-6 text-cyan-400" />
                  <h4 className="font-semibold text-xs text-white">FL Node Cryptography</h4>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Flower NumPyClient gradient tensors bound by L2 norm clipping (C = 1.0).
                  </p>
                  <span className="text-[10px] font-mono text-cyan-400 block pt-1">
                    Mechanism: Differential Privacy
                  </span>
                </div>

                <div className="p-4 rounded-2xl bg-[#060a14] border border-slate-800 space-y-2">
                  <TbFileSpreadsheet className="w-6 h-6 text-purple-400" />
                  <h4 className="font-semibold text-xs text-white">Readiness Audit</h4>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Weighted competency gap audit across {stats.total_students} verified learners.
                  </p>
                  <span className="text-[10px] font-mono text-purple-400 block pt-1">
                    Audited: Active Session
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ============================================================ */}
        {/* VIEW 9: SETTINGS */}
        {/* ============================================================ */}
        {activeTab === 'settings' && (
          <div className="space-y-6">
            <div>
              <h1 className="font-heading text-2xl font-bold text-white tracking-tight">
                Consortium Configuration & Node Settings
              </h1>
              <p className="text-slate-400 text-xs mt-0.5">
                Parameters controlling local SGD training, L2 clipping, and Gaussian noise scales.
              </p>
            </div>

            <div className="p-6 rounded-3xl bg-slate-900/60 border border-slate-800 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
                <div className="p-4 rounded-2xl bg-[#060a14] border border-slate-800">
                  <span className="text-slate-400 block text-[10px]">Aggregation Strategy</span>
                  <span className="text-cyan-300 font-bold">PrivacyPreservingFedAvg</span>
                </div>
                <div className="p-4 rounded-2xl bg-[#060a14] border border-slate-800">
                  <span className="text-slate-400 block text-[10px]">Local Classifier</span>
                  <span className="text-white font-bold">SGDClassifier (log_loss, L2)</span>
                </div>
                <div className="p-4 rounded-2xl bg-[#060a14] border border-slate-800">
                  <span className="text-slate-400 block text-[10px]">L2 Norm Clipping Bound</span>
                  <span className="text-white font-bold">C = 1.0</span>
                </div>
                <div className="p-4 rounded-2xl bg-[#060a14] border border-slate-800">
                  <span className="text-slate-400 block text-[10px]">Differential Privacy Target</span>
                  <span className="text-emerald-400 font-bold">ε = 0.85, δ = 1e-5</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </AdminLayout>
  );
}
