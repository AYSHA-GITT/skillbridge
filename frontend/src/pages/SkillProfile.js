import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import AppLayout from '../components/AppLayout';
import QuizModal from '../components/QuizModal';
import AlertBanner from '../components/AlertBanner';
import skillService from '../services/skillService';
import {
  TbFileUpload,
  TbSearch,
  TbCheck,
  TbAlertTriangle,
  TbCircleX,
  TbHelpCircle,
  TbArrowRight,
  TbFileCheck,
  TbCalendar,
  TbAward
} from 'react-icons/tb';

export default function SkillProfile() {
  const navigate = useNavigate();
  const [profileData, setProfileData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('all'); // all, verified, needs_verification, needs_improvement, target_gaps
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedQuizSkill, setSelectedQuizSkill] = useState(null);
  const [alert, setAlert] = useState(null);

  const fetchProfile = () => {
    setLoading(true);
    skillService.getVerifiedSkillProfile()
      .then((data) => {
        setProfileData(data);
      })
      .catch(() => {
        setAlert({ type: 'error', message: 'Failed to load verified skills profile.' });
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  const handleQuizComplete = (res) => {
    setAlert({
      type: 'success',
      message: `Completed assessment for ${res.skill_name}! Score: ${res.quiz_score_percent}%`,
    });
    fetchProfile();
  };

  const verified = profileData?.verified_skills || [];
  const needsVerification = profileData?.needs_verification || [];
  const needsImprovement = profileData?.needs_improvement || [];
  const targetGaps = profileData?.target_career_gaps || [];

  // Flatten based on filter
  let displayedSkills = [];
  if (activeTab === 'all') {
    displayedSkills = [...verified, ...needsImprovement, ...needsVerification, ...targetGaps];
  } else if (activeTab === 'verified') {
    displayedSkills = verified;
  } else if (activeTab === 'needs_verification') {
    displayedSkills = needsVerification;
  } else if (activeTab === 'needs_improvement') {
    displayedSkills = needsImprovement;
  } else if (activeTab === 'target_gaps') {
    displayedSkills = targetGaps;
  }

  const filteredSkills = displayedSkills.filter((s) =>
    s.skill_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="font-heading text-2xl font-bold text-white">
                Verified Skill Profile
              </h1>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                Active Verification Engine
              </span>
            </div>
            <p className="text-white/50 text-sm mt-1">
              Resume-detected skills require passing an adaptive technical assessment before counting toward career readiness.
            </p>
          </div>

          <button
            onClick={() => navigate('/upload-resume')}
            className="btn-primary text-xs py-2.5 px-4 flex items-center justify-center space-x-2 max-w-xs shadow-glow"
          >
            <TbFileUpload className="w-4 h-4" />
            <span>Upload New Resume</span>
          </button>
        </div>

        {alert && (
          <AlertBanner
            type={alert.type}
            message={alert.message}
            onClose={() => setAlert(null)}
          />
        )}

        {/* 4-Tier Categorization Stats Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div
            onClick={() => setActiveTab('verified')}
            className={`glass p-4 rounded-xl cursor-pointer transition-all border ${
              activeTab === 'verified' ? 'border-emerald-400 bg-emerald-500/10' : 'hover:border-emerald-400/30'
            }`}
          >
            <div className="flex items-center justify-between text-emerald-400">
              <span className="text-xs font-semibold">1. Verified</span>
              <TbCheck className="w-4 h-4" />
            </div>
            <p className="font-heading text-2xl font-bold text-white mt-1">
              {verified.length}
            </p>
            <p className="text-[10px] text-white/40 mt-0.5">Passed quiz &ge; 70%</p>
          </div>

          <div
            onClick={() => setActiveTab('needs_verification')}
            className={`glass p-4 rounded-xl cursor-pointer transition-all border ${
              activeTab === 'needs_verification' ? 'border-amber-400 bg-amber-500/10' : 'hover:border-amber-400/30'
            }`}
          >
            <div className="flex items-center justify-between text-amber-400">
              <span className="text-xs font-semibold">2. Needs Verification</span>
              <TbHelpCircle className="w-4 h-4" />
            </div>
            <p className="font-heading text-2xl font-bold text-white mt-1">
              {needsVerification.length}
            </p>
            <p className="text-[10px] text-white/40 mt-0.5">In resume, not tested</p>
          </div>

          <div
            onClick={() => setActiveTab('needs_improvement')}
            className={`glass p-4 rounded-xl cursor-pointer transition-all border ${
              activeTab === 'needs_improvement' ? 'border-rose-400 bg-rose-500/10' : 'hover:border-rose-400/30'
            }`}
          >
            <div className="flex items-center justify-between text-rose-400">
              <span className="text-xs font-semibold">3. Needs Work</span>
              <TbCircleX className="w-4 h-4" />
            </div>
            <p className="font-heading text-2xl font-bold text-white mt-1">
              {needsImprovement.length}
            </p>
            <p className="text-[10px] text-white/40 mt-0.5">Quiz score &lt; 70%</p>
          </div>

          <div
            onClick={() => setActiveTab('target_gaps')}
            className={`glass p-4 rounded-xl cursor-pointer transition-all border ${
              activeTab === 'target_gaps' ? 'border-purple-400 bg-purple-500/10' : 'hover:border-purple-400/30'
            }`}
          >
            <div className="flex items-center justify-between text-purple-400">
              <span className="text-xs font-semibold">4. Target Gaps</span>
              <TbAlertTriangle className="w-4 h-4" />
            </div>
            <p className="font-heading text-2xl font-bold text-white mt-1">
              {targetGaps.length}
            </p>
            <p className="text-[10px] text-white/40 mt-0.5">Missing for target role</p>
          </div>
        </div>

        {/* Filter Tabs & Search */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex flex-wrap gap-1 bg-base-900 p-1 rounded-xl border border-base-700/60 w-full sm:w-auto">
            {[
              { id: 'all', label: `All (${displayedSkills.length})` },
              { id: 'verified', label: `Verified (${verified.length})` },
              { id: 'needs_verification', label: `Needs Quiz (${needsVerification.length})` },
              { id: 'needs_improvement', label: `Retake (${needsImprovement.length})` },
              { id: 'target_gaps', label: `Role Gaps (${targetGaps.length})` }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  activeTab === tab.id
                    ? 'bg-accent-500/20 text-accent-300 border border-accent-400/30 font-semibold'
                    : 'text-white/50 hover:text-white'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="relative w-full sm:w-64">
            <TbSearch className="w-4 h-4 text-white/40 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search skills..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input-field text-xs py-2 pl-9"
            />
          </div>
        </div>

        {/* Skill Evidence Grid */}
        {loading ? (
          <div className="py-16 text-center text-white/40">
            <div className="inline-block w-8 h-8 border-2 border-accent-400/30 border-t-accent-400 rounded-full animate-spin mb-3" />
            <p className="text-sm">Retrieving verified skill evidence...</p>
          </div>
        ) : filteredSkills.length === 0 ? (
          <div className="glass p-12 text-center rounded-2xl">
            <p className="text-white/50 text-sm mb-4">
              {displayedSkills.length === 0
                ? 'No skills in this category yet. Upload a resume or take assessments.'
                : 'No skills matched your search query.'}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredSkills.map((skill, idx) => {
              const isVerified = skill.status === 'VERIFIED';
              const isNeedsWork = skill.status === 'NEEDS_IMPROVEMENT';
              const isPending = skill.status === 'NEEDS_VERIFICATION';
              const isGap = skill.status === 'UNVERIFIED_GAP';

              return (
                <div
                  key={skill.skill_id || `${skill.skill_name}-${idx}`}
                  className="surface p-4 rounded-2xl flex flex-col justify-between border border-base-700/80 hover:border-accent-400/40 transition-all space-y-3"
                >
                  <div>
                    {/* Header: Skill Name & Status Badge */}
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-heading text-lg font-bold text-white capitalize">
                        {skill.skill_name}
                      </h3>

                      {isVerified && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 whitespace-nowrap">
                          <TbCheck className="w-3.5 h-3.5 mr-1" />
                          VERIFIED
                        </span>
                      )}
                      {isNeedsWork && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/40 whitespace-nowrap">
                          <TbCircleX className="w-3.5 h-3.5 mr-1" />
                          NEEDS WORK
                        </span>
                      )}
                      {isPending && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/40 whitespace-nowrap">
                          <TbHelpCircle className="w-3.5 h-3.5 mr-1" />
                          UNVERIFIED
                        </span>
                      )}
                      {isGap && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/40 whitespace-nowrap">
                          <TbAlertTriangle className="w-3.5 h-3.5 mr-1" />
                          ROLE GAP
                        </span>
                      )}
                    </div>

                    {/* Source Evidence */}
                    <div className="flex items-center space-x-1.5 text-xs text-white/50 mt-1">
                      {skill.resume_detected ? (
                        <>
                          <TbFileCheck className="w-3.5 h-3.5 text-accent-400" />
                          <span>Resume detected</span>
                          <span className="text-white/30">·</span>
                          <span className="capitalize">{skill.proficiency || 'Intermediate'}</span>
                        </>
                      ) : (
                        <>
                          <TbAward className="w-3.5 h-3.5 text-purple-400" />
                          <span>Industry Required Competency</span>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Verification Evidence Block */}
                  <div className="bg-base-950/70 p-3 rounded-xl border border-base-800 space-y-1.5 text-xs">
                    {skill.quiz_score_percent !== null && skill.quiz_score_percent !== undefined ? (
                      <>
                        <div className="flex justify-between items-center">
                          <span className="text-white/50">Assessment Score:</span>
                          <span className={`font-mono font-bold ${isVerified ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {skill.quiz_score_percent}% ({skill.quiz_correct_count}/{skill.quiz_question_count})
                          </span>
                        </div>
                        {skill.verified_on && (
                          <div className="flex justify-between items-center text-[11px] text-white/40">
                            <span className="flex items-center space-x-1">
                              <TbCalendar className="w-3 h-3" />
                              <span>Evaluated:</span>
                            </span>
                            <span>{new Date(skill.verified_on).toLocaleDateString()}</span>
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="flex justify-between items-center text-white/40">
                        <span>Assessment Evidence:</span>
                        <span className="font-mono text-amber-300/80">Not Evaluated</span>
                      </div>
                    )}
                  </div>

                  {/* Action Button */}
                  <div>
                    {!isVerified && skill.skill_id && (
                      <button
                        onClick={() => setSelectedQuizSkill({ id: skill.skill_id, skill_name: skill.skill_name })}
                        className="btn-primary text-xs w-full py-2 flex items-center justify-center space-x-1.5"
                      >
                        <span>{isNeedsWork ? 'Retake Verification Quiz' : 'Take Verification Quiz'}</span>
                        <TbArrowRight className="w-3.5 h-3.5" />
                      </button>
                    )}
                    {isVerified && (
                      <div className="text-center text-[11px] text-emerald-400/80 font-mono py-1">
                        ✓ Competency Proven for Career Readiness
                      </div>
                    )}
                    {isGap && (
                      <button
                        onClick={() => navigate('/roadmap')}
                        className="btn-ghost text-xs w-full py-2 flex items-center justify-center space-x-1.5"
                      >
                        <span>Add to Roadmap</span>
                        <TbArrowRight className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Verification Modal */}
        {selectedQuizSkill && (
          <QuizModal
            skill={selectedQuizSkill}
            onClose={() => setSelectedQuizSkill(null)}
            onQuizComplete={handleQuizComplete}
          />
        )}
      </div>
    </AppLayout>
  );
}
