import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import AppLayout from '../components/AppLayout';
import AlertBanner from '../components/AlertBanner';
import ProgressBar from '../components/ProgressBar';
import skillService from '../services/skillService';
import authService from '../services/authService';
import JobAlertsPanel from '../components/JobAlertsPanel';
import {
  TbBell,
  TbClock,
  TbShieldCheck,
  TbAlertTriangle,
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
  TbScale,
  TbSend
} from 'react-icons/tb';


// Must match backend CAREER_CATEGORY_RULES (utils/job_discovery/normalizer.py)
const DOMAINS = [
  'All Domains',
  'Software Development',
  'Backend Engineering',
  'Frontend Engineering',
  'Full Stack Development',
  'Data Analytics',
  'Data Science',
  'Data Engineering',
  'Machine Learning & AI',
  'Cloud & DevOps',
  'Cybersecurity',
  'Mobile Development',
  'QA & Testing'
];

const JOB_TYPES = ['All Types', 'Full-time', 'Internship', 'Contract', 'Part-time'];

const WORK_MODES = ['All Work Modes', 'Remote', 'Hybrid', 'Onsite'];

const DATE_POSTED = [
  { value: '', label: 'Any time' },
  { value: '24h', label: 'Last 24 hours' },
  { value: '3d', label: 'Last 3 days' },
  { value: '7d', label: 'Last 7 days' },
  { value: '30d', label: 'Last 30 days' }
];

const SORTS = [
  { value: 'relevance', label: 'Relevance (India first)' },
  { value: 'recent', label: 'Most recently posted' },
  { value: 'match', label: 'Best skill match' },
  { value: 'salary', label: 'Highest salary (where stated)' }
];

const PER_PAGE = 20;

function formatSalary(salary) {
  if (!salary || (salary.min == null && salary.max == null)) return null;
  const fmt = (v) => {
    if (v == null) return null;
    if (salary.currency === 'INR') {
      return v >= 100000 ? `₹${(v / 100000).toFixed(1)}L` : `₹${Math.round(v).toLocaleString('en-IN')}`;
    }
    return `${salary.currency || ''} ${Math.round(v).toLocaleString()}`.trim();
  };
  const range = salary.min != null && salary.max != null && salary.min !== salary.max
    ? `${fmt(salary.min)}–${fmt(salary.max)}`
    : fmt(salary.max ?? salary.min);
  return `${range}${salary.period ? ` / ${salary.period}` : ''}`;
}

function relativeTime(iso) {
  if (!iso) return null;
  const diffMin = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (diffMin < 0) return `in ${Math.abs(diffMin) < 60 ? `${Math.abs(diffMin)} min` : `${Math.round(Math.abs(diffMin) / 60)} h`}`;
  if (diffMin < 60) return `${diffMin} min ago`;
  if (diffMin < 60 * 48) return `${Math.round(diffMin / 60)} h ago`;
  return `${Math.round(diffMin / 1440)} days ago`;
}

