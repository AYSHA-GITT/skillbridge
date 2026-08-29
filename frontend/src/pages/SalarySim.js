import React, { useState, useEffect } from 'react';
import AppLayout from '../components/AppLayout';
import { SalaryProjectionBar } from '../components/Charts';
import AlertBanner from '../components/AlertBanner';
import skillService from '../services/skillService';
import { TbCoin, TbPlus, TbCheck, TbSparkles, TbTrendingUp } from 'react-icons/tb';

const CANDIDATE_ADDITIONAL_SKILLS = [
  'docker', 'aws', 'kubernetes', 'pytorch', 'tensorflow',
  'react', 'flask', 'sql', 'system design', 'machine learning'
];

export default function SalarySim() {
  const [selectedSkills, setSelectedSkills] = useState(['docker', 'aws']);
  const [simResult, setSimResult] = useState(null);
  const [error, setError] = useState('');

  const runSimulation = (skillsToSimulate) => {
    skillService.simulateSalary(skillsToSimulate)
      .then((data) => {
        setSimResult(data);
      })
      .catch(() => {
        setError('Failed to compute salary simulation.');
      });
  };

  useEffect(() => {
    runSimulation(selectedSkills);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleToggleSkill = (skill) => {
    const updated = selectedSkills.includes(skill)
      ? selectedSkills.filter((s) => s !== skill)
      : [...selectedSkills, skill];
    setSelectedSkills(updated);
    runSimulation(updated);
  };

  return (
    <AppLayout>
      <div className="space-y-6">
        <div>
          <h1 className="font-heading text-2xl font-bold text-white">
            Interactive Salary Simulator
          </h1>
          <p className="text-white/50 text-sm mt-1">
            See the direct financial upside of closing your skill gaps. Powered by benchmark regression modeling.
          </p>
        </div>

        {error && <AlertBanner type="error" message={error} onClose={() => setError('')} />}

        {/* Projection Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="glass p-5 rounded-2xl">
            <span className="text-white/40 text-xs">Current Estimated Package</span>
            <p className="font-heading text-3xl font-bold text-white mt-1">
              ₹{simResult?.current_salary || 5.0} LPA
            </p>
            <p className="text-[11px] text-white/40 mt-1">Based on currently verified skills</p>
          </div>

          <div className="glass p-5 rounded-2xl relative overflow-hidden">
            <div className="glow-teal absolute -right-8 -top-8 w-32 h-32 opacity-20" />
            <span className="text-white/40 text-xs">Projected Package</span>
            <p className="font-heading text-3xl font-bold text-accent-400 mt-1">
              ₹{simResult?.projected_salary || 8.5} LPA
            </p>
            <p className="text-[11px] text-accent-300/70 mt-1">
              With {selectedSkills.length} selected target skills
            </p>
          </div>

          <div className="glass p-5 rounded-2xl">
            <span className="text-white/40 text-xs">Estimated Earnings Boost</span>
            <p className="font-heading text-3xl font-bold text-emerald-400 mt-1">
              +₹{simResult?.projected_boost || 0} LPA
            </p>
            <span className="inline-block text-[11px] text-emerald-300 bg-emerald-500/10 px-2 py-0.5 rounded mt-1 font-mono font-medium">
              +{simResult?.percentage_increase || 0}% increase
            </span>
          </div>
        </div>

        {/* Chart + Skills Picker */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Visual Chart */}
          <div className="glass p-6 rounded-2xl flex flex-col justify-between">
            <div>
              <div className="flex items-center space-x-2 mb-3">
                <TbCoin className="w-5 h-5 text-accent-400" />
                <h3 className="font-heading font-semibold text-white text-base">
                  Salary Delta Projection
                </h3>
              </div>
              <p className="text-xs text-white/50 mb-4">
                Comparison of entry-level compensations before and after acquiring high-demand skills.
              </p>
            </div>

            <div className="py-2">
              <SalaryProjectionBar
                currentSalary={simResult?.current_salary || 5.0}
                projectedSalary={simResult?.projected_salary || 8.5}
              />
            </div>

            <p className="text-[11px] text-white/30 text-center">
              Estimates derived from Indian campus placement & tech startup benchmarks.
            </p>
          </div>

          {/* Interactive Skill Selector */}
          <div className="glass p-6 rounded-2xl space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <TbSparkles className="w-5 h-5 text-accent-400" />
                <h3 className="font-heading font-semibold text-white text-base">
                  Toggle Skills to Simulate
                </h3>
              </div>
              <span className="text-xs font-mono text-accent-300">
                {selectedSkills.length} Active
              </span>
            </div>

            <p className="text-xs text-white/50">
              Click skills below to see their compounding impact on your projected career compensation:
            </p>

            <div className="flex flex-wrap gap-2.5 pt-2">
              {CANDIDATE_ADDITIONAL_SKILLS.map((skill) => {
                const isSelected = selectedSkills.includes(skill);
                return (
                  <button
                    key={skill}
                    type="button"
                    onClick={() => handleToggleSkill(skill)}
                    className={`px-3.5 py-2 rounded-xl text-xs font-medium capitalize transition-all flex items-center space-x-2 ${
                      isSelected
                        ? 'bg-accent-500/20 text-white border border-accent-400/50 shadow-glow'
                        : 'bg-base-900 border border-base-700/60 text-white/60 hover:text-white hover:border-white/20'
                    }`}
                  >
                    {isSelected ? (
                      <TbCheck className="w-3.5 h-3.5 text-accent-400" />
                    ) : (
                      <TbPlus className="w-3.5 h-3.5 text-white/40" />
                    )}
                    <span>{skill}</span>
                  </button>
                );
              })}
            </div>

            <div className="surface p-4 rounded-xl border border-base-700/80 mt-6">
              <div className="flex items-center space-x-2 text-white/80 text-xs font-medium">
                <TbTrendingUp className="w-4 h-4 text-emerald-400" />
                <span>Market Insight:</span>
              </div>
              <p className="text-[11px] text-white/50 mt-1 leading-relaxed">
                Cloud and DevOps competencies (AWS, Docker, Kubernetes) yield the highest immediate salary multiplier when combined with standard software engineering.
              </p>
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
