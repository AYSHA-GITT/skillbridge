import { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../services/api';

export default function ProcessResume() {
  const { resumeId } = useParams();
  const navigate = useNavigate();

  const [stage, setStage] = useState('parsing'); // parsing | extracting | done | error
  const [skills, setSkills] = useState([]);
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
            <h1 className="font-heading text-2xl font-semibold mb-1">
              Skills detected
            </h1>
            <p className="text-white/50 text-sm mb-8">
              {skills.length} skills found in your resume
            </p>

            {skills.length === 0 ? (
              <p className="text-white/40 text-sm">
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

            <button
              onClick={() => navigate('/dashboard')}
              className="btn-primary mt-8"
            >
              Back to Dashboard
            </button>
          </>
        )}
      </div>
    </div>
  );
}