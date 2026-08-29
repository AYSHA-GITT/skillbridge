import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import AppLayout from '../components/AppLayout';
import SkillCard from '../components/SkillCard';
import QuizModal from '../components/QuizModal';
import AlertBanner from '../components/AlertBanner';
import skillService from '../services/skillService';
import { TbFileUpload, TbSearch } from 'react-icons/tb';

export default function SkillProfile() {
  const navigate = useNavigate();
  const [skills, setSkills] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState('all'); // all, verified, unverified
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedQuizSkill, setSelectedQuizSkill] = useState(null);
  const [alert, setAlert] = useState(null);

  const fetchSkills = () => {
    setLoading(true);
    skillService.getStudentSkills()
      .then((data) => {
        setSkills(data.skills || []);
      })
      .catch((err) => {
        setAlert({ type: 'error', message: 'Failed to load skills profile.' });
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchSkills();
  }, []);

  const handleQuizComplete = (res) => {
    setAlert({
      type: 'success',
      message: `Completed assessment for ${res.skill_name}! Score: ${res.quiz_score_percent}%`,
    });
    fetchSkills();
  };

  const filteredSkills = skills.filter((s) => {
    const matchesFilter =
      activeFilter === 'all' ||
      (activeFilter === 'verified' && (s.is_verified || s.verification)) ||
      (activeFilter === 'unverified' && !(s.is_verified || s.verification));

    const matchesSearch = s.skill_name.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const verifiedCount = skills.filter((s) => s.is_verified || s.verification).length;

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="font-heading text-2xl font-bold text-white">
              Skills Profile
            </h1>
            <p className="text-white/50 text-sm mt-1">
              Extracted from your parsed resumes & verified via adaptive assessments.
            </p>
          </div>
          <button
            onClick={() => navigate('/upload-resume')}
            className="btn-primary text-xs py-2.5 px-4 flex items-center justify-center space-x-2 max-w-xs"
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

        {/* Stats Row */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="glass p-4 rounded-xl">
            <span className="text-white/40 text-xs">Total Skills Detected</span>
            <p className="font-heading text-2xl font-bold text-white mt-1">
              {skills.length}
            </p>
          </div>
          <div className="glass p-4 rounded-xl">
            <span className="text-white/40 text-xs">Verified Competencies</span>
            <p className="font-heading text-2xl font-bold text-emerald-400 mt-1">
              {verifiedCount}
            </p>
          </div>
          <div className="glass p-4 rounded-xl">
            <span className="text-white/40 text-xs">Pending Verification</span>
            <p className="font-heading text-2xl font-bold text-amber-400 mt-1">
              {skills.length - verifiedCount}
            </p>
          </div>
        </div>

        {/* Filters & Search */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex space-x-2 bg-base-900 p-1 rounded-xl border border-base-700/60 w-full sm:w-auto">
            {['all', 'verified', 'unverified'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveFilter(tab)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-all flex-1 sm:flex-none ${
                  activeFilter === tab
                    ? 'bg-accent-500/20 text-accent-300 border border-accent-400/30'
                    : 'text-white/50 hover:text-white'
                }`}
              >
                {tab}
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

        {/* Skills Grid */}
        {loading ? (
          <div className="py-16 text-center text-white/40">
            <div className="inline-block w-8 h-8 border-2 border-accent-400/30 border-t-accent-400 rounded-full animate-spin mb-3" />
            <p className="text-sm">Loading skills inventory...</p>
          </div>
        ) : filteredSkills.length === 0 ? (
          <div className="glass p-12 text-center rounded-2xl">
            <p className="text-white/50 text-sm mb-4">
              {skills.length === 0
                ? "No skills found. Upload a resume to extract your skills."
                : "No skills matched your filter."}
            </p>
            {skills.length === 0 && (
              <button
                onClick={() => navigate('/upload-resume')}
                className="btn-primary text-xs py-2 px-4 max-w-xs mx-auto"
              >
                Upload Resume Now
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {filteredSkills.map((skill) => (
              <SkillCard
                key={skill.id}
                skill={skill}
                onVerify={(s) => setSelectedQuizSkill(s)}
              />
            ))}
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
