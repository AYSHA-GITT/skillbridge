import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  TbSparkles,
  TbFileCheck,
  TbFileUpload,
  TbCheck,
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
  TbShieldCheck,
  TbSchool,
  TbCertificate,
  TbBuilding,
  TbTool
} from 'react-icons/tb';
import { skillService } from '../services/skillService';

export default function ResumeOptimizer() {
  // Navigation / Workflow State: 'setup' | 'workspace'
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

  // Results & Workspace Data
  const [analysis, setAnalysis] = useState(null);
  const [originalSections, setOriginalSections] = useState(null);
  const [editableSections, setEditableSections] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [studentPrompts, setStudentPrompts] = useState([]);

  // Workspace View Mode: 'studio' (Suggestions + Editor) | 'diff' (Side-by-side) | 'preview' (Paper Preview)
  const [workspaceView, setWorkspaceView] = useState('studio');
  const [filterType, setFilterType] = useState('all'); // 'all' | 'summary' | 'bullet' | 'skill'
  const [newSkillInput, setNewSkillInput] = useState('');

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
      'Extracting contact details & parsing resume structure...',
      'Auditing skills against target role requirements...',
      'Calculating deterministic ATS job-match score...',
      'Applying STAR/XYZ impact enhancements with Gemini...',
      'Synthesizing side-by-side interactive studio...'
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
      showToast('Resume analyzed and optimization studio ready!', 'success');
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
          if (newStatus === 'accept') {
            handleAddSkillDirect(s.skill_to_add);
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

  // Direct 1-Click Add Missing Skill from ATS Matrix
  const handleAddSkillDirect = (skillName) => {
    if (!skillName || !skillName.trim()) return;
    const clean = skillName.trim();
    setEditableSections((prev) => {
      const current = prev.skills || [];
      if (!current.some((s) => s.toLowerCase() === clean.toLowerCase())) {
        return { ...prev, skills: [...current, clean] };
      }
      return prev;
    });
    showToast(`Added "${clean}" to your Technical Skills!`, 'success');
  };

  // Direct Remove Skill tag
  const handleRemoveSkill = (skillToRemove) => {
    setEditableSections((prev) => ({
      ...prev,
      skills: (prev.skills || []).filter((s) => s !== skillToRemove)
    }));
  };

  // Add custom typed skill
  const handleAddTypedSkill = (e) => {
    if (e && e.key && e.key !== 'Enter') return;
    if (e) e.preventDefault();
    if (!newSkillInput.trim()) return;
    handleAddSkillDirect(newSkillInput.trim());
    setNewSkillInput('');
  };

  // Dynamic Live ATS Match Score Calculator
  const liveScore = useMemo(() => {
    if (!analysis || !editableSections) return 0;
    const targetReqs = analysis.target_career ? analysis.target_career.toLowerCase() : '';
    const currentSkills = (editableSections.skills || []).map((s) => s.toLowerCase());

    let reqCount = 6;
    let prefCount = 4;
    if (careers.length > 0) {
      const matchedC = careers.find((c) => c.id === targetReqs || c.title.toLowerCase() === targetReqs);
      if (matchedC) {
        reqCount = matchedC.required.length;
        prefCount = matchedC.nice_to_have.length;
      }
    }

    // Count how many required & preferred skills are covered
    let matchedReq = 0;
    (analysis.missing_required_skills || []).forEach((req) => {
      if (currentSkills.includes(req.toLowerCase())) matchedReq++;
    });
    const baseMatchedReq = analysis.matched_skills.length;
    const totalReqMatched = Math.min(reqCount, baseMatchedReq + matchedReq);

    const reqScore = (totalReqMatched / Math.max(1, reqCount)) * 55;
    const prefScore = Math.min(25, (analysis.score_breakdown?.preferred_skills_score || (prefCount * 4)) + matchedReq * 2);
    const structScore = analysis.score_breakdown?.formatting_score || 18;

    const total = Math.round(Math.min(99, Math.max(15, reqScore + prefScore + structScore)));
    return total;
  }, [analysis, editableSections, careers]);

  // Section Editors
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

  // Experience CRUD
  const handleUpdateExperienceField = (expIdx, field, value) => {
    setEditableSections((prev) => {
      const next = JSON.parse(JSON.stringify(prev));
      if (next.experience[expIdx]) {
        next.experience[expIdx][field] = value;
      }
      return next;
    });
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
        next.experience[expIndex].bullets.push('Architected and delivered core modules, resulting in [Quantify impact: e.g. reduced load times by 30%].');
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

  const handleAddExperienceEntry = () => {
    setEditableSections((prev) => ({
      ...prev,
      experience: [
        {
          role: 'Software Engineer',
          company: 'Company Name',
          period: '2023 - Present',
          location: 'Location',
          bullets: ['Engineered scalable microservices utilizing Python and REST APIs.']
        },
        ...(prev.experience || [])
      ]
    }));
    showToast('Added new experience entry.', 'success');
  };

  const handleRemoveExperienceEntry = (expIdx) => {
    setEditableSections((prev) => {
      const next = JSON.parse(JSON.stringify(prev));
      next.experience.splice(expIdx, 1);
      return next;
    });
  };

  // Project CRUD
  const handleUpdateProjectField = (projIdx, field, value) => {
    setEditableSections((prev) => {
      const next = JSON.parse(JSON.stringify(prev));
      if (next.projects[projIdx]) {
        next.projects[projIdx][field] = value;
      }
      return next;
    });
  };

  const handleUpdateProjectBullet = (projIdx, bIdx, value) => {
    setEditableSections((prev) => {
      const next = JSON.parse(JSON.stringify(prev));
      if (next.projects[projIdx]?.bullets?.[bIdx] !== undefined) {
        next.projects[projIdx].bullets[bIdx] = value;
      }
      return next;
    });
  };

  const handleAddProjectBullet = (projIdx) => {
    setEditableSections((prev) => {
      const next = JSON.parse(JSON.stringify(prev));
      if (next.projects[projIdx]) {
        next.projects[projIdx].bullets = next.projects[projIdx].bullets || [];
        next.projects[projIdx].bullets.push('Engineered end-to-end solution, delivering [Quantify: e.g. 99.5% uptime or 500+ users].');
      }
      return next;
    });
  };

  const handleRemoveProjectBullet = (projIdx, bIdx) => {
    setEditableSections((prev) => {
      const next = JSON.parse(JSON.stringify(prev));
      if (next.projects[projIdx]?.bullets) {
        next.projects[projIdx].bullets.splice(bIdx, 1);
      }
      return next;
    });
  };

  const handleAddProjectEntry = () => {
    setEditableSections((prev) => ({
      ...prev,
      projects: [
        {
          name: 'Personal Project',
          technologies: 'React, Node.js, SQLite',
          bullets: ['Engineered full-stack responsive web application with authenticated REST APIs.']
        },
        ...(prev.projects || [])
      ]
    }));
    showToast('Added new project entry.', 'success');
  };

  const handleRemoveProjectEntry = (projIdx) => {
    setEditableSections((prev) => {
      const next = JSON.parse(JSON.stringify(prev));
      next.projects.splice(projIdx, 1);
      return next;
    });
  };

  // Education CRUD
  const handleUpdateEducationField = (eduIdx, field, value) => {
    setEditableSections((prev) => {
      const next = JSON.parse(JSON.stringify(prev));
      if (next.education[eduIdx]) {
        next.education[eduIdx][field] = value;
      }
      return next;
    });
  };

  const handleAddEducationEntry = () => {
    setEditableSections((prev) => ({
      ...prev,
      education: [
        ...(prev.education || []),
        { degree: 'B.Tech in Computer Science', institution: 'University / Institute', year: '2021 - 2025', score: 'CGPA: 8.5' }
      ]
    }));
  };

  const handleRemoveEducationEntry = (eduIdx) => {
    setEditableSections((prev) => {
      const next = JSON.parse(JSON.stringify(prev));
      next.education.splice(eduIdx, 1);
      return next;
    });
  };

  // Certifications CRUD
  const handleUpdateCertification = (certIdx, value) => {
    setEditableSections((prev) => {
      const next = JSON.parse(JSON.stringify(prev));
      if (next.certifications?.[certIdx] !== undefined) {
        next.certifications[certIdx] = value;
      }
      return next;
    });
  };

  const handleAddCertification = () => {
    setEditableSections((prev) => ({
      ...prev,
      certifications: [...(prev.certifications || []), 'AWS Certified Cloud Practitioner']
    }));
  };

  const handleRemoveCertification = (certIdx) => {
    setEditableSections((prev) => {
      const next = JSON.parse(JSON.stringify(prev));
      next.certifications.splice(certIdx, 1);
      return next;
    });
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

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      showToast(`Exported ${filename} successfully!`, 'success');
    } catch (err) {
      console.error(`Export ${format} error:`, err);
      showToast(`Failed to export ${format.toUpperCase()}. Please try again.`, 'error');
    } finally {
      setExporting((prev) => ({ ...prev, [format]: false }));
    }
  };

  return (
    <div className="space-y-6 pb-20">
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

      {/* Main Studio Banner */}
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
              AI Resume Optimizer & ATS Studio
            </h1>
            <p className="text-xs text-white/60 mt-1 max-w-2xl leading-relaxed">
              Transform your resume into a top-tier candidate profile with deterministic ATS scoring, STAR/XYZ bullet rewrites,
              live section editing, and instant ATS-compliant PDF and DOCX downloads.
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
          MODE 2: COMPLETE OPTIMIZATION STUDIO (WORKSPACE)
      ───────────────────────────────────────────────────────────── */}
      {mode === 'workspace' && analysis && editableSections && (
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
                    strokeDashoffset={251.2 - (251.2 * liveScore) / 100}
                    className={`${
                      liveScore >= 75
                        ? 'text-emerald-400'
                        : liveScore >= 50
                        ? 'text-amber-400'
                        : 'text-rose-400'
                    } transition-all duration-700 ease-out`}
                  />
                </svg>
                <div className="absolute flex flex-col items-center">
                  <span className="text-2xl font-bold font-heading text-white">
                    {liveScore}%
                  </span>
                  <span className="text-[9px] font-mono uppercase text-white/40">ATS Match</span>
                </div>
              </div>

              <div className="space-y-1">
                <div className="flex items-center space-x-1.5">
                  <span className="text-xs font-semibold text-white">
                    ATS Job-Match Score
                  </span>
                  {liveScore > analysis.match_score && (
                    <span className="text-[10px] font-mono font-bold text-emerald-400 bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-500/30">
                      +{liveScore - Math.round(analysis.match_score)}% Boost
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-white/50 leading-snug">
                  Target: <span className="text-teal-300 font-semibold">{analysis.target_career}</span>
                </p>
                <div className="text-[10px] text-white/40 space-y-0.5 pt-1">
                  <div className="flex justify-between">
                    <span>Required Competencies:</span>
                    <span className="font-mono text-teal-300">{analysis.score_breakdown?.required_skills_score || 0} / 55</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Preferred Skills:</span>
                    <span className="font-mono text-teal-300">{analysis.score_breakdown?.preferred_skills_score || 0} / 25</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Formatting & ATS Style:</span>
                    <span className="font-mono text-teal-300">{analysis.score_breakdown?.formatting_score || 0} / 20</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Matched & Missing Skills Snapshot with 1-Click Injection */}
            <div className="md:col-span-8 surface p-5 rounded-2xl border border-base-700/60 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-xs font-semibold text-white flex items-center space-x-2">
                    <TbListCheck className="w-4 h-4 text-teal-400" />
                    <span>Skills Competency Matrix (Click to Add to Resume)</span>
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

                  {/* Missing Required Skills with 1-Click Add */}
                  <div className="flex flex-wrap gap-1.5 items-center">
                    <span className="text-[10px] text-rose-400 font-mono font-medium mr-1">Missing Core:</span>
                    {analysis.missing_required_skills.length > 0 ? (
                      analysis.missing_required_skills.map((s) => {
                        const isAlreadyAdded = (editableSections.skills || []).some(
                          (sk) => sk.toLowerCase() === s.toLowerCase()
                        );
                        return (
                          <button
                            key={s}
                            type="button"
                            onClick={() => !isAlreadyAdded && handleAddSkillDirect(s)}
                            className={`px-2 py-0.5 rounded-lg text-[10px] font-medium flex items-center space-x-1 transition-all ${
                              isAlreadyAdded
                                ? 'bg-emerald-950/50 text-emerald-300 border border-emerald-500/40'
                                : 'bg-rose-950/40 text-rose-300 border border-rose-500/30 hover:bg-rose-900/40 cursor-pointer'
                            }`}
                            title={isAlreadyAdded ? 'Added to resume' : `Click to add ${s} to your skills`}
                          >
                            <span>{isAlreadyAdded ? '✓' : '+'}</span>
                            <span>{s}</span>
                          </button>
                        );
                      })
                    ) : (
                      <span className="text-[10px] text-emerald-400 font-mono">
                        All core required competencies covered!
                      </span>
                    )}
                  </div>

                  {/* Missing Preferred Skills */}
                  {analysis.missing_preferred_skills && analysis.missing_preferred_skills.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 items-center">
                      <span className="text-[10px] text-amber-400 font-mono font-medium mr-1">Preferred:</span>
                      {analysis.missing_preferred_skills.map((s) => {
                        const isAlreadyAdded = (editableSections.skills || []).some(
                          (sk) => sk.toLowerCase() === s.toLowerCase()
                        );
                        return (
                          <button
                            key={s}
                            type="button"
                            onClick={() => !isAlreadyAdded && handleAddSkillDirect(s)}
                            className={`px-2 py-0.5 rounded-lg text-[10px] font-medium flex items-center space-x-1 transition-all ${
                              isAlreadyAdded
                                ? 'bg-emerald-950/50 text-emerald-300 border border-emerald-500/40'
                                : 'bg-amber-950/40 text-amber-300 border border-amber-500/30 hover:bg-amber-900/40 cursor-pointer'
                            }`}
                            title={isAlreadyAdded ? 'Added to resume' : `Click to add ${s} to your skills`}
                          >
                            <span>{isAlreadyAdded ? '✓' : '+'}</span>
                            <span>{s}</span>
                          </button>
                        );
                      })}
                    </div>
                  )}
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

          {/* Student Required Input Notice (Anti-Hallucination Indicator) */}
          {studentPrompts && studentPrompts.length > 0 && (
            <div className="surface p-4 rounded-xl border border-amber-500/30 bg-amber-950/20 flex items-start space-x-3 text-xs">
              <TbAlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="font-semibold text-amber-200">
                  Information You Need to Provide ({studentPrompts.length} items flagged)
                </p>
                <p className="text-[11px] text-amber-300/80 leading-relaxed">
                  SkillLens AI guarantees 100% factual accuracy and strictly avoids fabricating metrics or achievements.
                  Please replace bracketed prompts like <span className="font-mono bg-amber-900/50 px-1 py-0.5 rounded text-amber-200">[Quantify impact: ...]</span> with your real numbers before final submission.
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

          {/* Studio View Selector Toolbar */}
          <div className="flex items-center justify-between border-b border-base-700/60 pb-3 flex-wrap gap-y-3">
            <div className="flex p-0.5 rounded-xl bg-base-900 border border-base-700 text-xs font-medium">
              <button
                type="button"
                onClick={() => setWorkspaceView('studio')}
                className={`px-3.5 py-1.5 rounded-lg transition-all flex items-center space-x-1.5 ${
                  workspaceView === 'studio'
                    ? 'bg-teal-500/20 text-teal-300 border border-teal-400/30 shadow-glow font-semibold'
                    : 'text-white/60 hover:text-white'
                }`}
              >
                <TbSparkles className="w-3.5 h-3.5" />
                <span>AI Suggestions & Live Editor</span>
              </button>

              <button
                type="button"
                onClick={() => setWorkspaceView('diff')}
                className={`px-3.5 py-1.5 rounded-lg transition-all flex items-center space-x-1.5 ${
                  workspaceView === 'diff'
                    ? 'bg-teal-500/20 text-teal-300 border border-teal-400/30 shadow-glow font-semibold'
                    : 'text-white/60 hover:text-white'
                }`}
              >
                <TbEye className="w-3.5 h-3.5" />
                <span>Side-by-Side Diff View</span>
              </button>

              <button
                type="button"
                onClick={() => setWorkspaceView('preview')}
                className={`px-3.5 py-1.5 rounded-lg transition-all flex items-center space-x-1.5 ${
                  workspaceView === 'preview'
                    ? 'bg-teal-500/20 text-teal-300 border border-teal-400/30 shadow-glow font-semibold'
                    : 'text-white/60 hover:text-white'
                }`}
              >
                <TbFileCheck className="w-3.5 h-3.5" />
                <span>A4 Paper Document Preview</span>
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

          {/* ─────────────────────────────────────────────────────────────
              VIEW 1: AI SUGGESTIONS & FULL LIVE EDITOR STUDIO (SPLIT)
          ───────────────────────────────────────────────────────────── */}
          {workspaceView === 'studio' && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              {/* Left Column (5 Cols): AI Suggestions Review Drawer */}
              <div className="lg:col-span-5 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-mono font-semibold uppercase text-teal-400 flex items-center space-x-2">
                    <TbSparkles className="w-4 h-4 text-teal-400" />
                    <span>AI Improvement Cards ({suggestions.length})</span>
                  </h3>
                  <div className="flex space-x-1 text-[10px]">
                    {['all', 'summary', 'bullet'].map((cat) => (
                      <button
                        key={cat}
                        type="button"
                        onClick={() => setFilterType(cat)}
                        className={`px-2 py-0.5 rounded capitalize ${
                          filterType === cat
                            ? 'bg-teal-500/30 text-teal-200 border border-teal-400/30'
                            : 'text-white/40 hover:text-white'
                        }`}
                      >
                        {cat}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="space-y-3.5 max-h-[820px] overflow-y-auto pr-1">
                  {suggestions
                    .filter((s) => (filterType === 'all' ? true : s.type.includes(filterType)))
                    .map((sug) => {
                      const isAccepted = sug.status === 'accepted';
                      const isRejected = sug.status === 'rejected';

                      return (
                        <div
                          key={sug.id}
                          className={`surface p-4 rounded-xl border transition-all ${
                            isAccepted
                              ? 'border-emerald-500/40 bg-emerald-950/10'
                              : isRejected
                              ? 'border-base-700/50 opacity-60'
                              : 'border-base-700/70 hover:border-teal-500/40'
                          }`}
                        >
                          <div className="flex items-center justify-between mb-2">
                            <span className="px-2 py-0.5 rounded-full text-[9px] font-mono uppercase bg-teal-500/15 text-teal-300 border border-teal-400/30">
                              {sug.type.replace('_', ' ')}
                            </span>

                            <div className="flex items-center space-x-1.5">
                              <button
                                type="button"
                                onClick={() => handleToggleSuggestion(sug.id, 'reject')}
                                className={`px-2.5 py-0.5 rounded text-[11px] font-medium transition-all ${
                                  isRejected
                                    ? 'bg-rose-950 text-rose-300 border border-rose-500/40'
                                    : 'text-white/40 hover:text-white'
                                }`}
                              >
                                Reject
                              </button>
                              <button
                                type="button"
                                onClick={() => handleToggleSuggestion(sug.id, 'accept')}
                                className={`px-2.5 py-0.5 rounded text-[11px] font-semibold transition-all ${
                                  isAccepted
                                    ? 'bg-emerald-500 text-base-950 font-bold'
                                    : 'bg-teal-500/20 text-teal-300 border border-teal-400/30 hover:bg-teal-500/30'
                                }`}
                              >
                                {isAccepted ? 'Applied' : 'Apply'}
                              </button>
                            </div>
                          </div>

                          <div className="space-y-2 text-xs">
                            <div className="p-2.5 rounded-lg bg-base-900/60 border border-base-700/60">
                              <span className="text-[9px] font-mono text-white/40 uppercase block mb-0.5">Original:</span>
                              <p className="text-white/60 line-through decoration-rose-500/60 leading-relaxed font-body">
                                {sug.original}
                              </p>
                            </div>

                            <div className="p-2.5 rounded-lg bg-teal-950/20 border border-teal-500/30">
                              <span className="text-[9px] font-mono text-teal-400 uppercase font-semibold block mb-0.5">
                                ✨ STAR Improved:
                              </span>
                              <p className="text-teal-100 leading-relaxed font-body">
                                {sug.improved}
                              </p>
                            </div>

                            <p className="text-[10px] text-white/50 pt-1 flex items-start space-x-1">
                              <TbInfoCircle className="w-3 h-3 text-teal-400 flex-shrink-0 mt-0.5" />
                              <span>{sug.explanation}</span>
                            </p>
                          </div>
                        </div>
                      );
                    })}
                </div>
              </div>

              {/* Right Column (7 Cols): The Full Interactive Live Resume Canvas */}
              <div className="lg:col-span-7 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-mono font-semibold uppercase text-teal-300 flex items-center space-x-2">
                    <span className="w-2 h-2 rounded-full bg-teal-400 animate-pulse" />
                    <span>Live Editable Resume (Final ATS Draft)</span>
                  </h3>
                  <span className="text-[10px] text-white/40">Real-time sync</span>
                </div>

                <div className="surface p-6 rounded-2xl border border-teal-500/40 space-y-6 max-h-[820px] overflow-y-auto font-body text-xs leading-relaxed bg-base-900/90 shadow-xl">
                  {/* Contact Header Inputs */}
                  <div className="space-y-3 border-b border-base-700/60 pb-4">
                    <span className="text-[10px] font-mono uppercase text-teal-400 font-semibold block">
                      Candidate Header
                    </span>
                    <input
                      type="text"
                      value={editableSections.contact?.name || ''}
                      onChange={(e) => handleUpdateContact('name', e.target.value)}
                      placeholder="Candidate Full Name"
                      className="w-full text-lg font-bold bg-transparent border-b border-base-700 focus:border-teal-400 focus:outline-none text-white py-1"
                    />
                    <div className="grid grid-cols-2 gap-2.5">
                      <input
                        type="text"
                        value={editableSections.contact?.email || ''}
                        onChange={(e) => handleUpdateContact('email', e.target.value)}
                        placeholder="Email Address"
                        className="input-field !py-2 text-xs"
                      />
                      <input
                        type="text"
                        value={editableSections.contact?.phone || ''}
                        onChange={(e) => handleUpdateContact('phone', e.target.value)}
                        placeholder="Phone Number"
                        className="input-field !py-2 text-xs"
                      />
                      <input
                        type="text"
                        value={editableSections.contact?.linkedin || ''}
                        onChange={(e) => handleUpdateContact('linkedin', e.target.value)}
                        placeholder="LinkedIn URL / Handle"
                        className="input-field !py-2 text-xs"
                      />
                      <input
                        type="text"
                        value={editableSections.contact?.github || ''}
                        onChange={(e) => handleUpdateContact('github', e.target.value)}
                        placeholder="GitHub URL / Handle"
                        className="input-field !py-2 text-xs"
                      />
                      <input
                        type="text"
                        value={editableSections.contact?.location || ''}
                        onChange={(e) => handleUpdateContact('location', e.target.value)}
                        placeholder="Location (City, Country)"
                        className="input-field !py-2 text-xs col-span-2"
                      />
                    </div>
                  </div>

                  {/* Executive Summary Editor */}
                  <div className="space-y-2 border-b border-base-700/60 pb-4">
                    <div className="flex items-center justify-between">
                      <h5 className="text-[11px] font-mono uppercase font-semibold text-teal-400">
                        Professional Summary
                      </h5>
                      <span className="text-[10px] text-teal-300 font-mono">Tailored for {selectedCareer}</span>
                    </div>
                    <textarea
                      rows={3}
                      value={editableSections.summary || ''}
                      onChange={(e) => handleUpdateSummary(e.target.value)}
                      className="input-field text-xs leading-relaxed"
                    />
                  </div>

                  {/* Skills Tag Management */}
                  <div className="space-y-2.5 border-b border-base-700/60 pb-4">
                    <div className="flex items-center justify-between">
                      <h5 className="text-[11px] font-mono uppercase font-semibold text-teal-400">
                        Technical Skills ({(editableSections.skills || []).length})
                      </h5>
                      <span className="text-[10px] text-white/40">Click '×' to remove</span>
                    </div>

                    <div className="flex flex-wrap gap-1.5 p-3 rounded-xl bg-base-800/40 border border-base-700/60 min-h-[50px]">
                      {(editableSections.skills || []).map((sk) => (
                        <span
                          key={sk}
                          className="px-2.5 py-1 rounded-lg text-xs bg-teal-950/40 text-teal-200 border border-teal-500/30 flex items-center space-x-1.5 shadow-sm"
                        >
                          <span>{sk}</span>
                          <button
                            type="button"
                            onClick={() => handleRemoveSkill(sk)}
                            className="text-white/40 hover:text-rose-400 transition-all ml-1"
                          >
                            ×
                          </button>
                        </span>
                      ))}
                    </div>

                    <div className="flex items-center space-x-2">
                      <input
                        type="text"
                        value={newSkillInput}
                        onChange={(e) => setNewSkillInput(e.target.value)}
                        onKeyDown={handleAddTypedSkill}
                        placeholder="Add a new skill (e.g. Docker, AWS, React) & press Enter..."
                        className="input-field !py-2 text-xs flex-1"
                      />
                      <button
                        type="button"
                        onClick={handleAddTypedSkill}
                        className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-teal-500/20 text-teal-300 border border-teal-400/30 hover:bg-teal-500/30 transition-all flex items-center space-x-1"
                      >
                        <TbPlus className="w-3.5 h-3.5" />
                        <span>Add</span>
                      </button>
                    </div>
                  </div>

                  {/* Work Experience Section */}
                  <div className="space-y-4 border-b border-base-700/60 pb-4">
                    <div className="flex items-center justify-between">
                      <h5 className="text-[11px] font-mono uppercase font-semibold text-teal-400 flex items-center space-x-1.5">
                        <TbBuilding className="w-3.5 h-3.5" />
                        <span>Work Experience</span>
                      </h5>
                      <button
                        type="button"
                        onClick={handleAddExperienceEntry}
                        className="text-[11px] text-teal-300 hover:text-white flex items-center space-x-1 font-medium"
                      >
                        <TbPlus className="w-3.5 h-3.5" />
                        <span>Add Position</span>
                      </button>
                    </div>

                    {(editableSections.experience || []).map((exp, expIdx) => (
                      <div key={expIdx} className="p-4 rounded-xl bg-base-800/60 border border-base-700/60 space-y-3">
                        <div className="flex items-center justify-between gap-2">
                          <input
                            type="text"
                            value={exp.role || ''}
                            onChange={(e) => handleUpdateExperienceField(expIdx, 'role', e.target.value)}
                            placeholder="Job Title / Role"
                            className="input-field !py-1.5 text-xs font-semibold text-white flex-1"
                          />
                          <input
                            type="text"
                            value={exp.company || ''}
                            onChange={(e) => handleUpdateExperienceField(expIdx, 'company', e.target.value)}
                            placeholder="Company Name"
                            className="input-field !py-1.5 text-xs flex-1"
                          />
                          <button
                            type="button"
                            onClick={() => handleRemoveExperienceEntry(expIdx)}
                            className="text-white/30 hover:text-rose-400 p-1.5 transition-all"
                            title="Delete this role"
                          >
                            <TbTrash className="w-4 h-4" />
                          </button>
                        </div>

                        <div className="grid grid-cols-2 gap-2">
                          <input
                            type="text"
                            value={exp.period || ''}
                            onChange={(e) => handleUpdateExperienceField(expIdx, 'period', e.target.value)}
                            placeholder="Dates (e.g. Jan 2024 - Present)"
                            className="input-field !py-1 text-[11px]"
                          />
                          <input
                            type="text"
                            value={exp.location || ''}
                            onChange={(e) => handleUpdateExperienceField(expIdx, 'location', e.target.value)}
                            placeholder="Location (e.g. Bengaluru, India)"
                            className="input-field !py-1 text-[11px]"
                          />
                        </div>

                        {/* Bullets */}
                        <div className="space-y-2 pt-1">
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

                          <button
                            type="button"
                            onClick={() => handleAddExperienceBullet(expIdx)}
                            className="text-[11px] text-teal-400 hover:text-teal-300 flex items-center space-x-1 pt-1 font-medium"
                          >
                            <TbPlus className="w-3.5 h-3.5" />
                            <span>Add Bullet Point</span>
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Projects Section */}
                  <div className="space-y-4 border-b border-base-700/60 pb-4">
                    <div className="flex items-center justify-between">
                      <h5 className="text-[11px] font-mono uppercase font-semibold text-teal-400 flex items-center space-x-1.5">
                        <TbTool className="w-3.5 h-3.5" />
                        <span>Key Projects</span>
                      </h5>
                      <button
                        type="button"
                        onClick={handleAddProjectEntry}
                        className="text-[11px] text-teal-300 hover:text-white flex items-center space-x-1 font-medium"
                      >
                        <TbPlus className="w-3.5 h-3.5" />
                        <span>Add Project</span>
                      </button>
                    </div>

                    {(editableSections.projects || []).map((proj, projIdx) => (
                      <div key={projIdx} className="p-4 rounded-xl bg-base-800/60 border border-base-700/60 space-y-3">
                        <div className="flex items-center justify-between gap-2">
                          <input
                            type="text"
                            value={proj.name || ''}
                            onChange={(e) => handleUpdateProjectField(projIdx, 'name', e.target.value)}
                            placeholder="Project Name"
                            className="input-field !py-1.5 text-xs font-semibold text-white flex-1"
                          />
                          <input
                            type="text"
                            value={proj.technologies || ''}
                            onChange={(e) => handleUpdateProjectField(projIdx, 'technologies', e.target.value)}
                            placeholder="Technologies (e.g. Python, React, PostgreSQL)"
                            className="input-field !py-1.5 text-xs flex-1"
                          />
                          <button
                            type="button"
                            onClick={() => handleRemoveProjectEntry(projIdx)}
                            className="text-white/30 hover:text-rose-400 p-1.5 transition-all"
                            title="Delete this project"
                          >
                            <TbTrash className="w-4 h-4" />
                          </button>
                        </div>

                        {/* Bullets */}
                        <div className="space-y-2 pt-1">
                          {(proj.bullets || []).map((bullet, bIdx) => (
                            <div key={bIdx} className="flex items-start space-x-2">
                              <span className="text-teal-400 mt-2 font-bold">•</span>
                              <textarea
                                rows={2}
                                value={bullet}
                                onChange={(e) => handleUpdateProjectBullet(projIdx, bIdx, e.target.value)}
                                className="input-field !py-1.5 text-xs font-body leading-snug flex-1"
                              />
                              <button
                                type="button"
                                onClick={() => handleRemoveProjectBullet(projIdx, bIdx)}
                                className="text-white/30 hover:text-rose-400 p-1.5 transition-all mt-1"
                              >
                                <TbTrash className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          ))}

                          <button
                            type="button"
                            onClick={() => handleAddProjectBullet(projIdx)}
                            className="text-[11px] text-teal-400 hover:text-teal-300 flex items-center space-x-1 pt-1 font-medium"
                          >
                            <TbPlus className="w-3.5 h-3.5" />
                            <span>Add Project Bullet</span>
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Education Section */}
                  <div className="space-y-3 border-b border-base-700/60 pb-4">
                    <div className="flex items-center justify-between">
                      <h5 className="text-[11px] font-mono uppercase font-semibold text-teal-400 flex items-center space-x-1.5">
                        <TbSchool className="w-3.5 h-3.5" />
                        <span>Education</span>
                      </h5>
                      <button
                        type="button"
                        onClick={handleAddEducationEntry}
                        className="text-[11px] text-teal-300 hover:text-white flex items-center space-x-1 font-medium"
                      >
                        <TbPlus className="w-3.5 h-3.5" />
                        <span>Add Degree</span>
                      </button>
                    </div>

                    {(editableSections.education || []).map((edu, eduIdx) => (
                      <div key={eduIdx} className="p-3 rounded-xl bg-base-800/40 border border-base-700/60 space-y-2">
                        <div className="flex items-center justify-between gap-2">
                          <input
                            type="text"
                            value={edu.degree || ''}
                            onChange={(e) => handleUpdateEducationField(eduIdx, 'degree', e.target.value)}
                            placeholder="Degree (e.g. B.Tech in CSE)"
                            className="input-field !py-1 text-xs font-semibold flex-1"
                          />
                          <input
                            type="text"
                            value={edu.institution || ''}
                            onChange={(e) => handleUpdateEducationField(eduIdx, 'institution', e.target.value)}
                            placeholder="University / College"
                            className="input-field !py-1 text-xs flex-1"
                          />
                          <button
                            type="button"
                            onClick={() => handleRemoveEducationEntry(eduIdx)}
                            className="text-white/30 hover:text-rose-400 p-1"
                          >
                            <TbTrash className="w-3.5 h-3.5" />
                          </button>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          <input
                            type="text"
                            value={edu.year || ''}
                            onChange={(e) => handleUpdateEducationField(eduIdx, 'year', e.target.value)}
                            placeholder="Graduation Year (e.g. 2021 - 2025)"
                            className="input-field !py-1 text-[11px]"
                          />
                          <input
                            type="text"
                            value={edu.score || ''}
                            onChange={(e) => handleUpdateEducationField(eduIdx, 'score', e.target.value)}
                            placeholder="GPA or Percentage (e.g. 8.8 CGPA)"
                            className="input-field !py-1 text-[11px]"
                          />
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Certifications Section */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h5 className="text-[11px] font-mono uppercase font-semibold text-teal-400 flex items-center space-x-1.5">
                        <TbCertificate className="w-3.5 h-3.5" />
                        <span>Certifications & Honors</span>
                      </h5>
                      <button
                        type="button"
                        onClick={handleAddCertification}
                        className="text-[11px] text-teal-300 hover:text-white flex items-center space-x-1 font-medium"
                      >
                        <TbPlus className="w-3.5 h-3.5" />
                        <span>Add Certificate</span>
                      </button>
                    </div>

                    {(editableSections.certifications || []).map((cert, certIdx) => (
                      <div key={certIdx} className="flex items-center space-x-2">
                        <span className="text-teal-400 font-bold">•</span>
                        <input
                          type="text"
                          value={cert}
                          onChange={(e) => handleUpdateCertification(certIdx, e.target.value)}
                          placeholder="Certification name (e.g. AWS Certified Developer)"
                          className="input-field !py-1.5 text-xs flex-1"
                        />
                        <button
                          type="button"
                          onClick={() => handleRemoveCertification(certIdx)}
                          className="text-white/30 hover:text-rose-400 p-1"
                        >
                          <TbTrash className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ─────────────────────────────────────────────────────────────
              VIEW 2: SIDE-BY-SIDE DIFF COMPARISON VIEW
          ───────────────────────────────────────────────────────────── */}
          {workspaceView === 'diff' && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              {/* Left Pane: Original Resume */}
              <div className="lg:col-span-6 space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-mono font-semibold uppercase text-white/50 flex items-center space-x-2">
                    <span className="w-2 h-2 rounded-full bg-white/40" />
                    <span>Original Resume (Read-Only Baseline)</span>
                  </h4>
                  <span className="text-[10px] text-white/40 font-mono">Kept 100% untouched</span>
                </div>

                <div className="surface p-5 rounded-2xl border border-base-700/60 space-y-4 max-h-[750px] overflow-y-auto font-body text-xs leading-relaxed bg-base-900/50">
                  <div className="border-b border-base-700/60 pb-2">
                    <h5 className="text-base font-bold text-white">{originalSections.contact?.name || 'Candidate Name'}</h5>
                    <p className="text-[11px] text-white/40 mt-0.5">
                      {[
                        originalSections.contact?.email,
                        originalSections.contact?.phone,
                        originalSections.contact?.location
                      ].filter(Boolean).join(' | ')}
                    </p>
                  </div>

                  <div>
                    <h6 className="text-[10px] font-mono uppercase text-teal-400/80 mb-1 font-semibold">Summary</h6>
                    <p className="text-white/60 italic">{originalSections.summary || '(None)'}</p>
                  </div>

                  <div>
                    <h6 className="text-[10px] font-mono uppercase text-teal-400/80 mb-1 font-semibold">Skills</h6>
                    <p className="text-white/60">{(originalSections.skills || []).join(', ')}</p>
                  </div>

                  <div>
                    <h6 className="text-[10px] font-mono uppercase text-teal-400/80 mb-1 font-semibold">Experience</h6>
                    {(originalSections.experience || []).map((exp, idx) => (
                      <div key={idx} className="mb-2">
                        <p className="font-semibold text-white/80">{exp.role} {exp.company ? `— ${exp.company}` : ''}</p>
                        <ul className="list-disc list-inside text-white/60 space-y-0.5">
                          {(exp.bullets || []).map((b, bIdx) => (
                            <li key={bIdx}>{b}</li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>

                  <div>
                    <h6 className="text-[10px] font-mono uppercase text-teal-400/80 mb-1 font-semibold">Projects</h6>
                    {(originalSections.projects || []).map((p, idx) => (
                      <div key={idx} className="mb-2">
                        <p className="font-semibold text-white/80">{p.name} {p.technologies ? `(${p.technologies})` : ''}</p>
                        <ul className="list-disc list-inside text-white/60 space-y-0.5">
                          {(p.bullets || []).map((b, bIdx) => (
                            <li key={bIdx}>{b}</li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Right Pane: Optimized Diff View */}
              <div className="lg:col-span-6 space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-mono font-semibold uppercase text-teal-300 flex items-center space-x-2">
                    <span className="w-2 h-2 rounded-full bg-teal-400 animate-pulse" />
                    <span>Optimized STAR Resume Version</span>
                  </h4>
                  <span className="text-[10px] text-teal-400 font-mono">Live dynamic diff</span>
                </div>

                <div className="surface p-5 rounded-2xl border border-teal-500/40 space-y-4 max-h-[750px] overflow-y-auto font-body text-xs leading-relaxed bg-base-900/90 shadow-xl">
                  <div className="border-b border-base-700/60 pb-2">
                    <h5 className="text-base font-bold text-white">{editableSections.contact?.name || 'Candidate Name'}</h5>
                    <p className="text-[11px] text-teal-300 mt-0.5">
                      {[
                        editableSections.contact?.email,
                        editableSections.contact?.phone,
                        editableSections.contact?.location,
                        editableSections.contact?.linkedin,
                        editableSections.contact?.github
                      ].filter(Boolean).join(' | ')}
                    </p>
                  </div>

                  <div>
                    <h6 className="text-[10px] font-mono uppercase text-teal-400 mb-1 font-semibold">Summary</h6>
                    <p className="text-teal-100 bg-teal-950/20 p-2.5 rounded-lg border border-teal-500/20 leading-relaxed">
                      {editableSections.summary}
                    </p>
                  </div>

                  <div>
                    <h6 className="text-[10px] font-mono uppercase text-teal-400 mb-1 font-semibold">Skills</h6>
                    <div className="flex flex-wrap gap-1">
                      {(editableSections.skills || []).map((s) => (
                        <span key={s} className="px-2 py-0.5 rounded text-[10px] bg-teal-950/40 text-teal-200 border border-teal-500/30">
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h6 className="text-[10px] font-mono uppercase text-teal-400 mb-1 font-semibold">Experience (STAR Polished)</h6>
                    {(editableSections.experience || []).map((exp, idx) => (
                      <div key={idx} className="mb-3 space-y-1">
                        <p className="font-semibold text-white">
                          {exp.role} {exp.company ? `— ${exp.company}` : ''}
                          <span className="text-white/40 text-[10px] font-normal ml-2">{exp.period}</span>
                        </p>
                        <ul className="list-disc list-inside text-white/80 space-y-1">
                          {(exp.bullets || []).map((b, bIdx) => (
                            <li key={bIdx} className={b.includes('[Quantify') ? 'text-amber-200' : 'text-white/80'}>
                              {b}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>

                  <div>
                    <h6 className="text-[10px] font-mono uppercase text-teal-400 mb-1 font-semibold">Key Projects</h6>
                    {(editableSections.projects || []).map((p, idx) => (
                      <div key={idx} className="mb-2 space-y-1">
                        <p className="font-semibold text-white">
                          {p.name} {p.technologies ? <span className="text-teal-300 font-mono text-[10px]">({p.technologies})</span> : ''}
                        </p>
                        <ul className="list-disc list-inside text-white/80 space-y-0.5">
                          {(p.bullets || []).map((b, bIdx) => (
                            <li key={bIdx}>{b}</li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ─────────────────────────────────────────────────────────────
              VIEW 3: REALISTIC A4 ATS PAPER DOCUMENT PREVIEW
          ───────────────────────────────────────────────────────────── */}
          {workspaceView === 'preview' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs text-white/50">
                  Exact preview of the generated ATS PDF document (Letter / A4 size formatted).
                </span>
                <div className="flex items-center space-x-2">
                  <button
                    type="button"
                    onClick={() => handleExport('pdf')}
                    className="btn-primary !w-auto text-xs py-1.5 px-3 flex items-center space-x-1"
                  >
                    <TbDownload className="w-3.5 h-3.5" />
                    <span>Download PDF</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleExport('docx')}
                    className="px-3 py-1.5 rounded-xl bg-base-800 text-teal-300 text-xs border border-teal-500/30 flex items-center space-x-1"
                  >
                    <TbDownload className="w-3.5 h-3.5" />
                    <span>Download DOCX</span>
                  </button>
                </div>
              </div>

              {/* Realistic Paper Container */}
              <div className="max-w-4xl mx-auto bg-white text-slate-900 shadow-2xl rounded-sm p-12 font-serif text-[13px] leading-relaxed border border-slate-300">
                {/* Header */}
                <div className="text-center border-b border-slate-300 pb-3 mb-4 space-y-1">
                  <h1 className="text-2xl font-bold tracking-tight text-slate-950 font-sans uppercase">
                    {editableSections.contact?.name || 'CANDIDATE NAME'}
                  </h1>
                  <p className="text-xs text-slate-600 font-sans">
                    {[
                      editableSections.contact?.phone,
                      editableSections.contact?.email,
                      editableSections.contact?.location,
                      editableSections.contact?.linkedin,
                      editableSections.contact?.github
                    ].filter(Boolean).join('  •  ')}
                  </p>
                </div>

                {/* Summary */}
                {editableSections.summary && (
                  <div className="mb-4">
                    <h2 className="text-xs font-bold uppercase tracking-wider text-teal-800 border-b border-teal-800 pb-0.5 mb-1.5 font-sans">
                      Professional Summary
                    </h2>
                    <p className="text-slate-800 leading-normal text-justify">
                      {editableSections.summary}
                    </p>
                  </div>
                )}

                {/* Skills */}
                {(editableSections.skills || []).length > 0 && (
                  <div className="mb-4">
                    <h2 className="text-xs font-bold uppercase tracking-wider text-teal-800 border-b border-teal-800 pb-0.5 mb-1.5 font-sans">
                      Technical Skills
                    </h2>
                    <p className="text-slate-800">
                      <strong className="font-semibold">Core Competencies: </strong>
                      {(editableSections.skills || []).join(', ')}
                    </p>
                  </div>
                )}

                {/* Experience */}
                {(editableSections.experience || []).length > 0 && (
                  <div className="mb-4">
                    <h2 className="text-xs font-bold uppercase tracking-wider text-teal-800 border-b border-teal-800 pb-0.5 mb-1.5 font-sans">
                      Work Experience
                    </h2>
                    {(editableSections.experience || []).map((exp, idx) => (
                      <div key={idx} className="mb-3">
                        <div className="flex justify-between font-sans text-xs font-bold text-slate-900">
                          <span>
                            {exp.role} {exp.company ? `— ${exp.company}` : ''}
                          </span>
                          <span className="font-normal text-slate-600">
                            {[exp.location, exp.period].filter(Boolean).join(' | ')}
                          </span>
                        </div>
                        <ul className="list-disc list-inside text-slate-800 mt-1 space-y-0.5 pl-2 text-[12.5px]">
                          {(exp.bullets || []).map((b, bIdx) => (
                            <li key={bIdx} className="leading-snug">
                              {b}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                )}

                {/* Projects */}
                {(editableSections.projects || []).length > 0 && (
                  <div className="mb-4">
                    <h2 className="text-xs font-bold uppercase tracking-wider text-teal-800 border-b border-teal-800 pb-0.5 mb-1.5 font-sans">
                      Key Technical Projects
                    </h2>
                    {(editableSections.projects || []).map((proj, idx) => (
                      <div key={idx} className="mb-2.5">
                        <div className="flex justify-between font-sans text-xs font-bold text-slate-900">
                          <span>{proj.name}</span>
                          {proj.technologies && (
                            <span className="font-normal italic text-slate-600">
                              {proj.technologies}
                            </span>
                          )}
                        </div>
                        <ul className="list-disc list-inside text-slate-800 mt-0.5 space-y-0.5 pl-2 text-[12.5px]">
                          {(proj.bullets || []).map((b, bIdx) => (
                            <li key={bIdx} className="leading-snug">
                              {b}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                )}

                {/* Education */}
                {(editableSections.education || []).length > 0 && (
                  <div className="mb-4">
                    <h2 className="text-xs font-bold uppercase tracking-wider text-teal-800 border-b border-teal-800 pb-0.5 mb-1.5 font-sans">
                      Education
                    </h2>
                    {(editableSections.education || []).map((edu, idx) => (
                      <div key={idx} className="flex justify-between font-sans text-xs text-slate-900 mb-1">
                        <div>
                          <strong className="font-bold">{edu.degree}</strong>
                          {edu.institution ? ` — ${edu.institution}` : ''}
                        </div>
                        <span className="text-slate-600">
                          {[edu.year, edu.score].filter(Boolean).join(' | ')}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Certifications */}
                {(editableSections.certifications || []).length > 0 && (
                  <div>
                    <h2 className="text-xs font-bold uppercase tracking-wider text-teal-800 border-b border-teal-800 pb-0.5 mb-1.5 font-sans">
                      Certifications & Honors
                    </h2>
                    <ul className="list-disc list-inside text-slate-800 space-y-0.5 pl-2 text-[12.5px]">
                      {(editableSections.certifications || []).map((cert, idx) => (
                        <li key={idx}>{cert}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
