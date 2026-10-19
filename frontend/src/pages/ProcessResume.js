import { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../services/api';

export default function ProcessResume() {
  const { resumeId } = useParams();
  const navigate = useNavigate();

  const [stage, setStage] = useState('parsing'); // parsing | extracting | done | error
  const [skills, setSkills] = useState([]);
  const [ragAnalysis, setRagAnalysis] = useState(null);
  const [activeTab, setActiveTab] = useState('skills'); // skills | rag
  const [error, setError] = useState('');
  const executingRef = useRef(false);

  const runPipeline = useCallback(async () => {
    if (executingRef.current) return;
    executingRef.current = true;
    setError('');

    try {
      setStage('parsing');
      await api.post(`/student/parse_resume/${resumeId}`);

      setStage('extracting');
      const res = await api.post(`/student/extract_skills/${resumeId}`);
      setSkills(res.data.skills || []);

      // Run RAG Semantic Retrieval & Grounding
      try {
        const ragRes = await api.post(`/student/rag/analyze_resume/${resumeId}`);
        if (ragRes.data?.rag_analysis) {
          setRagAnalysis(ragRes.data.rag_analysis);
        }
      } catch (ragErr) {
        console.warn('RAG analysis fallback notice:', ragErr);
      }

      setStage('done');
    } catch (err) {
      setError(err.response?.data?.error || 'Something went wrong while processing your resume');
      setStage('error');
    } finally {
      executingRef.current = false;
    }
  }, [resumeId]);

  useEffect(() => {
    runPipeline();
  }, [runPipeline]);

  const confidenceColor = (score) => {
    if (score >= 0.7) return 'text-accent-400';
    if (score >= 0.4) return 'text-amber-400';
    return 'text-red-400';
  };

  const confidenceLabel = (score) => {
    if (score >= 0.7) return 'Strong evidence';
    if (score >= 0.4) return 'Some evidence';
    return 'Just listed';
  };

  return (
    <div className="min-h-screen px-6 py-10 max-w-3xl mx-auto">
      <button
        onClick={() => navigate('/dashboard')}
        className="text-white/40 hover:text-white text-sm mb-6"
      >
        ← Back to dashboard
      </button>

      <div className="glass p-8">
        {stage === 'parsing' && (
          <div className="text-center py-12">
            <div className="inline-block w-8 h-8 border-2 border-accent-400/30 border-t-accent-400 rounded-full animate-spin mb-4" />
            <p className="text-white/60">Reading your resume...</p>
          </div>
        )}

        {stage === 'extracting' && (
          <div className="text-center py-12">
            <div className="inline-block w-8 h-8 border-2 border-accent-400/30 border-t-accent-400 rounded-full animate-spin mb-4" />
            <p className="text-white/60">Extracting your skills...</p>
          </div>
        )}

        {stage === 'error' && (
          <div className="text-center py-12">
            <div className="w-12 h-12 rounded-full bg-red-500/10 border border-red-500/20 text-red-400 flex items-center justify-center mx-auto mb-4 text-xl">
              ✕
            </div>
            <p className="text-red-400 font-semibold mb-2">Failed to process resume</p>
            <p className="text-white/50 text-sm max-w-md mx-auto mb-6">{error}</p>
            <div className="flex items-center justify-center gap-3">
              <button
                onClick={() => runPipeline()}
                className="btn-primary px-6"
              >
                Retry Extraction
              </button>
              <button
                onClick={() => navigate('/upload-resume')}
                className="px-5 py-2.5 rounded-xl border border-white/10 text-white/70 hover:bg-white/5 transition-all text-sm"
              >
                Re-upload File
              </button>
            </div>
          </div>
        )}

        {stage === 'done' && (
          <>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
              <div>
                <h1 className="font-heading text-2xl font-semibold mb-1">
                  Resume Analysis Results
                </h1>
                <p className="text-white/50 text-sm">
                  {skills.length} skills extracted · Grounded against verified industry benchmarks
                </p>
              </div>

              {/* Tab Switcher */}
              <div className="flex bg-white/5 border border-white/10 rounded-xl p-1 self-start sm:self-auto">
                <button
                  type="button"
                  onClick={() => setActiveTab('skills')}
                  className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${
                    activeTab === 'skills'
                      ? 'bg-accent-400/20 text-accent-300 border border-accent-400/30'
                      : 'text-white/60 hover:text-white'
                  }`}
                >
                  Detected Skills ({skills.length})
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('rag')}
                  className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all flex items-center space-x-1.5 ${
                    activeTab === 'rag'
                      ? 'bg-accent-400/20 text-accent-300 border border-accent-400/30'
                      : 'text-white/60 hover:text-white'
                  }`}
                >
                  <span>RAG Intelligence</span>
                  {ragAnalysis?.semantic_match_score !== undefined && (
                    <span className="px-1.5 py-0.5 rounded-full text-[10px] bg-accent-400/30 text-white font-mono">
                      {Math.round(ragAnalysis.semantic_match_score)}%
                    </span>
                  )}
                </button>
              </div>
            </div>

            {/* TAB 1: DETECTED SKILLS (NLP) */}
            {activeTab === 'skills' && (
              <>
                {skills.length === 0 ? (
                  <p className="text-white/40 text-sm py-8 text-center">
                    No known skills detected. Try uploading a more detailed resume.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {skills.map((skill) => (
                      <div
                        key={skill.id}
                        onClick={() => navigate(`/verify-skill/${skill.id}`)}
                        className="flex items-center justify-between p-4 rounded-xl
                                   bg-white/5 border border-white/10
                                   hover:border-accent-400/30 hover:bg-white/[0.07]
                                   transition-all cursor-pointer"
                      >
                        <div>
                          <p className="font-medium capitalize">{skill.skill_name}</p>
                          <p className={`text-xs mt-0.5 ${confidenceColor(skill.extraction_confidence)}`}>
                            {confidenceLabel(skill.extraction_confidence)}
                          </p>
                        </div>
                        <span className="text-white/30 text-sm">Verify →</span>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}

            {/* TAB 2: RAG SEMANTIC INTELLIGENCE */}
            {activeTab === 'rag' && (
              <div className="space-y-6">
                {ragAnalysis ? (
                  <>
                    {/* Header Score Card */}
                    <div className="p-5 rounded-2xl bg-gradient-to-r from-accent-500/10 via-base-800 to-transparent border border-accent-400/25 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                      <div>
                        <span className="text-xs uppercase tracking-wider text-accent-400 font-mono">Semantic Benchmark Match</span>
                        <h3 className="font-heading text-xl font-bold text-white capitalize mt-0.5">
                          {ragAnalysis.target_career}
                        </h3>
                        <p className="text-xs text-white/50 mt-1">
                          Vector similarity: {(ragAnalysis.cosine_similarity * 100).toFixed(1)}% | Sentence Transformers (384-d)
                        </p>
                      </div>
                      <div className="flex items-center space-x-2">
                        <div className="text-right">
                          <span className="text-2xl font-bold font-mono text-accent-300">
                            {ragAnalysis.semantic_match_score}%
                          </span>
                          <span className="block text-[10px] text-white/40 uppercase">Match Score</span>
                        </div>
                      </div>
                    </div>

                    {/* Explicit Evidence vs Inferred Gaps */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Explicit Skills */}
                      <div className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-2">
                        <div className="flex items-center justify-between border-b border-white/10 pb-2">
                          <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wide">
                            ✓ Explicit Resume Evidence
                          </span>
                          <span className="text-[11px] font-mono text-white/40">
                            {ragAnalysis.explicit_skills?.length || 0} Skills
                          </span>
                        </div>
                        <div className="flex flex-wrap gap-1.5 pt-1">
                          {ragAnalysis.explicit_skills?.map((item) => (
                            <span
                              key={item.skill_name}
                              title={item.evidence}
                              className="px-2.5 py-1 rounded-lg text-xs font-medium bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 capitalize"
                            >
                              {item.skill_name}
                            </span>
                          ))}
                        </div>
                      </div>

                      {/* Missing Benchmark Requirements */}
                      <div className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-2">
                        <div className="flex items-center justify-between border-b border-white/10 pb-2">
                          <span className="text-xs font-semibold text-red-400 uppercase tracking-wide">
                            ○ Missing Benchmark Gaps
                          </span>
                          <span className="text-[11px] font-mono text-white/40">
                            {ragAnalysis.missing_skills?.length || 0} Gaps
                          </span>
                        </div>
                        <div className="flex flex-wrap gap-1.5 pt-1">
                          {ragAnalysis.missing_skills?.slice(0, 8).map((skill) => (
                            <span
                              key={skill}
                              className="px-2.5 py-1 rounded-lg text-xs font-medium bg-red-500/10 text-red-300 border border-red-500/20 capitalize"
                            >
                              {skill}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Grounded AI Evaluation */}
                    {ragAnalysis.explanation && (
                      <div className="p-5 rounded-2xl bg-white/[0.03] border border-white/10 space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-mono uppercase tracking-wider text-accent-300">
                            Grounded Career Synthesis
                          </span>
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-accent-400/10 text-accent-300 border border-accent-400/20 font-mono">
                            Gemini 3.6 Flash + RAG
                          </span>
                        </div>
                        <div className="text-sm text-white/80 leading-relaxed whitespace-pre-line font-sans">
                          {ragAnalysis.explanation}
                        </div>
                      </div>
                    )}

                    {/* Retrieved Sources & Citations */}
                    {ragAnalysis.retrieved_sources?.length > 0 && (
                      <div className="pt-2">
                        <span className="text-[11px] text-white/40 uppercase tracking-wider block mb-2 font-mono">
                          Verified Benchmark Sources
                        </span>
                        <div className="space-y-1.5">
                          {ragAnalysis.retrieved_sources.slice(0, 3).map((src, i) => (
                            <div
                              key={i}
                              className="flex items-center justify-between text-xs px-3 py-2 rounded-lg bg-white/5 border border-white/5 text-white/60"
                            >
                              <span className="truncate pr-2 font-medium text-white/80">{src.title}</span>
                              <span className="text-[10px] text-accent-300/80 truncate font-mono">{src.source}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="py-8 text-center text-white/40">
                    <p className="text-sm">RAG semantic analysis is computing...</p>
                  </div>
                )}
              </div>
            )}

            <div className="flex items-center justify-between pt-6 border-t border-white/10 mt-6">
              <button
                onClick={() => navigate('/skill-gap')}
                className="px-4 py-2.5 rounded-xl border border-accent-400/30 text-accent-400 hover:bg-accent-400/10 transition-all text-xs font-medium"
              >
                Go to Skill Gap Analysis →
              </button>
              <button
                onClick={() => navigate('/dashboard')}
                className="btn-primary text-xs py-2.5 px-6"
              >
                Back to Dashboard
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}