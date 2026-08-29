import React, { useState, useEffect } from 'react';
import AppLayout from '../components/AppLayout';
import QuizModal from '../components/QuizModal';
import AlertBanner from '../components/AlertBanner';
import skillService from '../services/skillService';
import {
  TbHelp,
  TbArrowRight,
  TbCheck,
  TbAlertCircle
} from 'react-icons/tb';

export default function Assessment() {
  const [data, setData] = useState({ available: [], completed: [] });
  const [loading, setLoading] = useState(true);
  const [selectedSkill, setSelectedSkill] = useState(null);
  const [alert, setAlert] = useState(null);

  const fetchAssessments = () => {
    setLoading(true);
    skillService.getAssessments()
      .then((res) => {
        setData(res);
      })
      .catch(() => {
        setAlert({ type: 'error', message: 'Failed to load assessment catalog.' });
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchAssessments();
  }, []);

  const handleQuizComplete = (res) => {
    setAlert({
      type: 'success',
      message: `Assessment completed for ${res.skill_name}! Score: ${res.quiz_score_percent}%`,
    });
    fetchAssessments();
  };

  return (
    <AppLayout>
      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="font-heading text-2xl font-bold text-white">
            Skill Verification Assessments
          </h1>
          <p className="text-white/50 text-sm mt-1">
            Prove your competency. AI adapts question counts and difficulty tiers based on evidence extracted from your resume.
          </p>
        </div>

        {alert && (
          <AlertBanner
            type={alert.type}
            message={alert.message}
            onClose={() => setAlert(null)}
          />
        )}

        {/* How it works Banner */}
        <div className="glass p-5 rounded-2xl border border-accent-400/20 bg-gradient-to-r from-base-900 to-base-800">
          <div className="flex items-start space-x-3">
            <div className="p-2 rounded-xl bg-accent-500/20 text-accent-300">
              <TbHelp className="w-5 h-5" />
            </div>
            <div className="text-xs text-white/70 space-y-1">
              <p className="font-semibold text-white">Adaptive Evaluation Logic:</p>
              <p>
                Skills detected across multiple sections trigger quick 3-question sanity checks. Uncorroborated skills require a thorough 8-question verification quiz to confirm genuine competency.
              </p>
            </div>
          </div>
        </div>

        {/* Available for Testing */}
        <div className="space-y-4">
          <h2 className="font-heading font-semibold text-lg text-white flex items-center space-x-2">
            <span>Pending Skills</span>
            <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-base-800 text-white/40">
              {data.available.length}
            </span>
          </h2>

          {loading ? (
            <div className="py-12 text-center text-white/40 text-sm">
              Loading available assessments...
            </div>
          ) : data.available.length === 0 ? (
            <div className="glass p-6 text-center rounded-xl text-white/50 text-sm">
              All extracted skills have been verified!
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              {data.available.map((item) => (
                <div key={item.skill_id} className="surface p-4 rounded-xl flex flex-col justify-between space-y-3">
                  <div>
                    <h3 className="font-medium text-white capitalize text-base">
                      {item.skill_name}
                    </h3>
                    <p className="text-xs text-white/40 mt-0.5">
                      Confidence: {Math.round(item.extraction_confidence * 100)}%
                    </p>
                  </div>
                  <button
                    onClick={() => setSelectedSkill(item)}
                    className="btn-primary text-xs py-2 px-3 flex items-center justify-center space-x-1.5"
                  >
                    <span>Begin Quiz</span>
                    <TbArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Completed Assessments History */}
        <div className="space-y-4">
          <h2 className="font-heading font-semibold text-lg text-white flex items-center space-x-2">
            <span>Completed Test Attempts</span>
            <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-base-800 text-white/40">
              {data.completed.length}
            </span>
          </h2>

          {data.completed.length === 0 ? (
            <div className="glass p-6 text-center rounded-xl text-white/40 text-xs">
              No test attempts completed yet. Start with a pending skill above.
            </div>
          ) : (
            <div className="glass overflow-hidden rounded-xl border border-base-700/60">
              <table className="w-full text-left text-xs">
                <thead className="bg-base-900 border-b border-base-700/60 text-white/50">
                  <tr>
                    <th className="py-3 px-4">Skill</th>
                    <th className="py-3 px-4">Quiz Score</th>
                    <th className="py-3 px-4">Verification Score</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-base-800">
                  {data.completed.map((attempt) => (
                    <tr key={attempt.skill_id} className="hover:bg-white/5 transition-colors">
                      <td className="py-3 px-4 font-medium text-white capitalize">
                        {attempt.skill_name}
                      </td>
                      <td className="py-3 px-4 font-mono font-semibold text-accent-300">
                        {attempt.score_percent}%
                      </td>
                      <td className="py-3 px-4 font-mono text-white/70">
                        {Math.round(attempt.verification_score * 100)}%
                      </td>
                      <td className="py-3 px-4">
                        {attempt.passed ? (
                          <span className="inline-flex items-center text-emerald-400 font-medium">
                            <TbCheck className="w-4 h-4 mr-1" /> Passed
                          </span>
                        ) : (
                          <span className="inline-flex items-center text-amber-400 font-medium">
                            <TbAlertCircle className="w-4 h-4 mr-1" /> Needs Review
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-white/40 font-mono">
                        {attempt.verified_on ? attempt.verified_on.split('T')[0] : 'N/A'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Modal */}
        {selectedSkill && (
          <QuizModal
            skill={selectedSkill}
            onClose={() => setSelectedSkill(null)}
            onQuizComplete={handleQuizComplete}
          />
        )}
      </div>
    </AppLayout>
  );
}
