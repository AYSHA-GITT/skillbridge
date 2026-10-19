import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import AppLayout from '../components/AppLayout';
import AlertBanner from '../components/AlertBanner';
import ProgressBar from '../components/ProgressBar';
import skillService from '../services/skillService';
import {
  TbBriefcase,
  TbSearch,
  TbRefresh,
  TbBookmark,
  TbBookmarkFilled,
  TbExternalLink,
  TbMicrophone,
  TbCheck,
  TbX,
  TbChartBar,
  TbSparkles,
  TbWorld,
  TbBuilding,
  TbMapPin,
  TbArrowsDiff,
  TbBrandYoutube,
  TbBrandGithub,
  TbScale
} from 'react-icons/tb';


const DOMAINS = [
  'All Domains',
  'Software Development',
  'Machine Learning & AI',
  'Cloud & DevOps',
  'Data Science',
  'Cybersecurity',
  'Frontend Engineering'
];

const JOB_TYPES = ['All Types', 'Full-time', 'Internship', 'Contract', 'Part-time'];

export default function Jobs() {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [alert, setAlert] = useState(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDomain, setSelectedDomain] = useState('All Domains');
  const [selectedJobType, setSelectedJobType] = useState('All Types');
  const [remoteOnly, setRemoteOnly] = useState(false);
  const [sourceFilter, setSourceFilter] = useState('all'); // 'all', 'live', 'sample'
  const [showSavedOnly, setShowSavedOnly] = useState(false);

  // Saved Jobs tracking
  const [savedJobIds, setSavedJobIds] = useState(new Set());

  // Match Modal
  const [matchModalJob, setMatchModalJob] = useState(null);
  const [matchData, setMatchData] = useState(null);
  const [matchLoading, setMatchLoading] = useState(false);

  // Comparison Drawer & Modal
  const [selectedForCompare, setSelectedForCompare] = useState([]);
  const [comparisonModalOpen, setComparisonModalOpen] = useState(false);
  const [comparisonData, setComparisonData] = useState(null);
  const [comparisonLoading, setComparisonLoading] = useState(false);

  // Telemetry Modal
  const [telemetryModalOpen, setTelemetryModalOpen] = useState(false);
  const [telemetryData, setTelemetryData] = useState(null);
  const [telemetryLoading, setTelemetryLoading] = useState(false);

  // Quick match cache for cards
  const [cardMatches, setCardMatches] = useState({});

  const loadSavedJobs = useCallback(async () => {
    try {
      const res = await skillService.getSavedJobs();
      if (res && res.saved_jobs) {
        setSavedJobIds(new Set(res.saved_jobs.map((j) => j.id)));
      }
    } catch {
      // Saved jobs failure non-blocking
    }
  }, []);

  const loadJobs = useCallback(async () => {
    setLoading(true);
    try {
      if (showSavedOnly) {
        const res = await skillService.getSavedJobs();
        const list = res.saved_jobs || [];
        setJobs(list);
        setTotalCount(list.length);
      } else {
        const params = {
          per_page: 30,
        };
        if (searchQuery.trim()) params.query = searchQuery.trim();
        if (selectedDomain !== 'All Domains') params.domain = selectedDomain;
        if (selectedJobType !== 'All Types') params.job_type = selectedJobType;
        if (remoteOnly) params.remote_only = true;
        if (sourceFilter === 'sample') params.sample_only = true;
        if (sourceFilter === 'live') params.live_only = true;

        const res = await skillService.getJobs(params);
        setJobs(res.jobs || []);
        setTotalCount(res.total_count || 0);
      }
    } catch {
      setAlert({ type: 'error', message: 'Failed to retrieve job opportunities.' });
    } finally {
      setLoading(false);
    }
  }, [searchQuery, selectedDomain, selectedJobType, remoteOnly, sourceFilter, showSavedOnly]);

  useEffect(() => {
    loadSavedJobs();
    loadJobs();
  }, [loadSavedJobs, loadJobs]);

  // Handle Sync
  const handleSyncJobs = async () => {
    setSyncing(true);
    setAlert(null);
    try {
      const res = await skillService.syncJobs();
      setAlert({
        type: 'success',
        message: `Synced ${res.new_jobs_added} new live opportunities (${res.total_jobs_in_db} total in catalog).`
      });
      loadJobs();
    } catch {
      setAlert({ type: 'error', message: 'Failed to synchronize live job sources.' });
    } finally {
      setSyncing(false);
    }
  };

  // Handle Save / Unsave
  const handleToggleSave = async (job) => {
    const isSaved = savedJobIds.has(job.id);
    try {
      if (isSaved) {
        await skillService.unsaveJob(job.id);
        const updated = new Set(savedJobIds);
        updated.delete(job.id);
        setSavedJobIds(updated);
        if (showSavedOnly) {
          setJobs(jobs.filter((j) => j.id !== job.id));
        }
      } else {
        await skillService.saveJob(job.id);
        const updated = new Set(savedJobIds);
        updated.add(job.id);
        setSavedJobIds(updated);
      }
    } catch {
      setAlert({ type: 'error', message: 'Could not update saved job status.' });
    }
  };

  // Open Match Breakdown
  const handleOpenMatch = async (job) => {
    setMatchModalJob(job);
    setMatchLoading(true);
    setMatchData(null);
    try {
      const res = await skillService.getJobMatch(job.id);
      setMatchData(res.match);
      setCardMatches((prev) => ({ ...prev, [job.id]: res.match.match_score }));
    } catch {
      setAlert({ type: 'error', message: 'Could not compute explainable match score.' });
    } finally {
      setMatchLoading(false);
    }
  };

  // Toggle selection for comparison
  const toggleCompare = (jobId) => {
    if (selectedForCompare.includes(jobId)) {
      setSelectedForCompare(selectedForCompare.filter((id) => id !== jobId));
    } else {
      if (selectedForCompare.length >= 3) {
        setAlert({ type: 'warning', message: 'You can compare a maximum of 3 jobs at once.' });
        return;
      }
      setSelectedForCompare([...selectedForCompare, jobId]);
    }
  };

  // Open Multi-Job Comparison
  const handleOpenComparison = async () => {
    if (selectedForCompare.length < 2) {
      setAlert({ type: 'warning', message: 'Select at least 2 jobs to compare.' });
      return;
    }
    setComparisonLoading(true);
    setComparisonModalOpen(true);
    try {
      const res = await skillService.compareJobs(selectedForCompare);
      setComparisonData(res.comparison);
    } catch {
      setAlert({ type: 'error', message: 'Could not generate job comparison.' });
      setComparisonModalOpen(false);
    } finally {
      setComparisonLoading(false);
    }
  };

  // Open Telemetry
  const handleOpenTelemetry = async () => {
    setTelemetryLoading(true);
    setTelemetryModalOpen(true);
    try {
      const res = await skillService.getJobQualityMetrics();
      setTelemetryData(res.metrics);
    } catch {
      setAlert({ type: 'error', message: 'Could not fetch data telemetry.' });
    } finally {
      setTelemetryLoading(false);
    }
  };

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="font-heading text-2xl font-bold text-white">
                Job & Internship Discovery
              </h1>
              <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-accent-500/15 text-accent-300 border border-accent-500/30">
                Explainable Matching Engine
              </span>
            </div>
            <p className="text-white/50 text-sm mt-1">
              Discover real-world openings and curated benchmarks scored transparently against your verified skills.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleOpenTelemetry}
              className="btn-ghost text-xs py-2 px-3 flex items-center space-x-1.5"
              title="Inspect discovery pipeline metrics"
            >
              <TbChartBar className="w-4 h-4 text-accent-300" />
              <span>Data Telemetry</span>
            </button>
            <button
              onClick={handleSyncJobs}
              disabled={syncing}
              className="btn-primary text-xs py-2 px-3.5 flex items-center space-x-1.5 shadow-glow"
            >
              <TbRefresh className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
              <span>{syncing ? 'Syncing...' : 'Sync Live Feeds'}</span>
            </button>
          </div>
        </div>

        {alert && (
          <AlertBanner
            type={alert.type}
            message={alert.message}
            onClose={() => setAlert(null)}
          />
        )}

        {/* Search & Filter Bar */}
        <div className="surface p-4 rounded-2xl border border-base-700/60 space-y-3">
          <div className="flex flex-col sm:flex-row gap-2">
            <div className="relative flex-1">
              <TbSearch className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/40 w-4 h-4" />
              <input
                type="text"
                placeholder="Search jobs by title, company, or required skill (e.g., Python, React, Cloud)..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="input-field pl-10 text-xs py-2.5 w-full bg-base-950/80 border-base-700/80 rounded-xl"
              />
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowSavedOnly(!showSavedOnly)}
                className={`text-xs px-3.5 py-2 rounded-xl border flex items-center space-x-1.5 transition-all ${
                  showSavedOnly
                    ? 'bg-rose-500/20 text-rose-300 border-rose-500/40 shadow-glow'
                    : 'bg-base-950/80 text-white/70 border-base-700/80 hover:text-white'
                }`}
              >
                {showSavedOnly ? <TbBookmarkFilled className="w-3.5 h-3.5" /> : <TbBookmark className="w-3.5 h-3.5" />}
                <span>Saved Only ({savedJobIds.size})</span>
              </button>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-base-800 text-xs">
            {/* Domain Dropdown */}
            <select
              value={selectedDomain}
              onChange={(e) => setSelectedDomain(e.target.value)}
              className="bg-base-950 border border-base-700 text-white/80 rounded-xl px-2.5 py-1.5 text-xs focus:border-accent-400 outline-none"
            >
              {DOMAINS.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>

            {/* Job Type Dropdown */}
            <select
              value={selectedJobType}
              onChange={(e) => setSelectedJobType(e.target.value)}
              className="bg-base-950 border border-base-700 text-white/80 rounded-xl px-2.5 py-1.5 text-xs focus:border-accent-400 outline-none"
            >
              {JOB_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>

            {/* Source Pill Filter */}
            <div className="flex items-center bg-base-950 p-0.5 rounded-xl border border-base-800">
              <button
                onClick={() => setSourceFilter('all')}
                className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all ${
                  sourceFilter === 'all'
                    ? 'bg-accent-500/20 text-accent-300'
                    : 'text-white/50 hover:text-white'
                }`}
              >
                All Sources
              </button>
              <button
                onClick={() => setSourceFilter('live')}
                className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all ${
                  sourceFilter === 'live'
                    ? 'bg-emerald-500/20 text-emerald-300'
                    : 'text-white/50 hover:text-white'
                }`}
              >
                Live Feeds
              </button>
              <button
                onClick={() => setSourceFilter('sample')}
                className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all ${
                  sourceFilter === 'sample'
                    ? 'bg-purple-500/20 text-purple-300'
                    : 'text-white/50 hover:text-white'
                }`}
              >
                Curated Benchmarks
              </button>
            </div>

            {/* Remote Only Toggle */}
            <label className="flex items-center space-x-1.5 cursor-pointer ml-auto text-white/70 hover:text-white">
              <input
                type="checkbox"
                checked={remoteOnly}
                onChange={(e) => setRemoteOnly(e.target.checked)}
                className="w-3.5 h-3.5 accent-accent-400 rounded bg-base-950 border-base-700"
              />
              <span className="text-[11px]">Remote Only</span>
            </label>
          </div>
        </div>

        {/* Results Count & Selection Bar */}
        <div className="flex items-center justify-between text-xs text-white/50 px-1">
          <span>
            Showing <strong className="text-white font-mono">{jobs.length}</strong> of{' '}
            <strong className="text-white font-mono">{totalCount}</strong> opportunities
          </span>
          {selectedForCompare.length > 0 && (
            <span className="text-accent-300 font-medium">
              {selectedForCompare.length} selected for comparison
            </span>
          )}
        </div>

        {/* Jobs Grid */}
        {loading ? (
          <div className="py-20 text-center space-y-3">
            <div className="w-8 h-8 border-2 border-accent-400/30 border-t-accent-400 rounded-full animate-spin mx-auto" />
            <p className="text-xs text-white/50">Analyzing and retrieving matching job opportunities...</p>
          </div>
        ) : jobs.length === 0 ? (
          <div className="surface p-12 text-center rounded-2xl border border-base-800 space-y-3">
            <TbBriefcase className="w-10 h-10 text-white/20 mx-auto" />
            <h3 className="font-heading text-sm font-semibold text-white">No Matching Opportunities Found</h3>
            <p className="text-xs text-white/50 max-w-sm mx-auto">
              Try adjusting your search terms, removing filters, or syncing live feeds to fetch the latest postings.
            </p>
            <button
              onClick={() => {
                setSearchQuery('');
                setSelectedDomain('All Domains');
                setSelectedJobType('All Types');
                setRemoteOnly(false);
                setSourceFilter('all');
                setShowSavedOnly(false);
              }}
              className="btn-ghost text-xs py-1.5 px-3 mx-auto"
            >
              Reset All Filters
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {jobs.map((job) => {
              const isSaved = savedJobIds.has(job.id);
              const isSelected = selectedForCompare.includes(job.id);
              const score = cardMatches[job.id];

              return (
                <div
                  key={job.id}
                  className={`surface p-5 rounded-2xl border transition-all duration-200 flex flex-col justify-between group ${
                    isSelected
                      ? 'border-accent-400/60 bg-accent-500/5 shadow-glow'
                      : 'border-base-700/60 hover:border-base-600 bg-base-900/40'
                  }`}
                >
                  <div className="space-y-3">
                    {/* Top Row: Meta badges & actions */}
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex flex-wrap items-center gap-1.5">
                        {/* Sample vs Live Feed */}
                        {job.is_sample ? (
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-purple-500/15 text-purple-300 border border-purple-500/30">
                            Benchmark Data
                          </span>
                        ) : (
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                            Live Feed
                          </span>
                        )}

                        <span className="text-[10px] px-2 py-0.5 rounded-md bg-base-800 text-white/70 border border-base-700">
                          {job.job_type}
                        </span>

                        {job.remote_policy && (
                          <span className="text-[10px] px-2 py-0.5 rounded-md bg-teal-500/10 text-teal-300 border border-teal-500/20 flex items-center space-x-1">
                            <TbWorld className="w-3 h-3" />
                            <span>{job.remote_policy}</span>
                          </span>
                        )}
                      </div>

                      <div className="flex items-center space-x-1">
                        {/* Comparison checkbox */}
                        <button
                          type="button"
                          onClick={() => toggleCompare(job.id)}
                          className={`p-1.5 rounded-lg border text-xs transition-colors ${
                            isSelected
                              ? 'bg-accent-500/20 text-accent-300 border-accent-400/50'
                              : 'border-base-700 text-white/30 hover:text-white hover:bg-white/5'
                          }`}
                          title="Select to compare side-by-side"
                        >
                          <TbArrowsDiff className="w-3.5 h-3.5" />
                        </button>

                        {/* Save Button */}
                        <button
                          type="button"
                          onClick={() => handleToggleSave(job)}
                          className={`p-1.5 rounded-lg transition-colors ${
                            isSaved
                              ? 'text-rose-400 hover:text-rose-300 bg-rose-500/10'
                              : 'text-white/30 hover:text-white hover:bg-white/5'
                          }`}
                          title={isSaved ? 'Remove from saved' : 'Save opportunity'}
                        >
                          {isSaved ? (
                            <TbBookmarkFilled className="w-4 h-4" />
                          ) : (
                            <TbBookmark className="w-4 h-4" />
                          )}
                        </button>
                      </div>
                    </div>

                    {/* Job Title & Company */}
                    <div>
                      <h3 className="font-heading text-base font-semibold text-white group-hover:text-accent-300 transition-colors">
                        {job.title}
                      </h3>
                      <div className="flex items-center space-x-3 text-xs text-white/50 mt-1">
                        <span className="flex items-center space-x-1 text-white/80">
                          <TbBuilding className="w-3.5 h-3.5 text-accent-400" />
                          <span>{job.company}</span>
                        </span>
                        <span className="flex items-center space-x-1">
                          <TbMapPin className="w-3.5 h-3.5" />
                          <span>{job.location}</span>
                        </span>
                      </div>
                    </div>

                    {/* Description preview */}
                    <p className="text-xs text-white/60 line-clamp-2 leading-relaxed">
                      {job.description}
                    </p>

                    {/* Skills Chips */}
                    <div className="space-y-1.5 pt-1">
                      <div className="flex flex-wrap gap-1">
                        {(job.required_skills || []).slice(0, 5).map((skill, idx) => (
                          <span
                            key={idx}
                            className="text-[11px] px-2 py-0.5 rounded-md bg-base-950 text-white/80 border border-base-800"
                          >
                            {skill}
                          </span>
                        ))}
                        {(job.required_skills || []).length > 5 && (
                          <span className="text-[10px] text-white/40 self-center">
                            +{(job.required_skills || []).length - 5} more
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Card Bottom Action Bar */}
                  <div className="pt-4 mt-4 border-t border-base-800/80 flex items-center justify-between gap-2">
                    <button
                      onClick={() => handleOpenMatch(job)}
                      className="btn-primary text-xs py-1.5 px-3 flex items-center space-x-1.5 flex-1 justify-center shadow-glow"
                    >
                      <TbSparkles className="w-3.5 h-3.5" />
                      <span>{score !== undefined ? `Match: ${score}%` : 'Explain Match'}</span>
                    </button>

                    <button
                      onClick={() =>
                        navigate(
                          `/interview-prep?job_id=${job.id}&role=${encodeURIComponent(job.title)}`
                        )
                      }
                      className="btn-ghost text-xs py-1.5 px-3 flex items-center space-x-1.5"
                      title="Practice realistic interview for this role"
                    >
                      <TbMicrophone className="w-3.5 h-3.5 text-teal-300" />
                      <span>Practice</span>
                    </button>

                    {job.application_url && (
                      <a
                        href={job.application_url}
                        target="_blank"
                        rel="noreferrer"
                        className="p-2 rounded-xl text-white/40 hover:text-white hover:bg-white/5 transition-colors border border-base-800"
                        title="View original posting"
                      >
                        <TbExternalLink className="w-3.5 h-3.5" />
                      </a>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Floating Bottom Comparison Bar */}
        {selectedForCompare.length >= 2 && (
          <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 bg-base-900/90 border border-accent-400/40 rounded-2xl p-3 shadow-2xl backdrop-blur-xl flex items-center space-x-4 animate-slide-up">
            <div className="flex items-center space-x-2 text-xs text-white">
              <TbScale className="w-4 h-4 text-accent-300" />
              <span>
                <strong>{selectedForCompare.length}</strong> opportunities selected
              </span>
            </div>
            <button
              onClick={handleOpenComparison}
              disabled={comparisonLoading}
              className="btn-primary text-xs py-1.5 px-4 shadow-glow"
            >
              {comparisonLoading ? 'Comparing...' : 'Compare Side-by-Side'}
            </button>
            <button
              onClick={() => setSelectedForCompare([])}
              className="text-xs text-white/40 hover:text-white"
            >
              Clear
            </button>
          </div>
        )}

        {/* Explainable Match Modal */}
        {matchModalJob && (
          <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="surface max-w-2xl w-full rounded-3xl border border-accent-400/30 p-6 max-h-[90vh] overflow-y-auto space-y-5 animate-scale-in">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-accent-500/20 text-accent-300 border border-accent-400/30">
                      Explainable Fit Breakdown
                    </span>
                    {matchModalJob.is_sample && (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-500/20 text-purple-300">
                        Benchmark Profile
                      </span>
                    )}
                  </div>
                  <h2 className="font-heading text-lg font-bold text-white mt-1">
                    {matchModalJob.title}
                  </h2>
                  <p className="text-xs text-white/50">{matchModalJob.company} · {matchModalJob.location}</p>
                </div>
                <button
                  onClick={() => setMatchModalJob(null)}
                  className="p-1.5 rounded-lg text-white/40 hover:text-white hover:bg-white/10"
                >
                  <TbX className="w-4 h-4" />
                </button>
              </div>

              {matchLoading ? (
                <div className="py-12 text-center space-y-3">
                  <div className="w-8 h-8 border-2 border-accent-400/30 border-t-accent-400 rounded-full animate-spin mx-auto" />
                  <p className="text-xs text-white/50">Calculating 4-pillar deterministic match matrix...</p>
                </div>
              ) : matchData ? (
                <div className="space-y-5">
                  {/* Total Deterministic Score Card */}
                  <div className="bg-base-950/80 p-4 rounded-2xl border border-base-800 flex items-center justify-between">
                    <div>
                      <div className="text-xs text-white/40">Deterministic Fit Score</div>
                      <div className="font-heading text-3xl font-bold text-white flex items-baseline space-x-1.5">
                        <span className={matchData.match_score >= 70 ? 'text-emerald-400' : matchData.match_score >= 45 ? 'text-amber-400' : 'text-rose-400'}>
                          {matchData.match_score}%
                        </span>
                        <span className="text-xs text-white/40">/ 100%</span>
                      </div>
                      <p className="text-[11px] text-white/50 mt-1">
                        Calculated deterministically without generative hallucination.
                      </p>
                    </div>

                    <button
                      onClick={() => {
                        setMatchModalJob(null);
                        navigate(`/interview-prep?job_id=${matchModalJob.id}&role=${encodeURIComponent(matchModalJob.title)}`);
                      }}
                      className="btn-primary text-xs py-2 px-3.5 flex items-center space-x-1.5 shadow-glow"
                    >
                      <TbMicrophone className="w-4 h-4" />
                      <span>Prepare Interview</span>
                    </button>
                  </div>

                  {/* 4 Scoring Pillars Breakdown */}
                  <div className="space-y-3">
                    <h4 className="text-xs font-semibold text-white/80 uppercase tracking-wider font-mono">
                      Deterministic Weight Allocation
                    </h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                      {/* Mandatory Skills (50%) */}
                      <div className="bg-base-950/60 p-3 rounded-xl border border-base-800 space-y-1.5">
                        <div className="flex justify-between items-center">
                          <span className="text-white/70 font-medium">Mandatory Skills</span>
                          <span className="text-accent-300 font-mono font-bold">
                            {matchData.scoring_breakdown?.mandatory_skills_score}% (50% wt)
                          </span>
                        </div>
                        <ProgressBar
                          progress={matchData.scoring_breakdown?.mandatory_skills_score || 0}
                          size="sm"
                        />
                      </div>

                      {/* Preferred Skills (20%) */}
                      <div className="bg-base-950/60 p-3 rounded-xl border border-base-800 space-y-1.5">
                        <div className="flex justify-between items-center">
                          <span className="text-white/70 font-medium">Preferred Skills</span>
                          <span className="text-accent-300 font-mono font-bold">
                            {matchData.scoring_breakdown?.preferred_skills_score}% (20% wt)
                          </span>
                        </div>
                        <ProgressBar
                          progress={matchData.scoring_breakdown?.preferred_skills_score || 0}
                          size="sm"
                        />
                      </div>

                      {/* Transferable Skills (15%) */}
                      <div className="bg-base-950/60 p-3 rounded-xl border border-base-800 space-y-1.5">
                        <div className="flex justify-between items-center">
                          <span className="text-white/70 font-medium">Transferable Bridges</span>
                          <span className="text-accent-300 font-mono font-bold">
                            {matchData.scoring_breakdown?.transferable_skills_score}% (15% wt)
                          </span>
                        </div>
                        <ProgressBar
                          progress={matchData.scoring_breakdown?.transferable_skills_score || 0}
                          size="sm"
                        />
                      </div>

                      {/* Eligibility & Experience (15%) */}
                      <div className="bg-base-950/60 p-3 rounded-xl border border-base-800 space-y-1.5">
                        <div className="flex justify-between items-center">
                          <span className="text-white/70 font-medium">Role Eligibility</span>
                          <span className="text-accent-300 font-mono font-bold">
                            {matchData.scoring_breakdown?.experience_eligibility_score}% (15% wt)
                          </span>
                        </div>
                        <ProgressBar
                          progress={matchData.scoring_breakdown?.experience_eligibility_score || 0}
                          size="sm"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Transferable Skill Bridges */}
                  {matchData.transferable_bridges && matchData.transferable_bridges.length > 0 && (
                    <div className="bg-teal-950/20 p-3.5 rounded-2xl border border-teal-500/30 space-y-2">
                      <div className="flex items-center space-x-1.5 text-xs text-teal-300 font-semibold">
                        <TbSparkles className="w-4 h-4" />
                        <span>Transferable Skill Bridges Identified</span>
                      </div>
                      <p className="text-[11px] text-white/60">
                        Your existing skills provide partial competency transfer for these requirements:
                      </p>
                      <div className="space-y-1">
                        {matchData.transferable_bridges.map((bridge, bIdx) => (
                          <div
                            key={bIdx}
                            className="flex items-center justify-between text-xs bg-base-950/60 px-2.5 py-1.5 rounded-lg border border-teal-500/20"
                          >
                            <span className="text-white/80">
                              <strong className="text-teal-200">{bridge.user_skill}</strong>{' '}
                              transfers to{' '}
                              <strong className="text-accent-300">{bridge.target_skill}</strong>
                            </span>
                            <span className="text-[10px] font-mono text-teal-400">
                              {(bridge.transfer_coefficient * 100).toFixed(0)}% affinity
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Matched vs Missing Skills breakdown */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                    {/* Satisfied Skills */}
                    <div className="space-y-2">
                      <h5 className="font-semibold text-emerald-400 flex items-center space-x-1">
                        <TbCheck className="w-4 h-4" />
                        <span>Matched Skills ({matchData.matched_skills?.length || 0})</span>
                      </h5>
                      <div className="space-y-1">
                        {(matchData.matched_skills || []).map((ms, idx) => (
                          <div
                            key={idx}
                            className="flex items-center justify-between bg-base-950/60 px-2.5 py-1.5 rounded-lg border border-base-800"
                          >
                            <span className="text-white/80">{ms.skill}</span>
                            <span
                              className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                                ms.is_verified
                                  ? 'bg-emerald-500/20 text-emerald-300'
                                  : 'bg-amber-500/20 text-amber-300'
                              }`}
                            >
                              {ms.is_verified ? 'Verified Quiz' : 'Resume Only'}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Missing Skills with Curated Resources */}
                    <div className="space-y-2">
                      <h5 className="font-semibold text-rose-400 flex items-center space-x-1">
                        <TbX className="w-4 h-4" />
                        <span>Missing Skill Gaps ({matchData.missing_mandatory_skills?.length || 0})</span>
                      </h5>
                      <div className="space-y-1.5">
                        {(matchData.missing_mandatory_skills || []).map((skill, idx) => {
                          const links = matchData.resource_recommendations?.[skill] || {};
                          return (
                            <div
                              key={idx}
                              className="bg-base-950/60 p-2 rounded-lg border border-base-800 space-y-1"
                            >
                              <div className="flex items-center justify-between">
                                <span className="text-white/80 font-medium">{skill}</span>
                                <span className="text-[10px] font-mono text-rose-400">Mandatory</span>
                              </div>
                              <div className="flex items-center gap-2 pt-0.5 text-[10px]">
                                {links.youtube && (
                                  <a
                                    href={links.youtube}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="text-red-400 hover:text-red-300 flex items-center space-x-1"
                                  >
                                    <TbBrandYoutube className="w-3 h-3" />
                                    <span>Tutorial</span>
                                  </a>
                                )}
                                {links.github && (
                                  <a
                                    href={links.github}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="text-white/60 hover:text-white flex items-center space-x-1"
                                  >
                                    <TbBrandGithub className="w-3 h-3" />
                                    <span>Projects</span>
                                  </a>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        )}

        {/* Multi-Job Comparison Modal */}
        {comparisonModalOpen && (
          <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="surface max-w-4xl w-full rounded-3xl border border-accent-400/30 p-6 max-h-[90vh] overflow-y-auto space-y-5 animate-scale-in">
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-accent-500/20 text-accent-300 border border-accent-400/30">
                    Side-by-Side Analysis
                  </span>
                  <h2 className="font-heading text-lg font-bold text-white mt-1">
                    Multi-Opportunity Comparison
                  </h2>
                </div>
                <button
                  onClick={() => setComparisonModalOpen(false)}
                  className="p-1.5 rounded-lg text-white/40 hover:text-white hover:bg-white/10"
                >
                  <TbX className="w-4 h-4" />
                </button>
              </div>

              {comparisonLoading ? (
                <div className="py-12 text-center space-y-3">
                  <div className="w-8 h-8 border-2 border-accent-400/30 border-t-accent-400 rounded-full animate-spin mx-auto" />
                  <p className="text-xs text-white/50">Comparing skill matrices and overlap...</p>
                </div>
              ) : comparisonData ? (
                <div className="space-y-5">
                  {/* High Yield Overlapping Skills Highlight */}
                  {comparisonData.high_yield_overlapping_skills?.length > 0 && (
                    <div className="bg-gradient-to-r from-accent-500/10 to-teal-500/10 p-4 rounded-2xl border border-accent-400/30 space-y-2">
                      <div className="flex items-center space-x-2 text-accent-300 text-xs font-semibold">
                        <TbSparkles className="w-4 h-4" />
                        <span>High-Yield Overlapping Skills</span>
                      </div>
                      <p className="text-xs text-white/70">
                        Mastering these skills simultaneously addresses requirements across multiple selected opportunities:
                      </p>
                      <div className="flex flex-wrap gap-2 pt-1">
                        {comparisonData.high_yield_overlapping_skills.map((skill, sIdx) => (
                          <span
                            key={sIdx}
                            className="text-xs font-mono px-3 py-1 rounded-xl bg-accent-500/20 text-accent-200 border border-accent-400/40 font-bold"
                          >
                            ★ {skill}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Side by side columns */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {(comparisonData.jobs || []).map((cJob) => (
                      <div
                        key={cJob.job_id}
                        className="bg-base-950/70 p-4 rounded-2xl border border-base-800 space-y-3"
                      >
                        <div>
                          <h4 className="font-heading text-sm font-bold text-white">
                            {cJob.title}
                          </h4>
                          <p className="text-xs text-white/50">{cJob.company}</p>
                        </div>

                        <div className="bg-base-900/80 p-3 rounded-xl border border-base-800">
                          <div className="text-[10px] text-white/40">Fit Score</div>
                          <div className="font-heading text-2xl font-bold text-accent-300">
                            {cJob.match_score}%
                          </div>
                        </div>

                        <div className="space-y-1.5 text-xs">
                          <div className="text-[11px] font-semibold text-emerald-400">
                            Matched ({cJob.matched_skills_count})
                          </div>
                          <div className="flex flex-wrap gap-1">
                            {(cJob.matched_skills || []).map((s, idx) => (
                              <span
                                key={idx}
                                className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20"
                              >
                                {s}
                              </span>
                            ))}
                          </div>
                        </div>

                        <div className="space-y-1.5 text-xs">
                          <div className="text-[11px] font-semibold text-rose-400">
                            Missing Mandatory ({cJob.missing_mandatory?.length || 0})
                          </div>
                          <div className="flex flex-wrap gap-1">
                            {(cJob.missing_mandatory || []).map((s, idx) => (
                              <span
                                key={idx}
                                className="text-[10px] px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-300 border border-rose-500/20"
                              >
                                {s}
                              </span>
                            ))}
                          </div>
                        </div>

                        <button
                          onClick={() => {
                            setComparisonModalOpen(false);
                            navigate(
                              `/interview-prep?job_id=${cJob.job_id}&role=${encodeURIComponent(
                                cJob.title
                              )}`
                            );
                          }}
                          className="btn-ghost text-xs w-full py-1.5 mt-2 flex items-center justify-center space-x-1"
                        >
                          <TbMicrophone className="w-3.5 h-3.5 text-teal-300" />
                          <span>Interview Prep</span>
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        )}

        {/* Telemetry / Data Quality Modal */}
        {telemetryModalOpen && (
          <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="surface max-w-xl w-full rounded-3xl border border-accent-400/30 p-6 space-y-5 animate-scale-in">
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-accent-500/20 text-accent-300 border border-accent-400/30">
                    Live Data Pipeline Telemetry
                  </span>
                  <h2 className="font-heading text-lg font-bold text-white mt-1">
                    Job Discovery Ingestion Metrics
                  </h2>
                </div>
                <button
                  onClick={() => setTelemetryModalOpen(false)}
                  className="p-1.5 rounded-lg text-white/40 hover:text-white hover:bg-white/10"
                >
                  <TbX className="w-4 h-4" />
                </button>
              </div>

              {telemetryLoading ? (
                <div className="py-8 text-center space-y-2">
                  <div className="w-6 h-6 border-2 border-accent-400/30 border-t-accent-400 rounded-full animate-spin mx-auto" />
                  <p className="text-xs text-white/50">Gathering telemetry metrics...</p>
                </div>
              ) : telemetryData ? (
                <div className="space-y-4 text-xs">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-base-950/80 p-3.5 rounded-xl border border-base-800">
                      <div className="text-white/40 text-[11px]">Total Records Ingested</div>
                      <div className="font-heading text-2xl font-bold text-white">
                        {telemetryData.total_ingested}
                      </div>
                    </div>
                    <div className="bg-base-950/80 p-3.5 rounded-xl border border-base-800">
                      <div className="text-white/40 text-[11px]">Duplicates Removed</div>
                      <div className="font-heading text-2xl font-bold text-amber-400">
                        {telemetryData.duplicates_removed}
                      </div>
                    </div>
                    <div className="bg-base-950/80 p-3.5 rounded-xl border border-base-800">
                      <div className="text-white/40 text-[11px]">Valid Schema Compliance</div>
                      <div className="font-heading text-2xl font-bold text-emerald-400">
                        {telemetryData.valid_schema_rate}%
                      </div>
                    </div>
                    <div className="bg-base-950/80 p-3.5 rounded-xl border border-base-800">
                      <div className="text-white/40 text-[11px]">Active Sources Configured</div>
                      <div className="font-heading text-2xl font-bold text-accent-300">
                        {telemetryData.sources_configured}
                      </div>
                    </div>
                  </div>

                  <div className="space-y-2 pt-2">
                    <h5 className="font-semibold text-white/70">Source Breakdown</h5>
                    <div className="space-y-1.5">
                      {Object.entries(telemetryData.source_breakdown || {}).map(([src, count]) => (
                        <div
                          key={src}
                          className="flex justify-between items-center bg-base-950/60 px-3 py-2 rounded-xl border border-base-800"
                        >
                          <span className="font-mono text-white/80">{src}</span>
                          <span className="font-mono font-bold text-accent-300">{count} listings</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
