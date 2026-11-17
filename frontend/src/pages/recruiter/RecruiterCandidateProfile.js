import React, { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { TbArrowLeft, TbShieldLock, TbNote, TbListCheck, TbMail, TbSend, TbTrash } from 'react-icons/tb';
import RecruiterLayout, { useRecruiter } from '../../components/RecruiterLayout';
import recruiterService, { errorText } from '../../services/recruiterService';
import AlertBanner from '../../components/AlertBanner';
import MatchReport from '../../components/MatchReport';
import {
  StatusBadge, ReviewBadge, SafeLink, GROUP_ORDER, KIND_LABELS, displaySkill, fmtDate, fmtDateTime
} from '../../components/PassportBits';

const EV_SECTIONS = { projects: 'Projects', experience: 'Experience', certifications: 'Certifications', practical_challenges: 'Practical challenges' };

function Section({ title, children, right }) {
  return (
    <section className="glass p-5 space-y-3">
      <div className="flex items-center justify-between gap-2">
        <h2 className="font-heading text-sm font-bold text-white">{title}</h2>{right}
      </div>
      {children}
    </section>
  );
}

function Passport({ p }) {
  const skills = p.skills || [];
  return (
    <>
      {p.sections.includes('skills') && (
        <Section title={`Skills (${skills.filter((s) => s.status === 'verified').length} verified of ${skills.length} shown)`}>
          {p.skill_filter !== 'all' && <p className="text-[11px] text-white/40">The candidate shares {p.skill_filter === 'verified' ? 'only verified skills' : 'only skills with evidence or an assessment'}.</p>}
          {GROUP_ORDER.map((g) => {
            const rows = skills.filter((s) => s.group === g);
            if (!rows.length) return null;
            return (
              <div key={g}>
                <h3 className="text-[11px] uppercase tracking-wider text-white/40 font-semibold pt-1 pb-1.5">{p.skill_groups[g]}</h3>
                <div className="flex flex-wrap gap-1.5">
                  {rows.map((s) => (
                    <StatusBadge key={s.skill_name} status={s.status} title={p.status_descriptions[s.status]}
                      label={`${displaySkill(s.skill_name)} · ${s.status_label}${s.assessment ? ` · ${Math.round(s.assessment.score_percent)}%` : ''}`} />
                  ))}
                </div>
              </div>
            );
          })}
          <p className="text-[11px] text-white/35">Verified = passed a SkillBridge assessment (pass mark {p.pass_threshold}%) or evidence accepted by a reviewer. Resume mentions are never treated as verification.</p>
        </Section>
      )}
      {Object.entries(EV_SECTIONS).map(([key, title]) => p.sections.includes(key) && (
        <Section key={key} title={title}>
          {(p[key] || []).length === 0 ? <p className="text-xs text-white/40 italic">None added.</p> : p[key].map((e, i) => (
            <div key={i} className="surface p-3 space-y-1">
              <div className="flex justify-between gap-2">
                <div className="text-sm font-semibold text-white">{e.title}{e.organization && <span className="text-white/50 font-normal"> · {e.organization}</span>}</div>
                <ReviewBadge status={e.review_status} />
              </div>
              <div className="text-[11px] text-white/40">{KIND_LABELS[e.kind]} {[e.start_date, e.end_date].filter(Boolean).join(' – ')}</div>
              {e.description && <p className="text-xs text-white/60 whitespace-pre-line">{e.description}</p>}
              {e.url && <SafeLink href={e.url} className="text-xs text-indigo-300">{e.url}</SafeLink>}
              {e.skills.length > 0 && <div className="text-[11px] text-white/50">Skills: {e.skills.map(displaySkill).join(', ')}</div>}
            </div>
          ))}
        </Section>
      ))}
      {p.sections.includes('assessments') && (p.assessments || []).length > 0 && (
        <Section title="Assessment results">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
            {p.assessments.map((a, i) => (
              <div key={i} className="surface p-2.5 flex justify-between">
                <span className="text-white">{displaySkill(a.skill_name)}</span>
                <span className={a.passed ? 'text-emerald-300' : 'text-amber-300'}>{Math.round(a.score_percent)}% ({a.correct}/{a.total}) · {fmtDate(a.taken_at)}</span>
              </div>
            ))}
          </div>
        </Section>
      )}
      {p.career_interests && (
        <Section title="Career interests">
          <dl className="text-xs grid grid-cols-1 sm:grid-cols-2 gap-2">
            {[['Target career', p.career_interests.target_career], ['Preferred roles', p.career_interests.preferred_roles?.join(', ')],
              ['Locations', p.career_interests.preferred_locations?.join(', ')], ['Work modes', p.career_interests.work_modes?.join(', ')],
              ['Job types', p.career_interests.job_types?.join(', ')]].filter(([, v]) => v).map(([k, v]) => (
              <div key={k} className="flex gap-2"><dt className="text-white/40 w-28 flex-shrink-0">{k}</dt><dd className="text-white/80">{v}</dd></div>
            ))}
          </dl>
        </Section>
      )}
    </>
  );
}

function Content() {
  const { ref } = useParams();
  const [params, setParams] = useSearchParams();
  const jobId = params.get('job_id');
  const { me } = useRecruiter();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [shortlists, setShortlists] = useState([]);
  const [alert, setAlert] = useState(null);
  const [notFound, setNotFound] = useState('');
  const [note, setNote] = useState({ kind: 'note', body: '', interview_round: '', outcome: 'pending', application_id: '' });
  const [stageMsg, setStageMsg] = useState({});
  const [invite, setInvite] = useState({ job_id: '', message: '' });
  const [slChoice, setSlChoice] = useState('');

  const load = useCallback(() => recruiterService.candidate(ref, jobId).then(setData)
    .catch((e) => setNotFound(errorText(e, 'Candidate not found.'))), [ref, jobId]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    recruiterService.listJobs().then((r) => setJobs(r.jobs.filter((j) => j.status !== 'draft'))).catch(() => {});
    recruiterService.listShortlists().then((r) => setShortlists(r.shortlists)).catch(() => {});
  }, []);

  const act = async (fn, after) => {
    try {
      const r = await fn();
      setAlert({ type: 'success', message: r.message });
      after?.();
      load();
    } catch (e) {
      setAlert({ type: 'error', message: errorText(e) });
    }
  };

  if (notFound) {
    return (
      <div className="glass p-8 rounded-2xl max-w-lg mx-auto text-center space-y-3">
        <TbShieldLock className="w-10 h-10 text-white/30 mx-auto" />
        <p className="text-sm text-white/60">{notFound}</p>
        <Link to="/recruiter/candidates" className="text-xs text-indigo-300">Back to search</Link>
      </div>
    );
  }
  if (!data) return <p className="text-sm text-white/40">Loading…</p>;
  const p = data.passport;
  const edu = p.education?.current;

  return (
    <div className="space-y-5">
      <button onClick={() => navigate(-1)} className="text-xs text-white/50 hover:text-white flex items-center gap-1"><TbArrowLeft /> Back</button>
      {alert && <AlertBanner type={alert.type} message={alert.message} onClose={() => setAlert(null)} />}

      <div className="glass p-5 flex flex-col md:flex-row gap-4 md:items-center">
        <div className="w-14 h-14 rounded-2xl bg-indigo-500/15 border border-indigo-400/30 flex items-center justify-center font-heading text-xl font-bold text-indigo-200 flex-shrink-0">
          {(p.name || '?')[0].toUpperCase()}
        </div>
        <div className="flex-1 min-w-0 space-y-1">
          <h1 className="font-heading text-xl font-bold text-white">{p.name}</h1>
          {p.profile?.headline && <p className="text-sm text-indigo-200/90">{p.profile.headline}</p>}
          {edu && (edu.program || edu.institution) && <p className="text-xs text-white/55">{[edu.program, edu.institution, edu.year].filter(Boolean).join(' · ')}</p>}
          <p className="text-[11px] text-white/40 flex items-center gap-1"><TbShieldLock className="w-3.5 h-3.5" /> {data.basis_label}. Shared sections: {p.sections.join(', ') || 'none'}.</p>
        </div>
        {p.readiness && (
          <div className="surface p-3 text-center md:w-36" title={p.readiness.note}>
            <div className="font-heading text-2xl font-bold text-white">{p.readiness.score ?? '—'}{p.readiness.score != null && '%'}</div>
            <div className="text-[11px] text-white/50">Readiness · {p.readiness.label}</div>
          </div>
        )}
      </div>

      <Section title="Job compatibility" right={
        <select className="input-field text-[11px] py-1.5 px-2 w-auto" value={jobId || ''}
          onChange={(e) => setParams(e.target.value ? { job_id: e.target.value } : {})}>
          <option value="">Choose a job to compare…</option>
          {jobs.map((j) => <option key={j.id} value={j.id}>{j.title}</option>)}
        </select>
      }>
        {data.report ? <MatchReport report={data.report} /> : <p className="text-xs text-white/40">Select one of your jobs to see an explainable, evidence-by-evidence comparison.</p>}
      </Section>

      {data.applications.length > 0 && (
        <Section title="Applications to your organisation">
          {data.applications.map((a) => (
            <div key={a.application_id} className="surface p-4 space-y-2">
              <div className="flex flex-col sm:flex-row justify-between gap-2">
                <div>
                  <div className="text-sm font-semibold text-white">{a.job_title}</div>
                  <div className="text-[11px] text-white/45">Applied {fmtDateTime(a.applied_at)} · stage: <b className="text-indigo-200">{a.stage_label}</b></div>
                </div>
                <div className="text-[11px] text-white/60 space-y-0.5 sm:text-right">
                  {a.contact_email && <div className="flex items-center gap-1 sm:justify-end"><TbMail className="w-3.5 h-3.5" /> {a.contact_email}</div>}
                  {a.portfolio_url && <SafeLink href={a.portfolio_url} className="text-indigo-300">{a.portfolio_url}</SafeLink>}
                </div>
              </div>
              {a.cover_note && <p className="text-xs text-white/60 whitespace-pre-line border-l-2 border-base-700 pl-3">{a.cover_note}</p>}
              <div className="flex flex-col sm:flex-row gap-2">
                <select className="input-field text-xs py-2 sm:w-48" defaultValue=""
                  onChange={(e) => {
                    const v = e.target.value;
                    e.target.value = '';
                    if (v) act(() => recruiterService.changeStage(a.application_id, v, stageMsg[a.application_id] || ''),
                      () => setStageMsg({ ...stageMsg, [a.application_id]: '' }));
                  }}>
                  <option value="">Move to stage…</option>
                  {me.pipeline_stages.filter((s) => s.key !== a.stage).map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
                </select>
                <input className="input-field text-xs py-2" maxLength={500} placeholder="Optional message the candidate will see with the update"
                  value={stageMsg[a.application_id] || ''} onChange={(e) => setStageMsg({ ...stageMsg, [a.application_id]: e.target.value })} />
              </div>
              {a.events.length > 0 && (
                <div className="text-[11px] text-white/40">History: {a.events.map((e) => `${me.pipeline_stages.find((s) => s.key === e.to_stage)?.label || e.to_stage} (${fmtDate(e.created_at)})`).join(' → ')}</div>
              )}
            </div>
          ))}
        </Section>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Section title={<span className="flex items-center gap-2"><TbListCheck className="w-4 h-4" /> Shortlist</span>}>
          {shortlists.length === 0 ? <p className="text-xs text-white/40">Create a shortlist on the Shortlists page first.</p> : (
            <div className="flex gap-2">
              <select className="input-field text-xs py-2" value={slChoice} onChange={(e) => setSlChoice(e.target.value)}>
                <option value="">Choose a shortlist…</option>
                {shortlists.map((s) => <option key={s.id} value={s.id} disabled={data.shortlist_ids.includes(s.id)}>{s.name}{data.shortlist_ids.includes(s.id) ? ' (added)' : ''}</option>)}
              </select>
              <button disabled={!slChoice} className="btn-ghost text-xs whitespace-nowrap"
                onClick={() => act(() => recruiterService.addToShortlist(slChoice, ref), () => setSlChoice(''))}>Add</button>
            </div>
          )}
          {data.basis === 'discovery' && (
            <div className="pt-3 border-t border-base-700 space-y-2">
              <h3 className="text-xs font-semibold text-white flex items-center gap-1.5"><TbSend className="w-4 h-4" /> Invite to apply</h3>
              {data.invitable_jobs.length === 0 ? <p className="text-xs text-white/40">No published jobs to invite to.</p> : (
                <>
                  <select className="input-field text-xs py-2" value={invite.job_id} onChange={(e) => setInvite({ ...invite, job_id: e.target.value })}>
                    <option value="">Choose a job…</option>
                    {data.invitable_jobs.map((j) => <option key={j.id} value={j.id} disabled={j.invited}>{j.title}{j.invited ? ' (invited)' : ''}</option>)}
                  </select>
                  <textarea className="input-field text-xs py-2" rows={2} maxLength={500} placeholder="Short message (optional)"
                    value={invite.message} onChange={(e) => setInvite({ ...invite, message: e.target.value })} />
                  <button disabled={!invite.job_id} className="btn-primary text-xs py-2"
                    onClick={() => act(() => recruiterService.invite(ref, Number(invite.job_id), invite.message), () => setInvite({ job_id: '', message: '' }))}>
                    Send invitation
                  </button>
                  <p className="text-[11px] text-white/40">The candidate decides whether to apply and what to share.</p>
                </>
              )}
            </div>
          )}
        </Section>

        <Section title={<span className="flex items-center gap-2"><TbNote className="w-4 h-4" /> Internal notes & interviews</span>}>
          <p className="text-[11px] text-white/40">Visible only to your organisation, never to the candidate.</p>
          <form className="space-y-2" onSubmit={(e) => {
            e.preventDefault();
            act(() => recruiterService.addNote(ref, note), () => setNote({ ...note, body: '', interview_round: '' }));
          }}>
            <div className="flex gap-2">
              <select className="input-field text-xs py-2" value={note.kind} onChange={(e) => setNote({ ...note, kind: e.target.value })}>
                <option value="note">Note</option><option value="interview">Interview outcome</option>
              </select>
              {data.applications.length > 0 && (
                <select className="input-field text-xs py-2" value={note.application_id} onChange={(e) => setNote({ ...note, application_id: e.target.value })}>
                  <option value="">General</option>
                  {data.applications.map((a) => <option key={a.application_id} value={a.application_id}>{a.job_title}</option>)}
                </select>
              )}
            </div>
            {note.kind === 'interview' && (
              <div className="flex gap-2">
                <input className="input-field text-xs py-2" placeholder="Round (e.g. Technical 1)" required maxLength={80}
                  value={note.interview_round} onChange={(e) => setNote({ ...note, interview_round: e.target.value })} />
                <select className="input-field text-xs py-2" value={note.outcome} onChange={(e) => setNote({ ...note, outcome: e.target.value })}>
                  {['pending', 'passed', 'failed', 'no_show'].map((o) => <option key={o} value={o}>{o.replace('_', ' ')}</option>)}
                </select>
              </div>
            )}
            <textarea className="input-field text-xs py-2" rows={3} maxLength={4000} required={note.kind === 'note'}
              placeholder="Write a note…" value={note.body} onChange={(e) => setNote({ ...note, body: e.target.value })} />
            <button className="btn-ghost text-xs">Save</button>
          </form>
          <div className="space-y-2">
            {data.notes.map((n) => (
              <div key={n.id} className="surface p-3 text-xs space-y-1">
                <div className="flex justify-between text-[11px] text-white/40">
                  <span>{n.kind === 'interview' ? `Interview · ${n.interview_round} · ${n.outcome?.replace('_', ' ')}` : 'Note'} · {fmtDateTime(n.created_at)}</span>
                  <button onClick={() => window.confirm('Delete this note?') && act(() => recruiterService.deleteNote(n.id))} className="hover:text-rose-300"><TbTrash className="w-3.5 h-3.5" /></button>
                </div>
                {n.body && <p className="text-white/70 whitespace-pre-line">{n.body}</p>}
              </div>
            ))}
          </div>
        </Section>
      </div>

      {p.profile?.summary && <Section title="Professional summary"><p className="text-sm text-white/70 whitespace-pre-line">{p.profile.summary}</p></Section>}
      {p.links && Object.keys(p.links).length > 0 && (
        <Section title="Links">
          <div className="flex flex-wrap gap-3 text-xs">{Object.values(p.links).map((u) => <SafeLink key={u} href={u} className="text-indigo-300">{u}</SafeLink>)}</div>
        </Section>
      )}
      <Passport p={p} />
      <p className="text-[11px] text-white/35">{data.privacy}</p>
    </div>
  );
}

export default function RecruiterCandidateProfile() {
  return <RecruiterLayout><Content /></RecruiterLayout>;
}
