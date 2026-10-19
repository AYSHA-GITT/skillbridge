import React, { useState, useEffect, useRef } from 'react';
import {
  TbSparkles,
  TbFileCheck,
  TbFileUpload,
  TbCheck,
  TbX,
  TbDownload,
  TbAlertCircle,
  TbArrowRight,
  TbRefresh,
  TbBriefcase,
  TbListCheck,
  TbCircleCheck,
  TbInfoCircle,
  TbPlus,
  TbTrash,
  TbEye,
  TbFileText,
  TbShieldCheck
} from 'react-icons/tb';
import { skillService } from '../services/skillService';

export default function ResumeOptimizer() {
  // Step / Mode: 'setup' | 'workspace'
  const [mode, setMode] = useState('setup');

  // Input states
  const [sourceType, setSourceType] = useState('upload'); // 'upload' | 'existing'
  const [file, setFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [myResumes, setMyResumes] = useState([]);
  const [selectedResumeId, setSelectedResumeId] = useState('');
  const [careers, setCareers] = useState([]);
  const [selectedCareer, setSelectedCareer] = useState('software engineer');
  const [useCustomJd, setUseCustomJd] = useState(false);
  const [customJd, setCustomJd] = useState('');

  // Execution states
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState('');
  const [error, setError] = useState('');
  const [exporting, setExporting] = useState({ pdf: false, docx: false });
  const [toast, setToast] = useState(null);

  // Results & Workspace
  const [analysis, setAnalysis] = useState(null);
  const [originalSections, setOriginalSections] = useState(null);
  const [editableSections, setEditableSections] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [studentPrompts, setStudentPrompts] = useState([]);
  const [activeTab, setActiveTab] = useState('comparison'); // 'comparison' | 'suggestions' | 'breakdown'
  const [filterType, setFilterType] = useState('all'); // 'all' | 'bullet' | 'summary' | 'skill'

  const fileInputRef = useRef(null);

  // Load initial careers & student's previous resumes
  useEffect(() => {
    loadSetupData();
  }, []);

  const loadSetupData = async () => {
    try {
      const [careersRes, resumesRes] = await Promise.allSettled([
        skillService.getOptimizerCareers(),
        skillService.getOptimizerResumes(),
      ]);

      if (careersRes.status === 'fulfilled' && careersRes.value?.careers) {
        setCareers(careersRes.value.careers);
      }

      if (resumesRes.status === 'fulfilled' && resumesRes.value?.resumes) {
        const list = resumesRes.value.resumes;
        setMyResumes(list);
        if (list.length > 0) {
          setSelectedResumeId(list[0].id);
        }
      }
    } catch (err) {
      console.warn('Initial data load warning:', err);
    }
  };

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4500);
  };

  // Drag & drop handlers
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelected = (selectedFile) => {
    const ext = selectedFile.name.split('.').pop().toLowerCase();
    if (!['pdf', 'docx'].includes(ext)) {
      setError('Please upload a PDF (.pdf) or Word (.docx) document.');
      return;
    }
    if (selectedFile.size > 10 * 1024 * 1024) {
      setError('File size exceeds the 10MB limit.');
      return;
    }
    setError('');
    setFile(selectedFile);
  };

  // Run Optimization Pipeline
  const handleRunOptimization = async () => {
    setError('');
    setLoading(true);

    const steps = [
      'Parsing resume structure & contact information...',
      'Auditing skills against target role requirements...',
      'Calculating deterministic ATS job-match score...',
      'Applying STAR/XYZ impact enhancements...',
      'Finalizing editable side-by-side workspace...'
    ];

    let stepIndex = 0;
    setLoadingStep(steps[0]);
    const stepInterval = setInterval(() => {
      stepIndex = (stepIndex + 1) % steps.length;
      setLoadingStep(steps[stepIndex]);
    }, 1800);

    try {
      const formData = new FormData();

      if (sourceType === 'upload') {
        if (!file) {
          throw new Error('Please select or upload a resume file first.');
        }
        formData.append('resume', file);
      } else {
        if (!selectedResumeId) {
          throw new Error('Please choose an existing resume from your profile.');
        }
        formData.append('resume_id', selectedResumeId);
      }

      if (useCustomJd && customJd.trim()) {
        formData.append('job_description', customJd.trim());
      } else {
        formData.append('target_career', selectedCareer);
      }

      const res = await skillService.analyzeResumeOptimizer(formData);

      clearInterval(stepInterval);
      setAnalysis(res.match_analysis);
      setOriginalSections(res.original_sections);
      setEditableSections(res.optimized_sections || res.original_sections);
      setSuggestions(res.suggestions || []);
      setStudentPrompts(res.student_prompts || []);
      setMode('workspace');
      showToast('Resume analyzed and optimization workspace ready!', 'success');
    } catch (err) {
      clearInterval(stepInterval);
      const msg = err.response?.data?.error || err.message || 'Failed to analyze resume. Please try again.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  // Suggestion actions: Accept / Reject
  const handleToggleSuggestion = (sugId, action) => {
    setSuggestions((prev) =>
      prev.map((s) => {
        if (s.id !== sugId) return s;
        const newStatus = action === 'accept' ? 'accepted' : 'rejected';

        // Apply change to editable sections
        if (s.type === 'summary_rewrite') {
          setEditableSections((cur) => ({
            ...cur,
            summary: newStatus === 'accepted' ? s.improved : s.original,
          }));
        } else if (s.type === 'bullet_enhancement') {
          const sec = (s.section || '').toLowerCase();
          const iIdx = s.item_index || 0;
          const bIdx = s.bullet_index || 0;

          setEditableSections((cur) => {
            const next = JSON.parse(JSON.stringify(cur));
            if (sec.includes('experience') && next.experience && next.experience[iIdx]) {
              const bullets = next.experience[iIdx].bullets || [];
              if (bullets[bIdx] !== undefined) {
                bullets[bIdx] = newStatus === 'accepted' ? s.improved : s.original;
              }
            } else if (sec.includes('project') && next.projects && next.projects[iIdx]) {
              const bullets = next.projects[iIdx].bullets || [];
              if (bullets[bIdx] !== undefined) {
                bullets[bIdx] = newStatus === 'accepted' ? s.improved : s.original;
              }
            }
            return next;
          });
        } else if (s.type === 'missing_skill_prompt' && s.skill_to_add) {
          if (newStatus === 'accepted') {
            setEditableSections((cur) => {
              const currentSkills = cur.skills || [];
              if (!currentSkills.some((k) => k.toLowerCase() === s.skill_to_add.toLowerCase())) {
                return { ...cur, skills: [...currentSkills, s.skill_to_add] };
              }
              return cur;
            });
          }
        }

        return { ...s, status: newStatus };
      })
    );
  };

  // 1-Click Accept All
  const handleAcceptAll = () => {
    suggestions.forEach((s) => {
      if (s.status !== 'accepted') {
        handleToggleSuggestion(s.id, 'accept');
      }
    });
    showToast('Applied all suggested improvements to your optimized resume!', 'success');
  };

  // Section Live Editors
  const handleUpdateContact = (field, value) => {
    setEditableSections((prev) => ({
      ...prev,
      contact: { ...prev.contact, [field]: value }
    }));
  };

  const handleUpdateSummary = (value) => {
    setEditableSections((prev) => ({
      ...prev,
      summary: value
    }));
  };

  const handleUpdateExperienceBullet = (expIndex, bulletIndex, value) => {
    setEditableSections((prev) => {
      const next = JSON.parse(JSON.stringify(prev));
      if (next.experience[expIndex]?.bullets?.[bulletIndex] !== undefined) {
        next.experience[expIndex].bullets[bulletIndex] = value;
      }
      return next;
    });
  };

  const handleAddExperienceBullet = (expIndex) => {
    setEditableSections((prev) => {
      const next = JSON.parse(JSON.stringify(prev));
      if (next.experience[expIndex]) {
        next.experience[expIndex].bullets = next.experience[expIndex].bullets || [];
        next.experience[expIndex].bullets.push('[Action Verb] [Context / Task] resulting in [Quantified Outcome].');
      }
      return next;
    });
  };

  const handleRemoveExperienceBullet = (expIndex, bulletIndex) => {
    setEditableSections((prev) => {
      const next = JSON.parse(JSON.stringify(prev));
      if (next.experience[expIndex]?.bullets) {
        next.experience[expIndex].bullets.splice(bulletIndex, 1);
      }
      return next;
    });
  };

  const handleUpdateSkills = (value) => {
    const list = value.split(',').map((s) => s.trim()).filter(Boolean);
    setEditableSections((prev) => ({
      ...prev,
      skills: list
    }));
  };

  // Export handlers
  const handleExport = async (format) => {
    if (!editableSections) return;
    setExporting((prev) => ({ ...prev, [format]: true }));

    const candidateName = (editableSections.contact?.name || 'Resume').replace(/[^a-zA-Z0-9]/g, '_');
    const targetName = (selectedCareer || 'Optimized').replace(/[^a-zA-Z0-9]/g, '_');
    const filename = `${candidateName}_${targetName}_Resume.${format}`;

    try {
      let blob;
      if (format === 'pdf') {
        blob = await skillService.exportOptimizerPdf(editableSections, filename);
      } else {
        blob = await skillService.exportOptimizerDocx(editableSections, filename);
      }

      // Trigger native browser download
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      showToast(`Downloaded ${filename} successfully!`, 'success');
    } catch (err) {
      console.error(`Export ${format} error:`, err);
      showToast(`Failed to export ${format.toUpperCase()}. Please try again.`, 'error');
    } finally {
      setExporting((prev) => ({ ...prev, [format]: false }));
    }
  };

  return (
    <div className="space-y-6 pb-16">
      {/* Toast Notification */}
      {toast && (
        <div
          className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl shadow-2xl flex items-center space-x-3 text-xs font-medium border backdrop-blur-md transition-all ${
            toast.type === 'success'
              ? 'bg-emerald-950/90 text-emerald-200 border-emerald-500/40 shadow-emerald-950/50'
              : 'bg-rose-950/90 text-rose-200 border-rose-500/40 shadow-rose-950/50'
          }`}
        >
          {toast.type === 'success' ? <TbCheck className="w-4 h-4 text-emerald-400" /> : <TbAlertCircle className="w-4 h-4 text-rose-400" />}
          <span>{toast.message}</span>
        </div>
      )}

      {/* Header Banner */}
      <div className="surface p-6 rounded-2xl relative overflow-hidden border border-teal-500/30">
        <div className="absolute top-0 right-0 w-96 h-96 bg-teal-500/10 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 relative z-10">
          <div>
            <div className="flex items-center space-x-2.5 text-accent-400 mb-1.5">
              <span className="p-1.5 rounded-lg bg-accent-500/15 border border-accent-400/30">
                <TbSparkles className="w-5 h-5 text-accent-300" />
              </span>
              <span className="text-xs font-mono font-semibold tracking-wider uppercase">
                SkillLens AI Studio
              </span>
            </div>
            <h1 className="text-2xl font-bold font-heading text-white">
              AI Resume Optimizer
            </h1>
            <p className="text-xs text-white/60 mt-1 max-w-2xl leading-relaxed">
              Transform your resume with deterministic ATS job-match scoring, passive-to-active STAR bullet rewrites,
              and professional PDF/DOCX downloads with zero fabricated facts.
            </p>
          </div>

          {mode === 'workspace' && (
            <div className="flex items-center space-x-2.5 flex-wrap gap-y-2">
              <button
                type="button"
                onClick={() => setMode('setup')}
                className="btn-ghost flex items-center space-x-1.5 text-xs py-2 px-3"
              >
                <TbRefresh className="w-3.5 h-3.5" />
                <span>New Optimization</span>
              </button>

              <button
                type="button"
                onClick={() => handleExport('docx')}
                disabled={exporting.docx}
                className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-base-800 hover:bg-base-700 text-teal-300 border border-teal-500/30 flex items-center space-x-1.5 transition-all"
              >
                <TbDownload className="w-3.5 h-3.5" />
                <span>{exporting.docx ? 'Exporting...' : 'DOCX'}</span>
              </button>

              <button
                type="button"
                onClick={() => handleExport('pdf')}
                disabled={exporting.pdf}
                className="btn-primary !w-auto flex items-center space-x-1.5 text-xs py-2 px-4"
              >
                <TbDownload className="w-4 h-4" />
                <span>{exporting.pdf ? 'Generating...' : 'Download PDF'}</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          MODE 1: SETUP & CONFIGURATION
      ───────────────────────────────────────────────────────────── */}
      {mode === 'setup' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Resume Source */}
          <div className="lg:col-span-6 space-y-6">
            <div className="surface p-5 rounded-2xl border border-base-700/60 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold text-white flex items-center space-x-2">
                  <TbFileText className="w-4 h-4 text-teal-400" />
                  <span>1. Select Resume Source</span>
                </h2>
                <div className="flex p-0.5 rounded-xl bg-base-900 border border-base-700 text-[11px] font-medium">
                  <button
                    type="button"
                    onClick={() => setSourceType('upload')}
                    className={`px-3 py-1 rounded-lg transition-all ${
                      sourceType === 'upload'
                        ? 'bg-teal-500/20 text-teal-300 border border-teal-400/30'
                        : 'text-white/50 hover:text-white'
                    }`}
                  >
                    Upload File
                  </button>
                  <button
                    type="button"
                    onClick={() => setSourceType('existing')}
                    className={`px-3 py-1 rounded-lg transition-all ${
                      sourceType === 'existing'
                        ? 'bg-teal-500/20 text-teal-300 border border-teal-400/30'
                        : 'text-white/50 hover:text-white'
                    }`}
                  >
                    Existing Resumes ({myResumes.length})
                  </button>
                </div>
              </div>

              {sourceType === 'upload' ? (
                <div>
                  <div
                    onDragEnter={handleDrag}
                    onDragLeave={handleDrag}
                    onDragOver={handleDrag}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                    className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition-all ${
                      dragActive
                        ? 'border-teal-400 bg-teal-950/30'
                        : file
                        ? 'border-emerald-500/40 bg-emerald-950/10'
                        : 'border-base-700 hover:border-teal-500/40 bg-base-900/40'
                    }`}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".pdf,.docx"
                      onChange={(e) => e.target.files?.[0] && handleFileSelected(e.target.files[0])}
                      className="hidden"
                    />
                    <div className="w-12 h-12 rounded-2xl bg-teal-500/10 border border-teal-400/20 text-teal-300 flex items-center justify-center mx-auto mb-3">
                      {file ? <TbFileCheck className="w-6 h-6 text-emerald-400" /> : <TbFileUpload className="w-6 h-6" />}
                    </div>
                    {file ? (
                      <div>
                        <p className="text-sm font-semibold text-emerald-300">{file.name}</p>
                        <p className="text-[11px] text-white/50 mt-1">
                          {(file.size / (1024 * 1024)).toFixed(2)} MB • Ready to analyze
                        </p>
                      </div>
                    ) : (
                      <div>
                        <p className="text-xs font-medium text-white">
                          Drag and drop your resume here, or <span className="text-teal-400 underline">browse</span>
                        </p>
                        <p className="text-[10px] text-white/40 mt-1 font-mono">
                          Supports PDF and DOCX (Max 10MB)
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                  {myResumes.length === 0 ? (
                    <div className="p-6 text-center text-xs text-white/40 border border-base-700/60 rounded-xl">
                      No previous resumes found. Switch to upload tab to add one.
                    </div>
                  ) : (
                    myResumes.map((r) => (
                      <div
                        key={r.id}
                        onClick={() => setSelectedResumeId(r.id)}
                        className={`p-3.5 rounded-xl border text-left cursor-pointer transition-all flex items-center justify-between ${
                          selectedResumeId === r.id
                            ? 'bg-teal-500/15 border-teal-400/40 text-teal-200'
                            : 'bg-base-900/50 border-base-700/60 hover:border-base-600 text-white/70'
                        }`}
                      >
                        <div className="flex items-center space-x-3">
                          <TbFileText className="w-4 h-4 text-teal-400 flex-shrink-0" />
                          <div>
                            <p className="text-xs font-semibold text-white truncate max-w-[220px]">
                              {r.original_filename}
                            </p>
                            <p className="text-[10px] text-white/40 font-mono">
                              Uploaded: {r.uploaded_on ? new Date(r.uploaded_on).toLocaleDateString() : 'N/A'}
                            </p>
                          </div>
                        </div>
                        {r.is_latest && (
                          <span className="text-[9px] font-mono uppercase px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-400/30">
                            Current
                          </span>
                        )}
                      </div>
                    ))
                  )}
                </div>
              )}

              {/* Data isolation reassurance */}
              <div className="flex items-center space-x-2 text-[10px] text-white/40 pt-2 border-t border-base-700/60">
                <TbShieldCheck className="w-3.5 h-3.5 text-teal-400 flex-shrink-0" />
                <span>Your resume files remain strictly private and accessible only to your account.</span>
              </div>
            </div>
          </div>

          {/* Right Column: Target Career or Custom JD */}
          <div className="lg:col-span-6 space-y-6">
            <div className="surface p-5 rounded-2xl border border-base-700/60 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold text-white flex items-center space-x-2">
                  <TbBriefcase className="w-4 h-4 text-teal-400" />
                  <span>2. Target Role / Job Description</span>
                </h2>
                <div className="flex p-0.5 rounded-xl bg-base-900 border border-base-700 text-[11px] font-medium">
                  <button
                    type="button"
                    onClick={() => setUseCustomJd(false)}
                    className={`px-3 py-1 rounded-lg transition-all ${
                      !useCustomJd
                        ? 'bg-teal-500/20 text-teal-300 border border-teal-400/30'
                        : 'text-white/50 hover:text-white'
                    }`}
                  >
                    Target Career
                  </button>
                  <button
                    type="button"
                    onClick={() => setUseCustomJd(true)}
                    className={`px-3 py-1 rounded-lg transition-all ${
                      useCustomJd
                        ? 'bg-teal-500/20 text-teal-300 border border-teal-400/30'
                        : 'text-white/50 hover:text-white'
                    }`}
                  >
                    Custom JD
                  </button>
                </div>
              </div>

              {!useCustomJd ? (
                <div className="space-y-3">
                  <p className="text-[11px] text-white/50">
                    Choose an industry track to match against curated required and nice-to-have competencies:
                  </p>
                  <div className="grid grid-cols-2 gap-2 max-h-56 overflow-y-auto pr-1">
                    {careers.map((c) => (
                      <button
                        key={c.id}
                        type="button"
                        onClick={() => setSelectedCareer(c.id)}
                        className={`p-2.5 rounded-xl border text-left transition-all ${
                          selectedCareer === c.id
                            ? 'bg-teal-500/20 border-teal-400/40 text-teal-200 shadow-sm'
                            : 'bg-base-900/60 border-base-700/60 hover:border-base-600 text-white/60'
                        }`}
                      >
                        <p className="text-xs font-semibold text-white">{c.title}</p>
                        <p className="text-[10px] text-white/40 mt-0.5 truncate">
                          {c.required.slice(0, 3).join(', ')}...
                        </p>
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  <label className="text-[11px] text-white/60 block">
                    Paste Job Description / Internship Posting:
                  </label>
                  <textarea
                    rows={7}
                    value={customJd}
                    onChange={(e) => setCustomJd(e.target.value)}
                    placeholder="Paste job posting text here (requirements, qualifications, tech stack)..."
                    className="input-field text-xs font-mono leading-relaxed"
                  />
                  <p className="text-[10px] text-white/40">
                    The optimizer will extract core technical skills and compare them deterministically against your resume.
                  </p>
                </div>
              )}

              {/* Error display */}
              {error && (
                <div className="p-3 rounded-xl bg-rose-950/30 border border-rose-500/30 text-rose-300 text-xs flex items-center space-x-2">
                  <TbAlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              {/* Launch Optimization Button */}
              <button
                type="button"
                onClick={handleRunOptimization}
                disabled={loading}
                className="btn-primary flex items-center justify-center space-x-2 text-sm font-bold py-3.5 mt-2"
              >
                {loading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-base-950 border-t-transparent rounded-full animate-spin" />
                    <span>Analyzing & Enhancing...</span>
                  </>
                ) : (
                  <>
                    <TbSparkles className="w-4 h-4" />
                    <span>Optimize My Resume</span>
                    <TbArrowRight className="w-4 h-4 ml-1" />
                  </>
                )}
              </button>

              {loading && (
                <div className="p-3 rounded-xl bg-teal-950/20 border border-teal-500/20 text-center space-y-1.5 animate-pulse">
                  <p className="text-xs text-teal-300 font-mono font-medium">{loadingStep}</p>
                  <p className="text-[10px] text-white/40">
                    Checking keywords, converting weak verbs, and checking ATS standards...
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          MODE 2: OPTIMIZATION STUDIO (INTERACTIVE WORKSPACE)
      ───────────────────────────────────────────────────────────── */}
      {mode === 'workspace' && analysis && (
        <div className="space-y-6">
          {/* Top ATS Score & Metric Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
            {/* Score Ring / Card */}
            <div className="md:col-span-4 surface p-5 rounded-2xl border border-teal-500/30 flex items-center space-x-5">
              <div className="relative w-24 h-24 flex-shrink-0 flex items-center justify-center">
                <svg className="w-24 h-24 -rotate-90">
                  <circle
                    cx="48"
                    cy="48"
                    r="40"
                    stroke="currentColor"
                    strokeWidth="7"
                    fill="transparent"
                    className="text-base-800"
                  />
                  <circle
                    cx="48"
                    cy="48"
                    r="40"
                    stroke="currentColor"
                    strokeWidth="7"
                    fill="transparent"
                    strokeDasharray="251.2"
                    strokeDashoffset={251.2 - (251.2 * analysis.match_score) / 100}
                    className={`${
                      analysis.match_score >= 75
                        ? 'text-emerald-400'
                        : analysis.match_score >= 50
                        ? 'text-amber-400'
                        : 'text-rose-400'
                    } transition-all duration-1000 ease-out`}
                  />
                </svg>
                <div className="absolute flex flex-col items-center">
                  <span className="text-2xl font-bold font-heading text-white">
                    {Math.round(analysis.match_score)}%
                  </span>
                  <span className="text-[9px] font-mono uppercase text-white/40">Match</span>
                </div>
              </div>

              <div className="space-y-1">
                <div className="flex items-center space-x-1.5">
                  <span className="text-xs font-semibold text-white">
                    ATS Job-Match Score
                  </span>
                </div>
                <p className="text-[11px] text-white/50 leading-snug">
                  Target: <span className="text-teal-300 font-semibold">{analysis.target_career.title ? analysis.target_career.title() : analysis.target_career}</span>
                </p>
                <div className="text-[10px] text-white/40 space-y-0.5 pt-1">
                  <div className="flex justify-between">
                    <span>Required:</span>
                    <span className="font-mono text-teal-300">{analysis.score_breakdown?.required_skills_score || 0} / 55</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Preferred:</span>
                    <span className="font-mono text-teal-300">{analysis.score_breakdown?.preferred_skills_score || 0} / 25</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Formatting:</span>
                    <span className="font-mono text-teal-300">{analysis.score_breakdown?.formatting_score || 0} / 20</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Matched & Missing Skills Snapshot */}
            <div className="md:col-span-8 surface p-5 rounded-2xl border border-base-700/60 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-xs font-semibold text-white flex items-center space-x-2">
                    <TbListCheck className="w-4 h-4 text-teal-400" />
                    <span>Skills Competency Matrix</span>
                  </h3>
                  <span className="text-[10px] font-mono text-white/40">
                    {analysis.matched_skills.length} Matched • {analysis.missing_required_skills.length} Missing
                  </span>
                </div>

                <div className="space-y-2">
                  {/* Matched Pills */}
                  <div className="flex flex-wrap gap-1.5 items-center">
                    <span className="text-[10px] text-emerald-400 font-mono font-medium mr-1">Matched:</span>
                    {analysis.matched_skills.length > 0 ? (
                      analysis.matched_skills.map((s) => (
                        <span
                          key={s}
                          className="px-2 py-0.5 rounded-lg text-[10px] font-medium bg-emerald-950/40 text-emerald-300 border border-emerald-500/30 flex items-center space-x-1"
                        >
                          <TbCheck className="w-2.5 h-2.5" />
                          <span>{s}</span>
                        </span>
                      ))
                    ) : (
                      <span className="text-[11px] text-white/30 italic">No direct matches found</span>
                    )}
                  </div>

                  {/* Missing Required Skills */}
                  <div className="flex flex-wrap gap-1.5 items-center">
                    <span className="text-[10px] text-rose-400 font-mono font-medium mr-1">Missing Core:</span>
                    {analysis.missing_required_skills.length > 0 ? (
                      analysis.missing_required_skills.map((s) => (
                        <span
                          key={s}
                          className="px-2 py-0.5 rounded-lg text-[10px] font-medium bg-rose-950/40 text-rose-300 border border-rose-500/30"
                        >
                          {s}
                        </span>
                      ))
                    ) : (
                      <span className="text-[10px] text-emerald-400 font-mono">
                        All core required competencies covered!
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Formatting & Anti-Hallucination Reassurance Notice */}
              <div className="pt-2.5 mt-2 border-t border-base-700/60 flex items-center justify-between text-[10px] text-white/40">
                <span className="flex items-center space-x-1 text-teal-300">
                  <TbCircleCheck className="w-3.5 h-3.5 text-teal-400" />
                  <span>Deterministic score calculated in Python • Zero AI invented statistics</span>
                </span>
                <span className="font-mono text-white/50">
                  {analysis.weak_bullet_points?.length || 0} weak bullet(s) flagged
                </span>
              </div>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="flex items-center justify-between border-b border-base-700/60 pb-2">
            <div className="flex space-x-2">
              <button
                type="button"
                onClick={() => setActiveTab('comparison')}
                className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all flex items-center space-x-2 ${
                  activeTab === 'comparison'
                    ? 'bg-teal-500/20 text-teal-300 border border-teal-400/30 shadow-glow'
                    : 'text-white/60 hover:text-white'
                }`}
              >
                <TbEye className="w-4 h-4" />
                <span>Side-by-Side Live Editor</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('suggestions')}
                className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all flex items-center space-x-2 ${
                  activeTab === 'suggestions'
                    ? 'bg-teal-500/20 text-teal-300 border border-teal-400/30 shadow-glow'
                    : 'text-white/60 hover:text-white'
                }`}
              >
                <TbSparkles className="w-4 h-4" />
                <span>AI Improvement Cards ({suggestions.length})</span>
              </button>
            </div>

            {suggestions.length > 0 && (
              <button
                type="button"
                onClick={handleAcceptAll}
                className="px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-emerald-950/50 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-900/50 transition-all flex items-center space-x-1.5"
              >
                <TbCheck className="w-3.5 h-3.5" />
                <span>Accept All ({suggestions.filter((s) => s.status !== 'accepted').length})</span>
              </button>
            )}
          </div>

          {/* Student Required Input Notice */}
          {studentPrompts && studentPrompts.length > 0 && (
            <div className="surface p-3.5 rounded-xl border border-amber-500/30 bg-amber-950/20 flex items-start space-x-3 text-xs">
              <TbAlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="font-semibold text-amber-200">
                  Action Required: Information You Need to Provide ({studentPrompts.length} items)
                </p>
                <p className="text-[11px] text-amber-300/80 leading-relaxed">
                  SkillLens AI strictly avoids inventing metrics, qualifications, or company data. Please fill in the bracketed placeholders <span className="font-mono bg-amber-900/40 px-1 py-0.5 rounded">[Quantify impact: ...]</span> with your real achievements.
                </p>
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {studentPrompts.map((p, pIdx) => (
                    <span key={pIdx} className="px-2 py-0.5 rounded bg-amber-900/40 border border-amber-500/30 text-[10px] text-amber-200 font-mono">
                      {p.target || p.prompt}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ─────────────────────────────────────────────────────────────
              TAB 1: SIDE-BY-SIDE RESUME WORKSPACE
          ───────────────────────────────────────────────────────────── */}
          {activeTab === 'comparison' && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Left Pane: Original Resume (Read-only Reference) */}
              <div className="lg:col-span-6 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-mono font-semibold uppercase text-white/50 flex items-center space-x-2">
                    <span className="w-2 h-2 rounded-full bg-white/40" />
                    <span>Original Resume (Read-Only)</span>
                  </h3>
                  <span className="text-[10px] text-white/40 font-mono">Original kept unchanged</span>
                </div>

                <div className="surface p-5 rounded-2xl border border-base-700/60 space-y-5 bg-base-900/40 max-h-[700px] overflow-y-auto font-body text-xs leading-relaxed">
                  {/* Contact Header */}
                  <div className="border-b border-base-700/60 pb-3">
                    <h4 className="text-base font-bold text-white">
                      {originalSections?.contact?.name || 'Candidate Name'}
                    </h4>
                    <p className="text-[11px] text-white/50 mt-0.5">
                      {[
                        originalSections?.contact?.phone,
                        originalSections?.contact?.email,
                        originalSections?.contact?.location,
                        originalSections?.contact?.linkedin,
                        originalSections?.contact?.github
                      ].filter(Boolean).join(' | ')}
                    </p>
                  </div>

                  {/* Summary */}
                  <div>
                    <h5 className="text-[11px] font-mono uppercase font-semibold text-teal-400/80 mb-1">
                      Professional Summary
                    </h5>
                    <p className="text-white/70 italic">
                      {originalSections?.summary || '(No summary provided)'}
                    </p>
                  </div>

                  {/* Skills */}
                  <div>
                    <h5 className="text-[11px] font-mono uppercase font-semibold text-teal-400/80 mb-1">
                      Skills
                    </h5>
                    <div className="flex flex-wrap gap-1">
                      {(originalSections?.skills || []).map((sk) => (
                        <span key={sk} className="px-2 py-0.5 rounded bg-base-800 text-white/60 text-[10px]">
                          {sk}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Experience */}
                  <div>
                    <h5 className="text-[11px] font-mono uppercase font-semibold text-teal-400/80 mb-1">
                      Experience
                    </h5>
                    {(originalSections?.experience || []).length === 0 ? (
                      <p className="text-white/40 italic">No experience listed</p>
                    ) : (
                      originalSections.experience.map((exp, idx) => (
                        <div key={idx} className="mb-3 space-y-1">
                          <p className="font-semibold text-white/90">
                            {exp.role} {exp.company ? `— ${exp.company}` : ''}
                          </p>
                          <ul className="list-disc list-inside space-y-1 text-white/60 pl-1">
                            {(exp.bullets || []).map((b, bIdx) => (
                              <li key={bIdx}>{b}</li>
                            ))}
                          </ul>
                        </div>
                      ))
                    )}
                  </div>

                  {/* Projects */}
                  <div>
                    <h5 className="text-[11px] font-mono uppercase font-semibold text-teal-400/80 mb-1">
                      Projects
                    </h5>
                    {(originalSections?.projects || []).map((proj, idx) => (
                      <div key={idx} className="mb-2 space-y-1">
                        <p className="font-semibold text-white/90">
                          {proj.name} {proj.technologies ? `| ${proj.technologies}` : ''}
                        </p>
                        <ul className="list-disc list-inside space-y-0.5 text-white/60 pl-1">
                          {(proj.bullets || []).map((b, bIdx) => (
                            <li key={bIdx}>{b}</li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>

                  {/* Education */}
                  <div>
                    <h5 className="text-[11px] font-mono uppercase font-semibold text-teal-400/80 mb-1">
                      Education
                    </h5>
                    {(originalSections?.education || []).map((edu, idx) => (
                      <div key={idx}>
                        <span className="font-semibold text-white">{edu.degree}</span>
                        {edu.institution ? ` — ${edu.institution}` : ''}
                        {edu.year ? ` (${edu.year})` : ''}
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Right Pane: Live Optimized Resume (Interactive & Editable) */}
              <div className="lg:col-span-6 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-mono font-semibold uppercase text-teal-300 flex items-center space-x-2">
                    <span className="w-2 h-2 rounded-full bg-teal-400 animate-pulse" />
                    <span>Optimized & Editable Resume (Final Draft)</span>
                  </h3>
                  <span className="text-[10px] text-teal-400 font-mono">Directly downloads to PDF/DOCX</span>
                </div>

                <div className="surface p-5 rounded-2xl border border-teal-500/40 space-y-5 max-h-[700px] overflow-y-auto font-body text-xs leading-relaxed bg-base-900/80">
                  {/* Contact Header Inputs */}
                  <div className="space-y-2 border-b border-base-700/60 pb-3">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-mono uppercase text-teal-400 font-semibold">
                        Contact Details
                      </span>
                      <span className="text-[10px] text-white/40">Editable</span>
                    </div>
                    <input
                      type="text"
                      value={editableSections?.contact?.name || ''}
                      onChange={(e) => handleUpdateContact('name', e.target.value)}
                      placeholder="Candidate Full Name"
                      className="w-full text-base font-bold bg-transparent border-b border-base-700 focus:border-teal-400 focus:outline-none text-white py-1"
                    />
                    <div className="grid grid-cols-2 gap-2 pt-1">
                      <input
                        type="text"
                        value={editableSections?.contact?.email || ''}
                        onChange={(e) => handleUpdateContact('email', e.target.value)}
                        placeholder="Email"
                        className="input-field !py-1.5 text-[11px]"
                      />
                      <input
                        type="text"
                        value={editableSections?.contact?.phone || ''}
                        onChange={(e) => handleUpdateContact('phone', e.target.value)}
                        placeholder="Phone"
                        className="input-field !py-1.5 text-[11px]"
                      />
                      <input
                        type="text"
                        value={editableSections?.contact?.linkedin || ''}
                        onChange={(e) => handleUpdateContact('linkedin', e.target.value)}
                        placeholder="LinkedIn URL"
                        className="input-field !py-1.5 text-[11px]"
                      />
                      <input
                        type="text"
                        value={editableSections?.contact?.github || ''}
                        onChange={(e) => handleUpdateContact('github', e.target.value)}
                        placeholder="GitHub URL"
                        className="input-field !py-1.5 text-[11px]"
                      />
                    </div>
                  </div>

                  {/* Executive Summary Editor */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <h5 className="text-[11px] font-mono uppercase font-semibold text-teal-400">
                        Executive Summary
                      </h5>
                      <span className="text-[10px] text-teal-300 font-mono">Tailored for {selectedCareer}</span>
                    </div>
                    <textarea
                      rows={3}
                      value={editableSections?.summary || ''}
                      onChange={(e) => handleUpdateSummary(e.target.value)}
                      className="input-field text-xs leading-relaxed"
                    />
                  </div>

                  {/* Skills Editor */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <h5 className="text-[11px] font-mono uppercase font-semibold text-teal-400">
                        Technical Skills (Comma-separated)
                      </h5>
                      <span className="text-[10px] text-white/40">{(editableSections?.skills || []).length} skills</span>
                    </div>
                    <input
                      type="text"
                      value={(editableSections?.skills || []).join(', ')}
                      onChange={(e) => handleUpdateSkills(e.target.value)}
                      className="input-field text-xs font-mono"
                    />
                  </div>

                  {/* Experience Bullet Editors */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h5 className="text-[11px] font-mono uppercase font-semibold text-teal-400">
                        Work Experience Bullets
                      </h5>
                    </div>

                    {(editableSections?.experience || []).map((exp, expIdx) => (
                      <div key={expIdx} className="p-3.5 rounded-xl bg-base-800/60 border border-base-700/60 space-y-2.5">
                        <div className="flex items-center justify-between">
                          <p className="font-semibold text-white text-xs">
                            {exp.role} {exp.company ? `— ${exp.company}` : ''}
                          </p>
                          <span className="text-[10px] text-white/40">{exp.period || ''}</span>
                        </div>

                        <div className="space-y-2">
                          {(exp.bullets || []).map((bullet, bIdx) => (
                            <div key={bIdx} className="flex items-start space-x-2">
                              <span className="text-teal-400 mt-2 font-bold">•</span>
                              <div className="flex-1">
                                <textarea
                                  rows={2}
                                  value={bullet}
                                  onChange={(e) => handleUpdateExperienceBullet(expIdx, bIdx, e.target.value)}
                                  className={`input-field !py-1.5 text-xs font-body leading-snug ${
                                    bullet.includes('[Quantify')
                                      ? 'border-amber-400/50 bg-amber-950/20 text-amber-100'
                                      : ''
                                  }`}
                                />
                                {bullet.includes('[Quantify') && (
                                  <p className="text-[10px] text-amber-300 font-mono mt-0.5 flex items-center space-x-1">
                                    <TbAlertCircle className="w-3 h-3 flex-shrink-0" />
                                    <span>Please replace bracketed text with your real metric before final download</span>
                                  </p>
                                )}
                              </div>
                              <button
                                type="button"
                                onClick={() => handleRemoveExperienceBullet(expIdx, bIdx)}
                                className="text-white/30 hover:text-rose-400 p-1.5 transition-all mt-1"
                                title="Remove bullet"
                              >
                                <TbTrash className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          ))}
                        </div>

                        <button
                          type="button"
                          onClick={() => handleAddExperienceBullet(expIdx)}
                          className="text-[11px] text-teal-400 hover:text-teal-300 flex items-center space-x-1 pt-1 font-medium"
                        >
                          <TbPlus className="w-3.5 h-3.5" />
                          <span>Add Bullet Point</span>
                        </button>
                      </div>
                    ))}
                  </div>

                  {/* Projects View */}
                  <div className="space-y-2">
                    <h5 className="text-[11px] font-mono uppercase font-semibold text-teal-400">
                      Projects & Education
                    </h5>
                    {(editableSections?.projects || []).map((proj, idx) => (
                      <div key={idx} className="p-2.5 rounded-lg bg-base-800/40 border border-base-700/60 text-xs">
                        <span className="font-semibold text-white">{proj.name}</span>
                        {proj.technologies ? <span className="text-teal-300 ml-2 font-mono">({proj.technologies})</span> : ''}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ─────────────────────────────────────────────────────────────
              TAB 2: AI IMPROVEMENT SUGGESTION CARDS
          ───────────────────────────────────────────────────────────── */}
          {activeTab === 'suggestions' && (
            <div className="space-y-4">
              {/* Category Filter Pills */}
              <div className="flex items-center space-x-2 pb-2">
                <span className="text-xs text-white/50 mr-1">Filter:</span>
                {['all', 'summary', 'bullet', 'skill'].map((cat) => (
                  <button
                    key={cat}
                    type="button"
                    onClick={() => setFilterType(cat)}
                    className={`px-3 py-1 rounded-xl text-xs font-medium capitalize transition-all ${
                      filterType === cat
                        ? 'bg-teal-500/20 text-teal-300 border border-teal-400/30'
                        : 'text-white/50 hover:text-white bg-base-900 border border-base-700'
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>

              {/* Suggestions Cards List */}
              <div className="grid grid-cols-1 gap-4">
                {suggestions
                  .filter((s) => (filterType === 'all' ? true : s.type.includes(filterType)))
                  .map((sug) => {
                    const isAccepted = sug.status === 'accepted';
                    const isRejected = sug.status === 'rejected';

                    return (
                      <div
                        key={sug.id}
                        className={`surface p-5 rounded-2xl border transition-all ${
                          isAccepted
                            ? 'border-emerald-500/40 bg-emerald-950/10'
                            : isRejected
                            ? 'border-base-700/50 opacity-60'
                            : 'border-base-700/70 hover:border-teal-500/40'
                        }`}
                      >
                        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-3">
                          <div className="flex items-center space-x-2">
                            <span className="px-2 py-0.5 rounded-full text-[9px] font-mono uppercase bg-teal-500/15 text-teal-300 border border-teal-400/30">
                              {sug.type.replace('_', ' ')}
                            </span>
                            <span className="text-xs font-semibold text-white">
                              {sug.section.title ? sug.section.title() : sug.section}
                            </span>
                          </div>

                          <div className="flex items-center space-x-2">
                            <button
                              type="button"
                              onClick={() => handleToggleSuggestion(sug.id, 'reject')}
                              className={`px-3 py-1 rounded-xl text-xs font-medium transition-all flex items-center space-x-1 ${
                                isRejected
                                  ? 'bg-rose-950 text-rose-300 border border-rose-500/40'
                                  : 'text-white/50 hover:text-white hover:bg-white/5'
                              }`}
                            >
                              <TbX className="w-3.5 h-3.5" />
                              <span>Reject</span>
                            </button>

                            <button
                              type="button"
                              onClick={() => handleToggleSuggestion(sug.id, 'accept')}
                              className={`px-3.5 py-1 rounded-xl text-xs font-semibold transition-all flex items-center space-x-1 ${
                                isAccepted
                                  ? 'bg-emerald-500 text-base-950 shadow-glow font-bold'
                                  : 'bg-teal-500/20 text-teal-300 border border-teal-400/30 hover:bg-teal-500/30'
                              }`}
                            >
                              <TbCheck className="w-3.5 h-3.5" />
                              <span>{isAccepted ? 'Applied' : 'Apply Suggestion'}</span>
                            </button>
                          </div>
                        </div>

                        {/* Comparison Diff Box */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                          {/* Original */}
                          <div className="p-3 rounded-xl bg-base-900/60 border border-base-700/60 space-y-1">
                            <span className="text-[10px] font-mono text-white/40 uppercase">Original Text:</span>
                            <p className="text-white/60 line-through decoration-rose-500/60 font-body">
                              {sug.original}
                            </p>
                          </div>

                          {/* Improved */}
                          <div className="p-3 rounded-xl bg-teal-950/20 border border-teal-500/30 space-y-1">
                            <span className="text-[10px] font-mono text-teal-400 uppercase font-semibold">
                              Optimized STAR/XYZ Version:
                            </span>
                            <p className="text-teal-100 font-body leading-relaxed">
                              {sug.improved}
                            </p>
                          </div>
                        </div>

                        {/* Explanation & Student Prompt */}
                        <div className="mt-3 pt-3 border-t border-base-700/60 flex flex-col md:flex-row md:items-center justify-between text-[11px] text-white/50 gap-2">
                          <div className="flex items-center space-x-1.5 text-white/70">
                            <TbInfoCircle className="w-3.5 h-3.5 text-teal-400 flex-shrink-0" />
                            <span>{sug.explanation}</span>
                          </div>

                          {sug.student_prompt && (
                            <div className="flex items-center space-x-1 text-amber-300 font-mono text-[10px] bg-amber-950/30 px-2.5 py-1 rounded-lg border border-amber-500/30">
                              <TbAlertCircle className="w-3 h-3 flex-shrink-0" />
                              <span>{sug.student_prompt}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