const VERIFICATION_BADGE = {
  verified: { label: 'Checked < 24h ago', cls: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30' },
  unverified_recently: { label: 'Not re-checked recently', cls: 'bg-amber-500/15 text-amber-300 border-amber-500/30' },
  unverified: { label: 'Unverified', cls: 'bg-amber-500/15 text-amber-300 border-amber-500/30' },
  expired: { label: 'Expired / archived', cls: 'bg-rose-500/15 text-rose-300 border-rose-500/30' },
  sample: { label: 'Demo listing', cls: 'bg-purple-500/15 text-purple-300 border-purple-500/30' }
};

const REGIONS = [
  { value: 'All Regions', label: 'All Regions (India & Asia First)' },
  { value: 'India', label: '🇮🇳 India' },
  { value: 'Asia', label: '🌏 Asia' },
  { value: 'Remote', label: '🌐 Remote' }
];

function cleanDescription(text) {
  if (!text) return '';
  const decoded = text
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, ' ');
  return decoded.replace(/<[^>]*>/g, '').trim();
}

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
  const [selectedRegion, setSelectedRegion] = useState('All Regions');
  const [workMode, setWorkMode] = useState('All Work Modes');
  const [opportunity, setOpportunity] = useState('all'); // 'all' | 'job' | 'internship'
  const [entryLevel, setEntryLevel] = useState(false);
  const [locationFilter, setLocationFilter] = useState('');
  const [companyFilter, setCompanyFilter] = useState('');
  const [skillFilter, setSkillFilter] = useState('');
  const [experienceMax, setExperienceMax] = useState('');
  const [salaryMinLpa, setSalaryMinLpa] = useState('');
  const [datePosted, setDatePosted] = useState('');
  const [sortBy, setSortBy] = useState('relevance');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [showSavedOnly, setShowSavedOnly] = useState(false);

  // Sync status & role
  const [isAdmin, setIsAdmin] = useState(false);
  const [syncInfo, setSyncInfo] = useState(null);

  // Alerts panel
  const [alertsPanelOpen, setAlertsPanelOpen] = useState(false);
  const [unreadAlerts, setUnreadAlerts] = useState(0);

  // Saved Jobs tracking
  const [savedJobIds, setSavedJobIds] = useState(new Set());

  // Applied Jobs tracking
  const [appliedJobsMap, setAppliedJobsMap] = useState({});
  const [showAppliedOnly, setShowAppliedOnly] = useState(false);

  // Apply Modal state
  const [applyModalJob, setApplyModalJob] = useState(null);
  const [applying, setApplying] = useState(false);
  const [applyForm, setApplyForm] = useState({
    cover_note: '',
    portfolio_url: '',
    contact_email: ''
  });

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

  const loadAppliedJobs = useCallback(async () => {
    try {
      const res = await skillService.getAppliedJobs();
      if (res && res.applications) {
        const map = {};
        res.applications.forEach((a) => {
          map[a.job_id] = a;
        });
        setAppliedJobsMap(map);
      }
    } catch {
      // Applied jobs failure non-blocking
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
      } else if (showAppliedOnly) {
        const res = await skillService.getAppliedJobs();
        const apps = res.applications || [];
        const list = apps.map((a) => ({
          ...(a.job || {}),
          id: a.job_id,
          is_applied: true,
          application: a
        }));
        setJobs(list);
        setTotalCount(list.length);
      } else {
        const params = {
          per_page: PER_PAGE,
          page,
          sort: sortBy,
        };
        if (searchQuery.trim()) params.query = searchQuery.trim();
        if (selectedDomain !== 'All Domains') params.domain = selectedDomain;
        if (selectedJobType !== 'All Types') params.job_type = selectedJobType;
        if (selectedRegion === 'India') params.region = 'india';
        else if (selectedRegion === 'Asia') params.region = 'asia';
        else if (selectedRegion === 'Remote') params.region = 'remote';
        if (workMode !== 'All Work Modes') params.work_arrangement = workMode;
        if (opportunity !== 'all') params.opportunity = opportunity;
        if (entryLevel) params.entry_level = true;
        if (locationFilter.trim()) params.location = locationFilter.trim();
        if (companyFilter.trim()) params.company = companyFilter.trim();
        if (skillFilter.trim()) params.skill = skillFilter.trim();
        if (experienceMax !== '') params.experience_max = experienceMax;
        if (salaryMinLpa !== '') params.salary_min = Number(salaryMinLpa) * 100000;
        if (datePosted) params.date_posted = datePosted;

        const res = await skillService.getJobs(params);
        const list = res.jobs || [];
        setJobs(list);
        setTotalCount(res.total_count ?? res.total ?? list.length);
        setTotalPages(res.pages || 1);
        // match scores now come with each listing
        const scores = {};
        list.forEach((j) => {
          if (j.match_score !== undefined) scores[j.id] = j.match_score;
        });
        setCardMatches((prev) => ({ ...prev, ...scores }));
      }
    } catch {
      setAlert({ type: 'error', message: 'Failed to retrieve job opportunities.' });
    } finally {
      setLoading(false);
    }
  }, [searchQuery, selectedDomain, selectedJobType, selectedRegion, workMode, opportunity, entryLevel,
      locationFilter, companyFilter, skillFilter, experienceMax, salaryMinLpa, datePosted, sortBy, page,
      showSavedOnly, showAppliedOnly]);

  const loadSyncInfo = useCallback(async () => {
    try {
      const res = await skillService.getJobQualityMetrics();
      setSyncInfo(res?.metrics || res);
    } catch {
      // status line is informational only
    }
  }, []);

  const loadUnreadAlerts = useCallback(async () => {
    try {
      const res = await skillService.getJobAlertNotifications();
      setUnreadAlerts(res.unread_count || 0);
    } catch {
      // non-blocking
    }
  }, []);

  useEffect(() => {
    authService.getCurrentUser()
      .then((u) => setIsAdmin((u?.role || '').toLowerCase() === 'admin'))
      .catch(() => setIsAdmin(false));
    loadSyncInfo();
    loadUnreadAlerts();
  }, [loadSyncInfo, loadUnreadAlerts]);

  // Debounce typing in search/text filters
  useEffect(() => {
    const t = setTimeout(() => {
      loadSavedJobs();
      loadAppliedJobs();
      loadJobs();
    }, 300);
    return () => clearTimeout(t);
  }, [loadSavedJobs, loadAppliedJobs, loadJobs]);

  // Any filter change returns to the first page
  useEffect(() => {
    setPage(1);
  }, [searchQuery, selectedDomain, selectedJobType, selectedRegion, workMode, opportunity, entryLevel,
      locationFilter, companyFilter, skillFilter, experienceMax, salaryMinLpa, datePosted, sortBy]);

  const resetFilters = () => {
    setSearchQuery('');
    setSelectedDomain('All Domains');
    setSelectedJobType('All Types');
    setSelectedRegion('All Regions');
    setWorkMode('All Work Modes');
    setOpportunity('all');
    setEntryLevel(false);
    setLocationFilter('');
    setCompanyFilter('');
    setSkillFilter('');
    setExperienceMax('');
    setSalaryMinLpa('');
    setDatePosted('');
    setSortBy('relevance');
    setShowSavedOnly(false);
    setShowAppliedOnly(false);
  };

  const handleOpenApply = (job) => {
    setApplyModalJob(job);
    setApplyForm({
      cover_note: `I am enthusiastic to apply for the ${job.title} position at ${job.company}. My verified technical competencies and practical project background align closely with your team's objectives.`,
      portfolio_url: '',
      contact_email: ''
    });
  };

  const handleSubmitApply = async (e) => {
    e.preventDefault();
    if (!applyModalJob) return;
    setApplying(true);
    try {
      const res = await skillService.applyForJob(applyModalJob.id, applyForm);
      setAppliedJobsMap((prev) => ({
        ...prev,
        [applyModalJob.id]: res.application
      }));
      setAlert({
        type: 'success',
        message: `Recorded in your tracker: ${applyModalJob.title} at ${applyModalJob.company}. ` +
          'Remember to complete the application on the employer\'s site.'
      });
      setApplyModalJob(null);
      loadJobs();
      loadAppliedJobs();
    } catch {
      setAlert({
        type: 'error',
        message: 'Failed to submit application. Please try again.'
      });
    } finally {
      setApplying(false);
    }
  };

  const handleWithdrawApply = async (jobId) => {
    try {
      await skillService.withdrawApplication(jobId);
      setAppliedJobsMap((prev) => {
        const next = { ...prev };
        delete next[jobId];
        return next;
      });
      setAlert({
        type: 'info',
        message: 'Application withdrawn successfully.'
      });
      loadJobs();
      loadAppliedJobs();
    } catch {
      setAlert({
        type: 'error',
        message: 'Failed to withdraw application.'
      });
    }
  };

  // Manual sync (administrators only - listings refresh automatically every two hours)
  const handleSyncJobs = async () => {
    setSyncing(true);
    setAlert(null);
    try {
      const res = await skillService.adminSyncJobs();
      const run = res.run || {};
      setAlert({
        type: run.status === 'success' ? 'success' : run.status === 'failed' ? 'error' : 'warning',
        message: `Sync ${run.status}: ${run.inserted_count ?? 0} new, ${run.updated_count ?? 0} updated, ` +
          `${run.expired_count ?? 0} expired.${run.error ? ` ${run.error}` : ''}`
      });
      loadJobs();
      loadSyncInfo();
    } catch (err) {
      const status = err.response?.status;
      setAlert({
        type: status === 409 ? 'warning' : 'error',
        message: status === 409
          ? 'A synchronization is already running. Please try again in a few minutes.'
          : (err.response?.data?.error || 'Failed to synchronize job sources.')
      });
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
      const matchObj = res?.match || res;
      setMatchData(matchObj);
      const score = matchObj?.match_score;
      if (score !== undefined) {
        setCardMatches((prev) => ({ ...prev, [job.id]: score }));
      }
    } catch (err) {
      console.error('getJobMatch error:', err);
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
      setComparisonData(res?.comparison || res);
    } catch (err) {
      console.error('compareJobs error:', err);
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
      setTelemetryData(res?.metrics || res);
    } catch (err) {
      console.error('getJobQualityMetrics error:', err);
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
              Real openings from authorized job sources, refreshed automatically every two hours and scored against your verified skills.
            </p>
            {syncInfo && (
              <p className="text-[11px] text-white/40 mt-1 flex items-center gap-1.5">
                <TbClock className="w-3.5 h-3.5" />
                <span>
                  {syncInfo.last_successful_sync
                    ? `Last refreshed ${relativeTime(syncInfo.last_successful_sync)}`
                    : 'Not refreshed yet'}
                  {syncInfo.next_scheduled_sync && ` · next refresh ${relativeTime(syncInfo.next_scheduled_sync)}`}
                  {syncInfo.last_sync_status && syncInfo.last_sync_status !== 'success' &&
                    ` · last run: ${syncInfo.last_sync_status}`}
                </span>
              </p>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setAlertsPanelOpen(true)}
              className="btn-ghost text-xs py-2 px-3 flex items-center space-x-1.5 relative"
              title="Job preferences and alerts"
            >
              <TbBell className="w-4 h-4 text-accent-300" />
              <span>Alerts & Preferences</span>
              {unreadAlerts > 0 && (
                <span className="ml-1 text-[10px] font-mono px-1.5 rounded-full bg-rose-500 text-white">
                  {unreadAlerts}
                </span>
              )}
            </button>
            <button
              onClick={handleOpenTelemetry}
              className="btn-ghost text-xs py-2 px-3 flex items-center space-x-1.5"
              title="Inspect discovery pipeline metrics"
            >
              <TbChartBar className="w-4 h-4 text-accent-300" />
              <span>Data Sources</span>
            </button>
            {isAdmin && (
              <button
                onClick={handleSyncJobs}
                disabled={syncing}
                className="btn-primary text-xs py-2 px-3.5 flex items-center space-x-1.5 shadow-glow"
                title="Administrators only: run a synchronization now"
              >
                <TbRefresh className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
                <span>{syncing ? 'Syncing...' : 'Sync Now'}</span>
              </button>
            )}
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
                onClick={() => {
                  const next = !showSavedOnly;
                  setShowSavedOnly(next);
                  if (next) setShowAppliedOnly(false);
                }}
                className={`text-xs px-3.5 py-2 rounded-xl border flex items-center space-x-1.5 transition-all ${
                  showSavedOnly
                    ? 'bg-rose-500/20 text-rose-300 border-rose-500/40 shadow-glow'
                    : 'bg-base-950/80 text-white/70 border-base-700/80 hover:text-white'
                }`}
              >
                {showSavedOnly ? <TbBookmarkFilled className="w-3.5 h-3.5" /> : <TbBookmark className="w-3.5 h-3.5" />}
                <span>Saved ({savedJobIds.size})</span>
              </button>

              <button
                onClick={() => {
                  const next = !showAppliedOnly;
                  setShowAppliedOnly(next);
                  if (next) setShowSavedOnly(false);
                }}
                className={`text-xs px-3.5 py-2 rounded-xl border flex items-center space-x-1.5 transition-all ${
                  showAppliedOnly
                    ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 shadow-glow'
                    : 'bg-base-950/80 text-white/70 border-base-700/80 hover:text-white'
                }`}
              >
                <TbCheck className="w-3.5 h-3.5" />
                <span>Applied ({Object.keys(appliedJobsMap).length})</span>
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

            {/* Region Dropdown */}
            <select
              value={selectedRegion}
              onChange={(e) => setSelectedRegion(e.target.value)}
              className="bg-base-950 border border-base-700 text-white/80 rounded-xl px-2.5 py-1.5 text-xs focus:border-accent-400 outline-none"
            >
              {REGIONS.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>

            {/* Work mode */}
            <select
              value={workMode}
              onChange={(e) => setWorkMode(e.target.value)}
              className="bg-base-950 border border-base-700 text-white/80 rounded-xl px-2.5 py-1.5 text-xs focus:border-accent-400 outline-none"
            >
              {WORK_MODES.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>

            {/* Job vs internship */}
            <div className="flex items-center bg-base-950 p-0.5 rounded-xl border border-base-800">
              {[['all', 'Jobs & Internships'], ['job', 'Jobs'], ['internship', 'Internships']].map(([val, label]) => (
                <button
                  key={val}
                  onClick={() => setOpportunity(val)}
                  className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all ${
                    opportunity === val ? 'bg-accent-500/20 text-accent-300' : 'text-white/50 hover:text-white'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>

            <label className="flex items-center space-x-1.5 cursor-pointer text-white/70 hover:text-white">
              <input
                type="checkbox"
                checked={entryLevel}
                onChange={(e) => setEntryLevel(e.target.checked)}
                className="w-3.5 h-3.5 accent-accent-400 rounded bg-base-950 border-base-700"
              />
              <span className="text-[11px]">Fresher / entry level</span>
            </label>

            {/* Sort */}
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="ml-auto bg-base-950 border border-base-700 text-white/80 rounded-xl px-2.5 py-1.5 text-xs focus:border-accent-400 outline-none"
              title="Sort results"
            >
              {SORTS.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>

          {/* Detailed filters */}
          <div className="grid grid-cols-2 md:grid-cols-6 gap-2 text-xs">
            <input
              type="text"
              placeholder="Location (e.g. Mangaluru)"
              value={locationFilter}
              onChange={(e) => setLocationFilter(e.target.value)}
              className="input-field text-xs py-1.5 bg-base-950/80 border-base-700/80 rounded-xl"
            />
            <input
              type="text"
              placeholder="Company"
              value={companyFilter}
              onChange={(e) => setCompanyFilter(e.target.value)}
              className="input-field text-xs py-1.5 bg-base-950/80 border-base-700/80 rounded-xl"
            />
            <input
              type="text"
              placeholder="Required skill (e.g. SQL)"
              value={skillFilter}
              onChange={(e) => setSkillFilter(e.target.value)}
              className="input-field text-xs py-1.5 bg-base-950/80 border-base-700/80 rounded-xl"
            />
            <select
              value={experienceMax}
              onChange={(e) => setExperienceMax(e.target.value)}
              className="bg-base-950 border border-base-700 text-white/80 rounded-xl px-2.5 py-1.5 text-xs outline-none"
              title="Maximum years of experience required"
            >
              <option value="">Any experience</option>
              <option value="0">0 years (fresher)</option>
              <option value="1">Up to 1 year</option>
              <option value="2">Up to 2 years</option>
              <option value="5">Up to 5 years</option>
            </select>
            <input
              type="number"
              min="0"
              step="0.5"
              placeholder="Min salary (LPA)"
              value={salaryMinLpa}
              onChange={(e) => setSalaryMinLpa(e.target.value)}
              className="input-field text-xs py-1.5 bg-base-950/80 border-base-700/80 rounded-xl"
              title="Only listings that state a salary are shown when this is set"
            />
            <select
              value={datePosted}
              onChange={(e) => setDatePosted(e.target.value)}
              className="bg-base-950 border border-base-700 text-white/80 rounded-xl px-2.5 py-1.5 text-xs outline-none"
            >
              {DATE_POSTED.map((d) => (
                <option key={d.value} value={d.value}>{d.label}</option>
              ))}
            </select>
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
              Try adjusting your search terms or removing filters. Listings refresh automatically every two hours
              {syncInfo?.next_scheduled_sync ? ` (next refresh ${relativeTime(syncInfo.next_scheduled_sync)})` : ''}.
            </p>
            <button
              onClick={resetFilters}
              className="btn-ghost text-xs py-1.5 px-3 mx-auto"
            >
              Reset All Filters
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {jobs.map((job) => {
              const isSaved = savedJobIds.has(job.id);
              const isApplied = Boolean(appliedJobsMap[job.id] || job.is_applied);
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
                        {/* Verification / freshness (from real timestamps) */}
                        {(() => {
                          const v = VERIFICATION_BADGE[job.freshness?.verification_status] ||
                            (job.is_sample ? VERIFICATION_BADGE.sample : VERIFICATION_BADGE.unverified);
                          return (
                            <span
                              className={`text-[10px] font-mono px-2 py-0.5 rounded-md border flex items-center gap-1 ${v.cls}`}
                              title={job.freshness?.last_checked_at
                                ? `Last confirmed by ${job.source}: ${new Date(job.freshness.last_checked_at).toLocaleString()}`
                                : 'Not confirmed by the source'}
                            >
                              {job.freshness?.verification_status === 'verified'
                                ? <TbShieldCheck className="w-3 h-3" />
                                : <TbAlertTriangle className="w-3 h-3" />}
                              {v.label}
                            </span>
                          );
                        })()}
                        {job.freshness?.is_recent && (
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-sky-500/15 text-sky-300 border border-sky-500/30">
                            Recently posted
                          </span>
                        )}

                        <span className="text-[10px] px-2 py-0.5 rounded-md bg-base-800 text-white/70 border border-base-700">
                          {job.job_type}
                        </span>

                        {/* Applied Status Badge */}
                        {isApplied && (
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-semibold flex items-center space-x-1">
                            <TbCheck className="w-3 h-3" />
                            <span>Applied</span>
                          </span>
                        )}

                        {/* Regional Location Badge */}
                        {job.region_badge === 'India' && (
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-amber-500/15 text-amber-300 border border-amber-500/30 font-medium">
                            🇮🇳 India
                          </span>
                        )}
                        {job.region_badge === 'Asia' && (
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-sky-500/15 text-sky-300 border border-sky-500/30 font-medium">
                            🌏 Asia
                          </span>
                        )}
                        {job.region_badge === 'Remote' && (
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-teal-500/15 text-teal-300 border border-teal-500/30 font-medium">
                            🌐 Remote
                          </span>
                        )}

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
                        {job.work_arrangement && job.work_arrangement !== 'Unspecified' && (
                          <span>{job.work_arrangement}</span>
                        )}
                      </div>
                      <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[11px] text-white/40 mt-1">
                        <span>{job.freshness?.posted_label}</span>
                        <span>Source: {job.source}</span>
                        {job.experience_level && job.experience_level !== 'Not specified' && (
                          <span>{job.experience_level}</span>
                        )}
                        {formatSalary(job.salary) && (
                          <span className="text-emerald-300/80" title={job.salary.label}>
                            {formatSalary(job.salary)}
                            {job.salary.is_estimated ? ' (estimated by provider)' : ''}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Description preview */}
                    <p className="text-xs text-white/60 line-clamp-2 leading-relaxed">
                      {cleanDescription(job.description)}
                    </p>

                    {/* Skills Chips */}
                    <div className="space-y-1.5 pt-1">
                      {(job.required_skills || []).length === 0 && (
                        <p className="text-[11px] text-white/40 italic">
                          No skills listed in the source summary — read the full posting.
                        </p>
                      )}
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
                      className="btn-primary text-xs py-1.5 px-2.5 flex items-center space-x-1 shadow-glow"
                      title="Explain deterministic match fit"
                    >
                      <TbSparkles className="w-3.5 h-3.5" />
                      <span>{score === null ? 'Fit: n/a' : score !== undefined ? `${score}% Fit` : 'Match'}</span>
                    </button>

                    {/* Apply Button */}
                    {isApplied ? (
                      <div className="flex items-center space-x-1">
                        <span className="text-xs px-2.5 py-1.5 rounded-xl bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 font-medium flex items-center space-x-1">
                          <TbCheck className="w-3.5 h-3.5" />
                          <span>Applied</span>
                        </span>
                        <button
                          onClick={() => handleWithdrawApply(job.id)}
                          className="text-[10px] text-white/40 hover:text-rose-400 px-1 py-0.5"
                          title="Withdraw application"
                        >
                          Withdraw
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => handleOpenApply(job)}
                        className="bg-accent-500 hover:bg-accent-400 text-base-950 font-semibold text-xs py-1.5 px-3 rounded-xl flex items-center space-x-1.5 transition-all shadow-glow hover:scale-[1.02]"
                        title="Apply for this role"
                      >
                        <TbSend className="w-3.5 h-3.5" />
                        <span>Apply Role</span>
                      </button>
                    )}

                    <button
                      onClick={() =>
                        navigate(
                          `/interview-prep?job_id=${job.id}&role=${encodeURIComponent(job.title)}`
                        )
                      }
                      className="btn-ghost text-xs py-1.5 px-2.5 flex items-center space-x-1"
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
                        title={`View the original posting on ${job.source}`}
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

        {/* Pagination */}
        {!loading && !showSavedOnly && !showAppliedOnly && totalPages > 1 && (
          <div className="flex items-center justify-center gap-3 text-xs text-white/60">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="btn-ghost text-xs py-1.5 px-3 disabled:opacity-30"
            >
              Previous
            </button>
            <span className="font-mono">Page {page} of {totalPages}</span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="btn-ghost text-xs py-1.5 px-3 disabled:opacity-30"
            >
              Next
            </button>
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
                  <p className="text-xs text-white/50">Comparing the posting with your verified skills...</p>
                </div>
              ) : matchData ? (
                <div className="space-y-5">
                  {/* Total Deterministic Score Card */}
                  <div className="bg-base-950/80 p-4 rounded-2xl border border-base-800 flex items-center justify-between">
                    <div>
                      <div className="text-xs text-white/40">Skill Fit Score</div>
                      {matchData.match_score === null || matchData.match_score === undefined ? (
                        <div className="font-heading text-lg font-bold text-white/70">Not enough data</div>
                      ) : (
                        <div className="font-heading text-3xl font-bold text-white flex items-baseline space-x-1.5">
                          <span className={matchData.match_score >= 70 ? 'text-emerald-400' : matchData.match_score >= 45 ? 'text-amber-400' : 'text-rose-400'}>
                            {matchData.match_score}%
                          </span>
                          <span className="text-xs text-white/40">{matchData.scoring_breakdown?.fit_label}</span>
                        </div>
                      )}
                      <p className="text-[11px] text-white/50 mt-1 max-w-xs">
                        Rule-based: required skills count 3× preferred ones, quiz-verified skills count more than
                        resume claims. It is not a prediction of hiring outcomes.
                      </p>
                    </div>

                    <div className="flex items-center space-x-2">
                      {appliedJobsMap[matchModalJob.id] ? (
                        <span className="text-xs px-3 py-2 rounded-xl bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 flex items-center space-x-1.5 font-medium">
                          <TbCheck className="w-4 h-4" />
                          <span>Applied</span>
                        </span>
                      ) : (
                        <button
                          onClick={() => {
                            const j = matchModalJob;
                            setMatchModalJob(null);
                            handleOpenApply(j);
                          }}
                          className="bg-accent-500 hover:bg-accent-400 text-base-950 font-semibold text-xs py-2 px-3.5 rounded-xl flex items-center space-x-1.5 shadow-glow"
                        >
                          <TbSend className="w-4 h-4" />
                          <span>Apply for Role</span>
                        </button>
                      )}

                      <button
                        onClick={() => {
                          setMatchModalJob(null);
                          navigate(`/interview-prep?job_id=${matchModalJob.id}&role=${encodeURIComponent(matchModalJob.title)}`);
                        }}
                        className="btn-ghost text-xs py-2 px-3.5 flex items-center space-x-1.5"
                      >
                        <TbMicrophone className="w-4 h-4 text-teal-300" />
                        <span>Practice</span>
                      </button>
                    </div>
                  </div>

                  {/* Why this score */}
                  {Array.isArray(matchData.match_reasons) && matchData.match_reasons.length > 0 && (
                    <div className="bg-base-950/60 p-3.5 rounded-2xl border border-base-800 space-y-1">
                      <h4 className="text-xs font-semibold text-white/80">Why this score</h4>
                      <ul className="list-disc list-inside text-[11px] text-white/60 space-y-0.5">
                        {matchData.match_reasons.map((r, i) => <li key={i}>{r}</li>)}
                      </ul>
                    </div>
                  )}

                  {/* Score components */}
                  <div className="space-y-3">
                    <h4 className="text-xs font-semibold text-white/80 uppercase tracking-wider font-mono">
                      Score Components
                    </h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                      {[
                        ['Required skills covered', matchData.scoring_breakdown?.mandatory_skills_score, 'of required skills you have'],
                        ['Preferred skills covered', matchData.scoring_breakdown?.preferred_skills_score, 'of preferred skills you have'],
                        ['Experience fit', matchData.scoring_breakdown?.experience_eligibility_score, 'multiplier on the score'],
                        ['Location / work-mode fit', matchData.scoring_breakdown?.location_fit_score, 'multiplier on the score']
                      ].map(([label, value, hint]) => (
                        <div key={label} className="bg-base-950/60 p-3 rounded-xl border border-base-800 space-y-1.5">
                          <div className="flex justify-between items-center">
                            <span className="text-white/70 font-medium">{label}</span>
                            <span className="text-accent-300 font-mono font-bold">
                              {value ?? 0}%
                            </span>
                          </div>
                          <ProgressBar progress={value || 0} size="sm" />
                          <p className="text-[10px] text-white/40">{hint}</p>
                        </div>
                      ))}
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
                        Related skills you already have make these requirements quicker to learn (partial credit only):
                      </p>                      <div className="space-y-1">
                        {(matchData.transferable_bridges || []).map((bridge, bIdx) => {
                          const coeff = bridge.transfer_coefficient ?? 0.25;
                          return (
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
                                {(coeff * 100).toFixed(0)}% credit
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Matched vs Missing Skills breakdown */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                    {/* Satisfied Skills */}
                    {(() => {
                      const satisfiedList = Array.isArray(matchData.matched_skills)
                        ? matchData.matched_skills
                        : [
                            ...(matchData.matched_skills?.verified || []).map((s) => ({ skill: s, is_verified: true })),
                            ...(matchData.matched_skills?.unverified || []).map((s) => ({ skill: s, is_verified: false })),
                            ...(matchData.matched_skills?.preferred || []).map((s) => ({ skill: s, is_verified: true }))
                          ];

                      return (
                        <div className="space-y-2">
                          <h5 className="font-semibold text-emerald-400 flex items-center space-x-1">
                            <TbCheck className="w-4 h-4" />
                            <span>Matched Skills ({satisfiedList.length})</span>
                          </h5>
                          <div className="space-y-1">
                            {satisfiedList.length === 0 ? (
                              <p className="text-[11px] text-white/40 italic">No direct matches identified yet.</p>
                            ) : (
                              satisfiedList.map((ms, idx) => (
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
                              ))
                            )}
                          </div>
                        </div>
                      );
                    })()}

                    {/* Missing Skills with Curated Resources */}
                    {(() => {
                      const missingList = Array.isArray(matchData.missing_mandatory_skills)
                        ? matchData.missing_mandatory_skills
                        : (matchData.missing_skills?.mandatory || []);

                      return (
                        <div className="space-y-2">
                          <h5 className="font-semibold text-rose-400 flex items-center space-x-1">
                            <TbX className="w-4 h-4" />
                            <span>Missing Skill Gaps ({missingList.length})</span>
                          </h5>
                          <div className="space-y-1.5">
                            {missingList.length === 0 ? (
                              <p className="text-[11px] text-emerald-400/80">All mandatory requirements satisfied!</p>
                            ) : (
                              missingList.map((skill, idx) => {
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
                                          className="text-white/70 hover:text-white flex items-center space-x-1"
                                        >
                                          <TbBrandGithub className="w-3 h-3" />
                                          <span>Project</span>
                                        </a>
                                      )}
                                    </div>
                                  </div>
                                );
                              })
                            )}
                          </div>
                        </div>
                      );
                    })()}
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
                    {(comparisonData.jobs || []).map((ev) => {
                      const cJob = {
                        job_id: ev.job?.id,
                        title: ev.job?.title,
                        company: ev.job?.company,
                        match_score: ev.match_score,
                        matched_skills: [
                          ...(ev.matched_skills?.verified || []),
                          ...(ev.matched_skills?.unverified || []),
                          ...(ev.matched_skills?.preferred || [])
                        ],
                        missing_mandatory: ev.missing_skills?.mandatory || []
                      };
                      return (
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
                            {cJob.match_score == null ? 'n/a' : `${cJob.match_score}%`}
                          </div>
                        </div>

                        <div className="space-y-1.5 text-xs">
                          <div className="text-[11px] font-semibold text-emerald-400">
                            Matched ({cJob.matched_skills.length})
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
                      );
                    })}
                  </div>
                  {comparisonData.recommendation && (
                    <p className="text-xs text-white/60">{comparisonData.recommendation}</p>
                  )}
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
                    {[
                      ['Active listings', telemetryData.listings_by_status?.active, 'text-white'],
                      ['Not re-confirmed recently', telemetryData.listings_by_status?.stale, 'text-amber-400'],
                      ['Expired / archived', telemetryData.listings_by_status?.expired, 'text-rose-300'],
                      ['Cross-source duplicates hidden', telemetryData.duplicates_flagged, 'text-accent-300']
                    ].map(([label, value, cls]) => (
                      <div key={label} className="bg-base-950/80 p-3.5 rounded-xl border border-base-800">
                        <div className="text-white/40 text-[11px]">{label}</div>
                        <div className={`font-heading text-2xl font-bold ${cls}`}>{value ?? 0}</div>
                      </div>
                    ))}
                  </div>

                  <div className="text-[11px] text-white/50 space-y-0.5">
                    <p>Last successful refresh: {telemetryData.last_successful_sync
                      ? new Date(telemetryData.last_successful_sync).toLocaleString() : 'never'}</p>
                    <p>Next scheduled refresh: {telemetryData.next_scheduled_sync
                      ? new Date(telemetryData.next_scheduled_sync).toLocaleString() : '—'}</p>
                    {telemetryData.scheduler && (
                      <p className={telemetryData.scheduler.healthy ? 'text-emerald-300/80' : 'text-amber-300'}>
                        Automatic refresh: {telemetryData.scheduler.healthy
                          ? 'running'
                          : `not running${telemetryData.scheduler.overdue_minutes > 0
                            ? ` (overdue by ${Math.floor(telemetryData.scheduler.overdue_minutes / 60)} h ${telemetryData.scheduler.overdue_minutes % 60} min)`
                            : ''} - listings may be out of date`}
                      </p>
                    )}
                    <p>Listings without a stated posting date: {telemetryData.listings_without_posting_date ?? 0}</p>
                    <p>Listings without recognisable skills: {telemetryData.listings_without_skills ?? 0}</p>
                  </div>

                  <div className="space-y-2 pt-2">
                    <h5 className="font-semibold text-white/70">Job Sources</h5>
                    <div className="space-y-1.5">
                      {(telemetryData.adapters || []).filter((a) => !a.is_sample_source).map((a) => {
                        const h = a.health || {};
                        const last = h.last_result;
                        return (
                          <div
                            key={a.name}
                            className="flex justify-between items-center bg-base-950/60 px-3 py-2 rounded-xl border border-base-800"
                          >
                            <span className="font-mono text-white/80">{a.name}</span>
                            <span className={`font-mono text-[11px] ${
                              !h.configured ? 'text-white/40'
                                : last?.status === 'ok' ? 'text-emerald-300' : 'text-amber-300'
                            }`}>
                              {!h.configured
                                ? 'Not configured'
                                : last ? `${last.status} · ${last.accepted ?? 0} jobs last run` : 'Configured, not run yet'}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        )}
        {/* Apply for Role Modal */}
        {applyModalJob && (
          <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="surface max-w-xl w-full rounded-3xl border border-accent-400/40 p-6 space-y-5 animate-scale-in max-h-[90vh] overflow-y-auto">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-accent-500/20 text-accent-300 border border-accent-400/30 font-semibold">
                      Application Tracker
                    </span>
                    {applyModalJob.region_badge === 'India' && (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30 font-medium">
                        🇮🇳 India
                      </span>
                    )}
                    {applyModalJob.region_badge === 'Asia' && (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-500/15 text-sky-300 border border-sky-500/30 font-medium">
                        🌏 Asia
                      </span>
                    )}
                  </div>
                  <h2 className="font-heading text-lg font-bold text-white mt-1.5">
                    Apply for {applyModalJob.title}
                  </h2>
                  <p className="text-xs text-white/50">
                    {applyModalJob.company} · {applyModalJob.location}
                  </p>
                </div>
                <button
                  onClick={() => setApplyModalJob(null)}
                  className="p-1.5 rounded-lg text-white/40 hover:text-white hover:bg-white/10"
                >
                  <TbX className="w-4 h-4" />
                </button>
              </div>

              {/* Honest notice: SkillBridge does not submit applications to employers */}
              <div className="bg-amber-500/10 p-4 rounded-2xl border border-amber-500/30 space-y-2">
                <div className="flex items-center gap-1.5 text-xs text-amber-300 font-semibold">
                  <TbAlertTriangle className="w-4 h-4" />
                  <span>This does not send anything to the employer</span>
                </div>
                <p className="text-[11px] text-white/60 leading-relaxed">
                  SkillBridge records the application in your personal tracker. To actually apply, open the
                  original posting on {applyModalJob.source} and follow the employer's application process.
                </p>
                {applyModalJob.application_url && (
                  <a
                    href={applyModalJob.application_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-white underline hover:text-accent-300"
                  >
                    <span>Open the original posting</span>
                    <TbExternalLink className="w-3.5 h-3.5" />
                  </a>
                )}
              </div>

              <form onSubmit={handleSubmitApply} className="space-y-4 text-xs">
                {/* Contact Email */}
                <div>
                  <label className="block text-white/70 font-medium mb-1">
                    Contact Email <span className="text-rose-400">*</span>
                  </label>
                  <input
                    type="email"
                    required
                    placeholder="your.email@example.com"
                    value={applyForm.contact_email}
                    onChange={(e) =>
                      setApplyForm({ ...applyForm, contact_email: e.target.value })
                    }
                    className="input-field text-xs py-2 w-full bg-base-950/80 border-base-700/80 rounded-xl"
                  />
                </div>

                {/* Portfolio / GitHub URL */}
                <div>
                  <label className="block text-white/70 font-medium mb-1">
                    Portfolio / GitHub URL (Optional)
                  </label>
                  <input
                    type="url"
                    placeholder="https://github.com/yourusername"
                    value={applyForm.portfolio_url}
                    onChange={(e) =>
                      setApplyForm({ ...applyForm, portfolio_url: e.target.value })
                    }
                    className="input-field text-xs py-2 w-full bg-base-950/80 border-base-700/80 rounded-xl"
                  />
                </div>

                {/* Candidate Cover Note */}
                <div>
                  <label className="block text-white/70 font-medium mb-1">
                    Candidate Cover Pitch / Note
                  </label>
                  <textarea
                    rows={4}
                    value={applyForm.cover_note}
                    onChange={(e) =>
                      setApplyForm({ ...applyForm, cover_note: e.target.value })
                    }
                    className="input-field text-xs py-2 w-full bg-base-950/80 border-base-700/80 rounded-xl resize-none"
                    placeholder="Highlight your relevant verified skills and why you're a great fit..."
                  />
                </div>

                {/* Action Buttons */}
                <div className="flex items-center justify-end space-x-2 pt-2 border-t border-base-800">
                  <button
                    type="button"
                    onClick={() => setApplyModalJob(null)}
                    className="btn-ghost text-xs py-2 px-3.5"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={applying}
                    className="btn-primary text-xs py-2 px-4 flex items-center space-x-1.5 shadow-glow"
                  >
                    <TbSend className="w-3.5 h-3.5" />
                    <span>{applying ? 'Saving...' : 'Record in My Tracker'}</span>
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {alertsPanelOpen && (
          <JobAlertsPanel
            onClose={() => {
              setAlertsPanelOpen(false);
              loadUnreadAlerts();
              loadJobs();
            }}
            onOpenJob={(job) => {
              setAlertsPanelOpen(false);
              handleOpenMatch(job);
            }}
          />
        )}
      </div>
    </AppLayout>
  );
}
