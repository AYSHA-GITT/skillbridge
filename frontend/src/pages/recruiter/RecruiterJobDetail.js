import React, { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { TbArrowLeft, TbUsers, TbUserSearch } from 'react-icons/tb';
import RecruiterLayout, { useRecruiter, VerificationGate } from '../../components/RecruiterLayout';
import recruiterService, { errorText } from '../../services/recruiterService';
import AlertBanner from '../../components/AlertBanner';
import { FitPill, ReportSummaryLine } from '../../components/MatchReport';
import { StatusBadge, displaySkill, fmtDate } from '../../components/PassportBits';
import { JobStatus } from './RecruiterJobs';

export function CandidateCard({ c, jobId, extra }) {
  return (
    <div className="glass p-4 space-y-2">
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
        <div className="min-w-0">
          <Link to={`/recruiter/candidates/${c.candidate_ref}${jobId ? `?job_id=${jobId}` : ''}`}
            className="font-semibold text-white hover:text-indigo-300">{c.name}</Link>
          {c.headline && <div className="text-xs text-indigo-200/80">{c.headline}</div>}
          <div className="text-[11px] text-white/45">
            {[c.education, `${c.verified_count}/${c.skill_count} skills verified`,
              c.project_count ? `${c.project_count} project${c.project_count === 1 ? '' : 's'}` : null,
              c.readiness?.score != null ? `readiness ${c.readiness.score}% (${c.readiness.label})` : null]
              .filter(Boolean).join(' · ')}
          </div>
        </div>
        <div className="flex items-center gap-2 flex-wrap">{c.report && <FitPill report={c.report} />}{extra}</div>
      </div>
      {c.report ? <ReportSummaryLine report={c.report} /> : (
        <div className="flex flex-wrap gap-1">
          {c.top_skills.map((s) => <StatusBadge key={s.skill_name} status={s.status} label={`${displaySkill(s.skill_name)} · ${s.status_label}`} />)}
        </div>
      )}
      {!c.skills_shared && <p className="text-[11px] text-white/40 italic">This candidate did not share their skills section.</p>}
    </div>
  );
}

function Content() {
  const { id } = useParams();
  const { me } = useRecruiter();
  const [tab, setTab] = useState('applicants');
  const [data, setData] = useState(null);
  const [matches, setMatches] = useState(null);
  const [alert, setAlert] = useState(null);

  const loadApplicants = useCallback(() => recruiterService.applicants(id).then(setData)
    .catch((e) => setAlert({ type: 'error', message: errorText(e, 'Job not found.') })), [id]);
  useEffect(() => { loadApplicants(); }, [loadApplicants]);
  useEffect(() => {
    if (tab === 'matches' && matches === null && me.can_search_candidates) {
      recruiterService.jobMatches(id).then(setMatches).catch((e) => setAlert({ type: 'error', message: errorText(e) }));
    }
  }, [tab, matches, id, me]);

  const stage = async (appId, value) => {
    try {
      const r = await recruiterService.changeStage(appId, value);
      setAlert({ type: 'success', message: r.message });
      loadApplicants();
    } catch (e) {
      setAlert({ type: 'error', message: errorText(e) });
    }
  };

  if (!data) return alert ? <AlertBanner type={alert.type} message={alert.message} /> : <p className="text-sm text-white/40">Loading…</p>;
  const job = data.job;

  return (
    <div className="space-y-5">
      <Link to="/recruiter/jobs" className="text-xs text-white/50 hover:text-white flex items-center gap-1"><TbArrowLeft /> All jobs</Link>
      <div className="glass p-5 space-y-2">
        <div className="flex items-center gap-2 flex-wrap">
          <h1 className="font-heading text-xl font-bold text-white">{job.title}</h1>
          <JobStatus status={job.status} />
        </div>
        <p className="text-xs text-white/50">{job.location} · {job.work_arrangement} · {job.job_type}
          {job.deadline && ` · apply by ${fmtDate(job.deadline)}`}</p>
        <div className="flex flex-wrap gap-1">
          {job.required_skills.map((s) => <span key={s} className="text-[10px] px-2 py-0.5 rounded-md bg-base-950 text-white/70 border border-base-800">{displaySkill(s)}</span>)}
          {job.preferred_skills.map((s) => <span key={s} className="text-[10px] px-2 py-0.5 rounded-md text-white/40 border border-dashed border-base-700">{displaySkill(s)} (preferred)</span>)}
        </div>
      </div>
      {alert && <AlertBanner type={alert.type} message={alert.message} onClose={() => setAlert(null)} />}

      <div className="flex gap-2">
        {[['applicants', `Applicants (${data.applicants.length})`, TbUsers], ['matches', 'Matching candidates', TbUserSearch]].map(([k, label, Icon]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`text-xs px-3 py-2 rounded-xl border flex items-center gap-1.5 ${tab === k ? 'border-indigo-400/50 text-indigo-200 bg-indigo-500/10' : 'border-base-700 text-white/50'}`}>
            <Icon className="w-4 h-4" /> {label}
          </button>
        ))}
      </div>

      {tab === 'applicants' && (
        data.applicants.length === 0 ? <div className="glass p-8 text-center text-sm text-white/50">No applications yet.</div> : (
          <div className="space-y-3">
            <p className="text-[11px] text-white/40">{data.ranked_by}. Open a candidate for the full evidence report.</p>
            {data.applicants.map((c) => (
              <CandidateCard key={c.application_id} c={c} jobId={job.id} extra={
                <select value={c.stage} onChange={(e) => stage(c.application_id, e.target.value)}
                  className="input-field text-[11px] py-1.5 px-2 w-auto" title="Hiring stage (the candidate sees stage changes)">
                  {me.pipeline_stages.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
                </select>
              } />
            ))}
          </div>
        )
      )}

      {tab === 'matches' && (
        <VerificationGate me={me} feature="Candidate matching">
          {matches === null ? <p className="text-sm text-white/40">Ranking candidates…</p> : (
            <div className="space-y-3">
              <p className="text-[11px] text-white/40">
                {matches.total} candidate{matches.total === 1 ? '' : 's'} who chose to be visible to verified employers. {matches.ranked_by}.
              </p>
              {matches.candidates.length === 0 && <div className="glass p-8 text-center text-sm text-white/50">No visible candidates yet.</div>}
              {matches.candidates.map((c) => <CandidateCard key={c.candidate_ref} c={c} jobId={job.id} />)}
            </div>
          )}
        </VerificationGate>
      )}
    </div>
  );
}

export default function RecruiterJobDetail() {
  return <RecruiterLayout><Content /></RecruiterLayout>;
}
