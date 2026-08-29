import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import AppLayout from '../components/AppLayout';
import ProgressBar from '../components/ProgressBar';
import AlertBanner from '../components/AlertBanner';
import skillService from '../services/skillService';
import { TbArrowRight } from 'react-icons/tb';

export default function Company() {
  const navigate = useNavigate();
  const [careers, setCareers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [updating, setUpdating] = useState(null);

  useEffect(() => {
    skillService.getCareerInsights()
      .then((res) => setCareers(res.careers || []))
      .catch(() => setError('Failed to load career benchmarks.'))
      .finally(() => setLoading(false));
  }, []);

  const handleSelectRole = async (role) => {
    setUpdating(role);
    try {
      await skillService.setTargetCareer(role);
      navigate('/skill-gap');
    } catch {
      setError('Could not set target career.');
      setUpdating(null);
    }
  };

  return (
    <AppLayout>
      <div className="space-y-6">
        <div>
          <h1 className="font-heading text-2xl font-bold text-white">
            Market Career Demands
          </h1>
          <p className="text-white/50 text-sm mt-1">
            Compare your verified skill set against the hiring standards of top technology companies.
          </p>
        </div>

        {error && <AlertBanner type="error" message={error} onClose={() => setError('')} />}

        {loading ? (
          <div className="py-16 text-center text-white/40">
            <div className="inline-block w-8 h-8 border-2 border-accent-400/30 border-t-accent-400 rounded-full animate-spin mb-3" />
            <p className="text-sm">Matching profiles against career benchmarks...</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {careers.map((career) => (
              <div
                key={career.role}
                className="glass p-6 rounded-2xl flex flex-col justify-between hover:border-accent-400/40 transition-all group"
              >
                <div>
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <span className="text-[10px] font-mono uppercase tracking-wider text-accent-400">
                        Tech Track
                      </span>
                      <h3 className="font-heading text-xl font-bold text-white group-hover:text-accent-300 transition-colors">
                        {career.role}
                      </h3>
                    </div>
                    <span className="font-mono text-sm font-semibold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-lg border border-emerald-500/20">
                      ₹{career.estimated_salary_lpa} LPA
                    </span>
                  </div>

                  {/* Match percentage */}
                  <div className="mt-4 mb-5">
                    <ProgressBar
                      label="Your Skill Match"
                      value={career.match_percentage}
                      colorGradient="from-accent-400 to-teal-500"
                    />
                  </div>

                  {/* Missing skills preview */}
                  <div className="space-y-2">
                    <span className="text-xs text-white/50 font-medium">Priority Gap Skills:</span>
                    <div className="flex flex-wrap gap-1.5">
                      {career.missing_skills?.map((s) => (
                        <span
                          key={s}
                          className="px-2 py-0.5 rounded-md text-[11px] font-mono bg-base-900 border border-base-700/80 text-white/60 capitalize"
                        >
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="pt-6 mt-6 border-t border-base-800 flex items-center justify-between">
                  <span className="text-xs text-white/40">
                    {career.matched_count} of {career.matched_count + career.missing_count} Skills Proven
                  </span>
                  <button
                    onClick={() => handleSelectRole(career.role)}
                    disabled={updating === career.role}
                    className="btn-primary text-xs py-2 px-4 flex items-center space-x-1.5 max-w-fit"
                  >
                    <span>{updating === career.role ? 'Selecting...' : 'Target This Role'}</span>
                    <TbArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
