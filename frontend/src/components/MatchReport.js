import React, { useState } from 'react';
import { TbCheck, TbX, TbAlertTriangle, TbInfoCircle, TbChevronDown, TbChevronUp } from 'react-icons/tb';
import { StatusBadge, KIND_LABELS, REVIEW_LABELS, displaySkill } from './PassportBits';

export function FitPill({ report, size = 'sm' }) {
  if (!report) return null;
  const fit = report.skill_fit_score;
  const cls = fit == null ? 'bg-white/5 text-white/50 border-white/15'
    : fit >= 70 ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40'
      : fit >= 45 ? 'bg-sky-500/15 text-sky-300 border-sky-500/40'
        : fit >= 25 ? 'bg-amber-500/15 text-amber-300 border-amber-500/40'
          : 'bg-rose-500/15 text-rose-300 border-rose-500/40';
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border font-semibold whitespace-nowrap ${cls} ${size === 'lg' ? 'text-sm px-3 py-1' : 'text-[10px] px-2 py-0.5'}`}
      title={report.method}>
      {fit == null ? 'Fit: n/a' : `${fit}% skill fit`} · {report.fit_label}
    </span>
  );
}

/** One-line summary that never hides gaps behind the percentage. */
export function ReportSummaryLine({ report }) {
  if (!report) return null;
  const s = report.summary;
  return (
    <div className="text-[11px] text-white/55 flex flex-wrap gap-x-3 gap-y-0.5">
      <span>Required: <b className="text-white/80">{s.required_matched}/{s.required_total}</b> shown, <b className="text-emerald-300">{s.required_verified}</b> verified</span>
      {s.preferred_total > 0 && <span>Preferred: {s.preferred_matched}/{s.preferred_total}</span>}
      {s.missing_mandatory.length > 0 && (
        <span className="text-rose-300">Missing: {s.missing_mandatory.map(displaySkill).join(', ')}</span>
      )}
      {s.needs_verification.length > 0 && (
        <span className="text-amber-300">Unverified: {s.needs_verification.map(displaySkill).join(', ')}</span>
      )}
    </div>
  );
}

function SkillRow({ r }) {
  return (
    <tr className="align-top">
      <td className="py-2 pr-3">
        <div className="flex items-center gap-1.5 text-white font-semibold">
          {r.matched ? (r.verified ? <TbCheck className="w-4 h-4 text-emerald-400" /> : <TbAlertTriangle className="w-4 h-4 text-amber-400" />)
            : <TbX className="w-4 h-4 text-rose-400" />}
          {displaySkill(r.skill)}
        </div>
        <div className="text-[10px] text-white/35 ml-5">{r.kind}</div>
      </td>
      <td className="py-2 pr-3">
        {r.matched ? <StatusBadge status={r.candidate_status} label={r.status_label} /> :
          <span className="text-[11px] text-rose-300">{r.status_label}</span>}
      </td>
      <td className="py-2 pr-3 text-white/70 font-mono">{r.credit.toFixed(2)}</td>
      <td className="py-2 text-white/60 text-[11px] space-y-0.5">
        {r.evidence.length ? r.evidence.map((e, i) => <div key={i}>{e}</div>) : '—'}
      </td>
    </tr>
  );
}

/** Full explainable candidate-job compatibility report. */
export default function MatchReport({ report, defaultOpen = true }) {
  const [showMethod, setShowMethod] = useState(false);
  const [open, setOpen] = useState(defaultOpen);
  if (!report) return null;
  const rows = [...report.required, ...report.preferred];
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <FitPill report={report} size="lg" />
          {report.job?.title && <span className="text-xs text-white/50">for {report.job.title}</span>}
        </div>
        <button type="button" onClick={() => setOpen(!open)} className="text-[11px] text-white/50 hover:text-white flex items-center gap-1">
          {open ? <>Hide details <TbChevronUp /></> : <>Show details <TbChevronDown /></>}
        </button>
      </div>
      <ReportSummaryLine report={report} />

      {report.limitations.length > 0 && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-3 space-y-1">
          {report.limitations.map((l, i) => (
            <p key={i} className="text-[11px] text-amber-200/90 flex gap-1.5"><TbAlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />{l}</p>
          ))}
        </div>
      )}

      {open && (
        <>
          {rows.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-white/35">
                    <th className="py-1.5 pr-3 font-medium">Job skill</th>
                    <th className="py-1.5 pr-3 font-medium">Candidate status</th>
                    <th className="py-1.5 pr-3 font-medium" title="Credit used in the skill fit (0-1)">Credit</th>
                    <th className="py-1.5 font-medium">Evidence behind it</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-base-700/60">
                  {rows.map((r) => <SkillRow key={`${r.kind}-${r.skill}`} r={r} />)}
                </tbody>
              </table>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="surface p-3 space-y-1.5">
              <h4 className="text-[11px] uppercase tracking-wider text-white/40 font-semibold">Relevant projects & experience</h4>
              {report.relevant_projects.length === 0 ? <p className="text-[11px] text-white/40 italic">None shared that use these skills.</p> :
                report.relevant_projects.map((p, i) => (
                  <div key={i} className="text-[11px] text-white/70">
                    <b className="text-white">{KIND_LABELS[p.kind]}: {p.title}</b>
                    {p.organization && ` · ${p.organization}`}
                    <span className="text-white/40"> — {p.matching_skills.map(displaySkill).join(', ')} · {REVIEW_LABELS[p.review_status]}</span>
                  </div>
                ))}
            </div>
            <div className="surface p-3 space-y-1.5">
              <h4 className="text-[11px] uppercase tracking-wider text-white/40 font-semibold">Relevant assessments</h4>
              {report.relevant_assessments.length === 0 ? <p className="text-[11px] text-white/40 italic">None shared for these skills.</p> :
                report.relevant_assessments.map((a, i) => (
                  <div key={i} className="text-[11px] text-white/70">
                    {displaySkill(a.skill_name)}: <b className={a.passed ? 'text-emerald-300' : 'text-amber-300'}>{Math.round(a.score_percent)}%</b> ({a.correct}/{a.total}) {a.passed ? 'passed' : 'below pass mark'}
                  </div>
                ))}
            </div>
            <div className="surface p-3 text-[11px] text-white/60 space-y-1">
              <h4 className="uppercase tracking-wider text-white/40 font-semibold">Experience</h4>
              <div>Job requires: <span className="text-white/80">{report.experience.job_requires}</span></div>
              <div>Candidate: <span className="text-white/80">{report.experience.candidate_entries == null ? 'Not shared' : `${report.experience.candidate_entries} experience entr${report.experience.candidate_entries === 1 ? 'y' : 'ies'} shared`}</span></div>
              <div className="text-white/35">{report.experience.note}</div>
            </div>
            <div className="surface p-3 text-[11px] text-white/60 space-y-1">
              <h4 className="uppercase tracking-wider text-white/40 font-semibold">Education</h4>
              <div>Job requires: <span className="text-white/80">{report.education.job_requires}</span></div>
              <div>Candidate: <span className="text-white/80">{report.education.candidate == null ? 'Not shared' : report.education.candidate || 'Not stated'}</span></div>
              <div className="text-white/35">{report.education.note}</div>
            </div>
          </div>

          <button type="button" onClick={() => setShowMethod(!showMethod)} className="text-[11px] text-indigo-300 hover:text-indigo-200 flex items-center gap-1">
            <TbInfoCircle className="w-3.5 h-3.5" /> How is this calculated?
          </button>
          {showMethod && (
            <p className="text-[11px] text-white/50 leading-relaxed">{report.method} {report.disclaimer}</p>
          )}
        </>
      )}
    </div>
  );
}
