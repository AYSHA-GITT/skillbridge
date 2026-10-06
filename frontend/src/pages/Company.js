import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import AppLayout from '../components/AppLayout';
import ProgressBar from '../components/ProgressBar';
import AlertBanner from '../components/AlertBanner';
import skillService from '../services/skillService';
import {
  TbArrowRight,
  TbSparkles,
  TbInfoCircle,
  TbScale,
  TbX,
  TbTarget,
  TbClock
} from 'react-icons/tb';

export default function Company() {
  const navigate = useNavigate();
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [updating, setUpdating] = useState(null);
  const [expandedCareer, setExpandedCareer] = useState(null);
  const [topMatchDetailsOpen, setTopMatchDetailsOpen] = useState(false);

  // Career Comparison state
  const [selectedForCompare, setSelectedForCompare] = useState([]);
  const [showComparisonModal, setShowComparisonModal] = useState(false);
  const [comparisonData, setComparisonData] = useState([]);
  const [comparing, setComparing] = useState(false);

  const fetchRecommendations = () => {
    setLoading(true);
    skillService.getCareerRecommendations()
      .then((res) => {
        setRecommendations(res.recommendations || []);
      })
      .catch(() => {
        setError('Failed to load career recommendations.');
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchRecommendations();
  }, []);

  const handleSelectRole = async (careerName) => {
    setUpdating(careerName);
    setError('');
    setSuccessMsg('');
    try {
      await skillService.setTargetCareer(careerName);
      setSuccessMsg(`Target career successfully set to ${careerName}!`);
      setTimeout(() => navigate('/skill-gap'), 800);
    } catch {
      setError('Could not update target career.');
      setUpdating(null);
    }
  };

  const toggleCompareSelection = (careerKey) => {
    if (selectedForCompare.includes(careerKey)) {
      setSelectedForCompare(selectedForCompare.filter((c) => c !== careerKey));
    } else {
      if (selectedForCompare.length >= 3) {
        setError('You can compare a maximum of 3 careers simultaneously.');
        return;
      }
      setSelectedForCompare([...selectedForCompare, careerKey]);
    }
  };

  const handleOpenComparison = async () => {
    if (selectedForCompare.length < 2) {
      setError('Please select at least 2 careers to compare.');
      return;
    }
    setComparing(true);
    setError('');
    try {
      const res = await skillService.compareCareers(selectedForCompare);
      setComparisonData(res.comparison || []);
      setShowComparisonModal(true);
    } catch {
      setError('Failed to generate career comparison.');
    } finally {
      setComparing(false);
    }
  };

  const topMatch = recommendations.find((r) => r.is_top_match) || recommendations[0];

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="font-heading text-2xl font-bold text-white">
                Career Recommendations & Comparison
              </h1>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-accent-500/15 text-accent-300 border border-accent-400/30">
                Verified Skills Grounded
              </span>
            </div>
            <p className="text-white/50 text-sm mt-1">
              Deterministic matching calculated strictly from your proven assessment results.
            </p>
          </div>

          {selectedForCompare.length > 0 && (
            <button
              onClick={handleOpenComparison}
              disabled={comparing || selectedForCompare.length < 2}
              className="btn-primary text-xs py-2.5 px-4 flex items-center justify-center space-x-2 shadow-glow disabled:opacity-50"
            >
              <TbScale className="w-4 h-4" />
              <span>
                {comparing
                  ? 'Comparing...'
                  : `Compare Selected (${selectedForCompare.length}/3)`}
              </span>
            </button>
          )}
        </div>

        {error && <AlertBanner type="error" message={error} onClose={() => setError('')} />}
        {successMsg && <AlertBanner type="success" message={successMsg} onClose={() => setSuccessMsg('')} />}

        {loading ? (
          <div className="py-16 text-center text-white/40">
            <div className="inline-block w-8 h-8 border-2 border-accent-400/30 border-t-accent-400 rounded-full animate-spin mb-3" />
            <p className="text-sm">Calculating deterministic career matches from verified skills...</p>
          </div>
        ) : (
          <>
            {/* Top Recommended Career Spotlight */}
            {topMatch && (
              <div className="glass p-6 sm:p-7 rounded-3xl relative overflow-hidden border-accent-400/40 shadow-glow transition-all duration-300">
                <div className="glow-teal absolute -right-10 -bottom-10 w-44 h-44 opacity-25" />
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative">
                  <div className="space-y-3 max-w-2xl">
                    <div className="flex items-center space-x-2">
                      <span className="flex items-center space-x-1 text-[11px] font-semibold text-accent-300 bg-accent-500/20 px-2.5 py-0.5 rounded-full border border-accent-400/30">
                        <TbSparkles className="w-3.5 h-3.5" />
                        <span>Top Career Match</span>
                      </span>
                      {topMatch.is_current_target && (
                        <span className="text-[11px] font-mono text-teal-300 bg-teal-500/20 px-2 py-0.5 rounded-full border border-teal-500/30">
                          Active Target
                        </span>
                      )}
                    </div>

                    <div>
                      <h2 className="font-heading text-3xl font-bold text-white">
                        {topMatch.career}
                      </h2>
                      <p className="text-sm text-white/70 mt-1">
                        {topMatch.recommendation_reason}
                      </p>
                    </div>

                    {/* Progressive Disclosure: Details Drawer */}
                    {topMatchDetailsOpen && (
                      <div className="surface p-4 rounded-2xl border border-base-700/80 space-y-2.5 animate-slide-up text-xs">
                        <div className="flex items-center space-x-1.5 font-semibold text-accent-300">
                          <TbInfoCircle className="w-4 h-4" />
                          <span>Why this was recommended:</span>
                        </div>
                        <ul className="text-white/60 space-y-1 pl-1">
                          {topMatch.explanation?.highlights?.map((h, i) => (
                            <li key={i} className="flex items-center space-x-2">
                              <span className="w-1.5 h-1.5 rounded-full bg-accent-400" />
                              <span>{h}</span>
                            </li>
                          ))}
                        </ul>
                        {topMatch.explanation?.action_recommendation && (
                          <div className="pt-2 border-t border-base-700/60 font-medium text-emerald-400">
                            🎯 {topMatch.explanation.action_recommendation}
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="flex flex-col items-start lg:items-end justify-between space-y-4">
                    <div className="text-left lg:text-right">
                      <span className="text-xs font-mono text-white/40">Readiness Score</span>
                      <p className="font-heading text-5xl font-bold text-white mt-0.5">
                        {topMatch.match_percentage}%
                      </p>
                      <p className="text-xs font-mono text-emerald-400 mt-0.5">
                        Estimated: ₹{topMatch.estimated_salary_lpa} LPA
                      </p>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                      <button
                        type="button"
                        onClick={() => setTopMatchDetailsOpen(!topMatchDetailsOpen)}
                        className="text-xs px-3 py-2 rounded-xl surface border border-base-700 text-accent-300 hover:text-white transition-all"
                      >
                        {topMatchDetailsOpen ? 'Hide Why ▲' : 'View Why & Details ▼'}
                      </button>

                      <button
                        onClick={() => toggleCompareSelection(topMatch.career_key)}
                        className={`text-xs py-2 px-3 rounded-xl border transition-all flex items-center space-x-1 ${
                          selectedForCompare.includes(topMatch.career_key)
                            ? 'bg-accent-500/20 border-accent-400 text-accent-300'
                            : 'surface border-base-700 text-white/70 hover:text-white'
                        }`}
                      >
                        <TbScale className="w-3.5 h-3.5" />
                        <span>{selectedForCompare.includes(topMatch.career_key) ? 'Selected' : 'Compare'}</span>
                      </button>

                      <button
                        onClick={() => handleSelectRole(topMatch.career)}
                        disabled={updating === topMatch.career}
                        className="btn-primary text-xs py-2 px-3.5 flex items-center space-x-1.5"
                      >
                        <TbTarget className="w-4 h-4" />
                        <span>{updating === topMatch.career ? 'Saving...' : 'Set as Target'}</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* All Career Recommendations Grid */}
            <div className="space-y-4 pt-2">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-heading text-lg font-bold text-white">
                    All Career Profiles ({recommendations.length})
                  </h3>
                  <p className="text-xs text-white/40 mt-0.5">
                    Click any card to inspect skills breakdown or select up to 3 to compare.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {recommendations.map((career) => {
                  const isSelected = selectedForCompare.includes(career.career_key);
                  const isExpanded = expandedCareer === career.career_key;

                  return (
                    <div
                      key={career.career_key}
                      className={`glass p-6 rounded-2xl flex flex-col justify-between transition-all duration-300 border hover:-translate-y-1 hover:shadow-glow ${
                        isSelected ? 'border-accent-400/80 bg-accent-500/5' : 'hover:border-accent-400/40'
                      }`}
                    >
                      <div className="space-y-3.5">
                        {/* Title Row */}
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <div className="flex items-center space-x-2">
                              <h4 className="font-heading text-xl font-bold text-white">
                                {career.career}
                              </h4>
                              {career.is_current_target && (
                                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-teal-500/20 text-teal-300 border border-teal-500/30">
                                  Current Target
                                </span>
                              )}
                            </div>
                            <p className="text-xs text-white/50 mt-1 line-clamp-1">
                              {career.recommendation_reason}
                            </p>
                          </div>

                          <span className="font-mono text-sm font-semibold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-lg border border-emerald-500/20 whitespace-nowrap">
                            ₹{career.estimated_salary_lpa} LPA
                          </span>
                        </div>

                        {/* Match Progress Bar */}
                        <div>
                          <ProgressBar
                            label="Skill Match"
                            value={career.match_percentage}
                            colorGradient="from-accent-400 to-teal-500"
                          />
                        </div>

                        {/* Clean Summary Pills upfront */}
                        <div className="flex items-center gap-2 pt-0.5">
                          <span className="px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 text-[11px] font-mono">
                            ✓ {career.matched_required?.length || 0} Skills Met
                          </span>
                          <span className="px-2.5 py-1 rounded-lg bg-base-800 text-white/60 border border-base-700/80 text-[11px] font-mono">
                            ⚠ {career.missing_required?.length || 0} Gaps
                          </span>
                        </div>

                        {/* Expandable Details on Click (Progressive Disclosure) */}
                        {isExpanded && (
                          <div className="surface p-3.5 rounded-xl border border-base-700/80 space-y-3 animate-slide-up text-xs mt-2">
                            {career.matched_required?.length > 0 && (
                              <div className="space-y-1">
                                <span className="text-[11px] text-emerald-400 font-medium">
                                  Strong Matches ({career.matched_required.length}):
                                </span>
                                <div className="flex flex-wrap gap-1">
                                  {career.matched_required.map((s) => (
                                    <span
                                      key={s}
                                      className="px-2 py-0.5 rounded-md text-[10px] font-mono bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 capitalize"
                                    >
                                      {s}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}

                            {career.missing_required?.length > 0 && (
                              <div className="space-y-1">
                                <span className="text-[11px] text-amber-400 font-medium">
                                  Missing Skills ({career.missing_required.length}):
                                </span>
                                <div className="flex flex-wrap gap-1">
                                  {career.missing_required.map((s) => (
                                    <span
                                      key={s}
                                      className="px-2 py-0.5 rounded-md text-[10px] font-mono bg-base-900 border border-base-700 text-white/60 capitalize"
                                    >
                                      {s}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}

                            {career.explanation?.action_recommendation && (
                              <p className="text-[11px] text-emerald-400 pt-1 border-t border-base-700/60">
                                💡 {career.explanation.action_recommendation}
                              </p>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Card Footer Actions */}
                      <div className="pt-4 mt-4 border-t border-base-800 flex items-center justify-between gap-2">
                        <div className="flex items-center space-x-2">
                          <button
                            type="button"
                            onClick={() => toggleCompareSelection(career.career_key)}
                            className={`text-xs px-2.5 py-1.5 rounded-lg border flex items-center space-x-1 transition-all ${
                              isSelected
                                ? 'bg-accent-500/20 border-accent-400 text-accent-300 font-semibold'
                                : 'surface border-base-700 text-white/60 hover:text-white'
                            }`}
                          >
                            <TbScale className="w-3.5 h-3.5" />
                            <span>{isSelected ? 'Selected' : 'Compare'}</span>
                          </button>

                          <button
                            type="button"
                            onClick={() => setExpandedCareer(isExpanded ? null : career.career_key)}
                            className="text-xs text-white/50 hover:text-accent-300 underline underline-offset-4"
                          >
                            {isExpanded ? 'Hide Details ▲' : 'View Details ▼'}
                          </button>
                        </div>

                        <button
                          onClick={() => handleSelectRole(career.career)}
                          disabled={updating === career.career}
                          className="btn-primary text-xs py-1.5 px-3 flex items-center space-x-1 shadow-glow"
                        >
                          <span>{updating === career.career ? 'Saving...' : 'Target'}</span>
                          <TbArrowRight className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </>
        )}

        {/* Side-by-Side Career Comparison Modal */}
        {showComparisonModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
            <div className="glass max-w-4xl w-full p-6 sm:p-8 rounded-3xl border border-accent-400/40 space-y-6 max-h-[90vh] overflow-y-auto">
              <div className="flex items-center justify-between border-b border-base-800 pb-4">
                <div className="flex items-center space-x-2">
                  <TbScale className="w-6 h-6 text-accent-400" />
                  <h3 className="font-heading text-xl font-bold text-white">
                    Side-by-Side Career Comparison
                  </h3>
                </div>
                <button
                  onClick={() => setShowComparisonModal(false)}
                  className="p-1 rounded-lg text-white/40 hover:text-white hover:bg-white/10"
                >
                  <TbX className="w-5 h-5" />
                </button>
              </div>

              {/* Comparison Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-base-800 text-white/40 font-mono">
                      <th className="py-3 px-3">Metric</th>
                      {comparisonData.map((c) => (
                        <th key={c.career_key} className="py-3 px-3 font-heading text-sm text-white font-bold">
                          {c.career}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-base-800 text-white/80">
                    <tr>
                      <td className="py-3.5 px-3 text-white/50 font-medium">Skill Match %</td>
                      {comparisonData.map((c) => (
                        <td key={c.career_key} className="py-3.5 px-3">
                          <span className="font-heading text-base font-bold text-accent-300">
                            {c.match_percentage}%
                          </span>
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td className="py-3.5 px-3 text-white/50 font-medium">Estimated Salary</td>
                      {comparisonData.map((c) => (
                        <td key={c.career_key} className="py-3.5 px-3 font-mono text-emerald-400 font-semibold">
                          ₹{c.estimated_salary_lpa} LPA
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td className="py-3.5 px-3 text-white/50 font-medium">Core Required Met</td>
                      {comparisonData.map((c) => (
                        <td key={c.career_key} className="py-3.5 px-3">
                          <span className="font-mono text-white">
                            {c.matched_required?.length || 0} / {c.total_required || 0}
                          </span>
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td className="py-3.5 px-3 text-white/50 font-medium">Verified Strengths</td>
                      {comparisonData.map((c) => (
                        <td key={c.career_key} className="py-3.5 px-3">
                          <div className="flex flex-wrap gap-1">
                            {c.matched_required?.map((s) => (
                              <span key={s} className="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-300 text-[10px] capitalize">
                                {s}
                              </span>
                            ))}
                            {c.matched_required?.length === 0 && (
                              <span className="text-white/30 text-[11px]">—</span>
                            )}
                          </div>
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td className="py-3.5 px-3 text-white/50 font-medium">Primary Gaps</td>
                      {comparisonData.map((c) => (
                        <td key={c.career_key} className="py-3.5 px-3">
                          <div className="flex flex-wrap gap-1">
                            {c.missing_required?.map((s) => (
                              <span key={s} className="px-1.5 py-0.5 rounded bg-base-900 text-white/60 text-[10px] capitalize border border-base-700">
                                {s}
                              </span>
                            ))}
                          </div>
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td className="py-3.5 px-3 text-white/50 font-medium">Est. Learning Effort</td>
                      {comparisonData.map((c) => (
                        <td key={c.career_key} className="py-3.5 px-3 flex items-center space-x-1 text-white/60">
                          <TbClock className="w-3.5 h-3.5 text-accent-400" />
                          <span>~{c.estimated_days_to_close} days</span>
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td className="py-3.5 px-3 text-white/50 font-medium">Action</td>
                      {comparisonData.map((c) => (
                        <td key={c.career_key} className="py-3.5 px-3">
                          <button
                            onClick={() => {
                              handleSelectRole(c.career);
                              setShowComparisonModal(false);
                            }}
                            className="btn-primary text-xs py-1.5 px-3 whitespace-nowrap"
                          >
                            Set as Target
                          </button>
                        </td>
                      ))}
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
