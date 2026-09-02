import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import {
  TbCloud, TbMessageCircle, TbChartBar, TbDatabase,
  TbCode, TbTable, TbTarget, TbCheck, TbBrandYoutube,
} from 'react-icons/tb';

function iconForSkill(skillName) {
  const s = skillName.toLowerCase();
  if (s.includes('cloud') || s.includes('aws') || s.includes('azure')) return TbCloud;
  if (s.includes('communicat')) return TbMessageCircle;
  if (s.includes('data') || s.includes('visualiz') || s.includes('analysis')) return TbChartBar;
  if (s.includes('sql') || s.includes('database')) return TbDatabase;
  if (s.includes('python') || s.includes('java') || s.includes('code') || s.includes('program')) return TbCode;
  if (s.includes('excel') || s.includes('sheet')) return TbTable;
  return TbTarget;
}

function buildResourceUrl(hint) {
  if (!hint) return null;
  const cleaned = hint.replace(/^(YouTube|Google|Search)\s*:\s*/i, '').trim();
  const query = encodeURIComponent(cleaned || hint);
  return `https://www.youtube.com/results?search_query=${query}`;
}

export default function Roadmap() {
  const navigate = useNavigate();
  const [stage, setStage] = useState('loading');
  const [roadmap, setRoadmap] = useState([]);
  const [selectedSkill, setSelectedSkill] = useState(null);
  const [error, setError] = useState('');

  const loadExisting = () => {
    api.get('/student/get_roadmap')
      .then((res) => {
        if (!res.data.roadmap || res.data.roadmap.length === 0) {
          setStage('empty');
        } else {
          setRoadmap(res.data.roadmap);
          setSelectedSkill(res.data.roadmap[0].skill);
          setStage('done');
        }
      })
      .catch((err) => {
        setError(err.response?.data?.error || 'Something went wrong');
        setStage('error');
      });
  };

  useEffect(() => {
    loadExisting();
  }, []);

  const handleGenerate = async () => {
    setStage('loading');
    try {
      const res = await api.post('/student/generate_roadmap');
      if (!res.data.roadmap || res.data.roadmap.length === 0) {
        setStage('empty');
      } else {
        setRoadmap(res.data.roadmap);
        setSelectedSkill(res.data.roadmap[0]?.skill || null);
        setStage('done');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Could not generate roadmap');
      setStage('error');
    }
  };

  const toggleDay = async (day) => {
    const goingToComplete = !day.is_completed;
    setRoadmap((prev) =>
      prev.map((group) => ({
        ...group,
        days: group.days.map((d) =>
          d.id === day.id ? { ...d, is_completed: goingToComplete } : d
        ),
      }))
    );
    if (goingToComplete) {
      try {
        await api.post(`/student/complete_roadmap_day/${day.id}`);
      } catch {
        setRoadmap((prev) =>
          prev.map((group) => ({
            ...group,
            days: group.days.map((d) =>
              d.id === day.id ? { ...d, is_completed: false } : d
            ),
          }))
        );
      }
    }
  };

  const skillProgress = (days) => {
    const done = days.filter((d) => d.is_completed).length;
    return { done, total: days.length, pct: Math.round((done / days.length) * 100) };
  };

  const activeGroup = roadmap.find((g) => g.skill === selectedSkill);

  return (
    <div className="min-h-screen px-6 py-10 max-w-3xl mx-auto">
      <button onClick={() => navigate('/dashboard')} className="text-white/40 hover:text-white text-sm mb-6">
        ← Back to dashboard
      </button>

      <div className="glass p-8">
        <h1 className="font-heading text-2xl font-semibold mb-1">Your learning roadmap</h1>
        <p className="text-white/50 text-sm mb-8">Day-by-day plans for the skills you're missing</p>

        {stage === 'loading' && (
          <div className="text-center py-12">
            <div className="inline-block w-8 h-8 border-2 border-accent-400/30 border-t-accent-400 rounded-full animate-spin mb-4" />
            <p className="text-white/60">Building your roadmap... this can take a moment</p>
          </div>
        )}

        {stage === 'error' && (
          <div className="text-center py-12">
            <p className="text-red-400 mb-2">Something went wrong</p>
            <p className="text-white/40 text-sm">{error}</p>
          </div>
        )}

        {stage === 'empty' && (
          <div className="text-center py-12">
            <p className="text-white/60 mb-6">You don't have a roadmap yet. Generate one based on your skill gaps.</p>
            <button onClick={handleGenerate} className="btn-primary max-w-xs mx-auto">Generate my roadmap</button>
          </div>
        )}

        {stage === 'done' && (
          roadmap.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-white/60 mb-6">No learning tasks generated yet. Click below to generate your personalized learning plan.</p>
              <button onClick={handleGenerate} className="btn-primary max-w-xs mx-auto">Generate my roadmap</button>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
                {roadmap.map((group) => {
                  const { done, total, pct } = skillProgress(group.days);
                  const Icon = iconForSkill(group.skill);
                  const isActive = selectedSkill === group.skill;
                  return (
                    <button
                      key={group.skill}
                      onClick={() => setSelectedSkill(group.skill)}
                      className={`text-left surface p-3.5 transition-all ${isActive ? 'border-accent-400' : 'hover:border-white/20'}`}
                    >
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${isActive ? 'bg-accent-400/15' : 'bg-white/5'}`}>
                        <Icon className={isActive ? 'text-accent-400' : 'text-white/40'} size={16} />
                      </div>
                      <p className="text-sm font-medium mt-2.5 capitalize">{group.skill}</p>
                      <p className="text-xs text-white/40 mt-0.5 mb-1.5">{done} of {total} days</p>
                      <div className="h-0.5 rounded-full bg-base-700 overflow-hidden">
                        <div className="h-full bg-accent-400 rounded-full" style={{ width: `${pct}%` }} />
                      </div>
                    </button>
                  );
                })}
              </div>

              {activeGroup && (
                <>
                  <p className="text-xs font-medium text-white/40 mb-4 capitalize">
                    {activeGroup.skill} — day by day
                  </p>

                  <div className="relative pl-1.5">
                    <div className="absolute left-[19px] top-1.5 bottom-1.5 w-0.5 bg-base-700" />
                    <div className="space-y-4">
                      {activeGroup.days.map((day) => {
                        const resourceUrl = buildResourceUrl(day.resource_link);
                        return (
                          <div key={day.id} className="flex gap-3.5 relative">
                            <button
                              onClick={() => toggleDay(day)}
                              className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 z-10 transition-all hover:scale-110 ${day.is_completed ? 'bg-accent-400' : 'bg-base-900 border-2 border-accent-400/60'
                                }`}
                            >
                              {day.is_completed && <TbCheck className="text-base-950" size={14} />}
                            </button>
                            <div className="flex-1 pb-1">
                              <div className="flex items-start justify-between gap-2">
                                <p className={`text-sm font-medium ${day.is_completed ? 'text-white/40 line-through' : 'text-white'}`}>
                                  Day {day.day_number}: {day.topic}
                                </p>
                                <span className="text-xs text-white/30 whitespace-nowrap">{day.duration_hours}h</span>
                              </div>
                              <p className="text-xs text-white/50 mt-1 mb-2">{day.description}</p>
                              {resourceUrl && (
                                <a
                                  href={resourceUrl}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="inline-flex items-center gap-1.5 bg-white/5 border border-white/10 hover:border-accent-400/50 hover:bg-white/10 px-2.5 py-1 rounded-full text-xs text-accent-400 transition-all"
                                >
                                  <TbBrandYoutube size={13} />
                                  {day.resource_link.replace(/^(YouTube|Google|Search)\s*:\s*/i, '')}
                                </a>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </>
              )}

              <button onClick={handleGenerate} className="w-full mt-6 px-4 py-3 rounded-xl border border-white/10 text-white/50 hover:text-white hover:border-white/20 transition-all text-sm">
                Regenerate roadmap
              </button>
            </>
          )
        )}
      </div>
    </div>
  );
}