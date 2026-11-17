import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { TbPlus, TbPencil, TbSend, TbLock, TbTrash, TbUsers, TbX } from 'react-icons/tb';
import RecruiterLayout, { useRecruiter } from '../../components/RecruiterLayout';
import recruiterService, { errorText } from '../../services/recruiterService';
import AlertBanner from '../../components/AlertBanner';
import { displaySkill, fmtDate } from '../../components/PassportBits';

const STATUS_CLS = {
  draft: 'bg-white/5 text-white/60 border-white/15',
  active: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40',
  closed: 'bg-slate-500/15 text-slate-300 border-slate-500/40',
  expired: 'bg-rose-500/15 text-rose-300 border-rose-500/40'
};
const STATUS_LABEL = { draft: 'Draft', active: 'Published', closed: 'Closed', expired: 'Expired' };

const EMPTY = {
  title: '', description: '', location: '', work_arrangement: 'Onsite', job_type: 'Full-time',
  required_skills: '', preferred_skills: '', experience_min_years: '', experience_max_years: '',
  education: '', salary_min: '', salary_max: '', salary_currency: 'INR', salary_period: 'year', deadline: ''
};

const toForm = (j) => ({
  title: j.title, description: j.description || '', location: j.location || '',
  work_arrangement: j.work_arrangement || 'Onsite', job_type: j.job_type || 'Full-time',
  required_skills: (j.required_skills || []).join(', '), preferred_skills: (j.preferred_skills || []).join(', '),
  experience_min_years: j.experience_min_years ?? '', experience_max_years: j.experience_max_years ?? '',
  education: j.eligibility || '', salary_min: j.salary?.min ?? '', salary_max: j.salary?.max ?? '',
  salary_currency: j.salary?.currency || 'INR', salary_period: j.salary?.period || 'year',
  deadline: j.deadline ? j.deadline.slice(0, 10) : ''
});

const toPayload = (f) => ({
  ...f,
  required_skills: f.required_skills.split(',').map((s) => s.trim()).filter(Boolean),
  preferred_skills: f.preferred_skills.split(',').map((s) => s.trim()).filter(Boolean)
});

export function JobStatus({ status }) {
  return <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${STATUS_CLS[status] || STATUS_CLS.draft}`}>{STATUS_LABEL[status] || status}</span>;
}

function JobEditor({ job, onClose, onSaved }) {
  const [f, setF] = useState(job ? toForm(job) : EMPTY);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      const res = job ? await recruiterService.updateJob(job.id, toPayload(f)) : await recruiterService.createJob(toPayload(f));
      onSaved(res.message);
    } catch (err) {
      setError(errorText(err, 'Could not save the job.'));
    } finally {
      setSaving(false);
    }
  };

  const field = 'input-field text-xs py-2.5';
  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-start justify-center overflow-y-auto p-4">
      <form onSubmit={save} className="glass w-full max-w-3xl p-6 space-y-4 my-8">
        <div className="flex items-center justify-between">
          <h2 className="font-heading text-lg font-bold text-white">{job ? 'Edit job' : 'New job posting'}</h2>
          <button type="button" onClick={onClose} className="p-1.5 text-white/40 hover:text-white"><TbX className="w-5 h-5" /></button>
        </div>
        {error && <AlertBanner type="error" message={error} />}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <label className="sm:col-span-2 text-[11px] text-white/50 space-y-1"><span>Job title *</span>
            <input className={field} value={f.title} onChange={set('title')} required maxLength={200} /></label>
          <label className="sm:col-span-2 text-[11px] text-white/50 space-y-1"><span>Description * (responsibilities, team, what the role involves)</span>
            <textarea className={field} rows={6} value={f.description} onChange={set('description')} required minLength={30} maxLength={10000} /></label>
          <label className="text-[11px] text-white/50 space-y-1"><span>Location *</span>
            <input className={field} value={f.location} onChange={set('location')} required maxLength={200} placeholder="Bengaluru, Karnataka" /></label>
          <div className="grid grid-cols-2 gap-2">
            <label className="text-[11px] text-white/50 space-y-1"><span>Work mode</span>
              <select className={field} value={f.work_arrangement} onChange={set('work_arrangement')}>
                {['Onsite', 'Hybrid', 'Remote'].map((m) => <option key={m}>{m}</option>)}</select></label>
            <label className="text-[11px] text-white/50 space-y-1"><span>Employment type</span>
              <select className={field} value={f.job_type} onChange={set('job_type')}>
                {['Full-time', 'Internship', 'Contract', 'Part-time'].map((m) => <option key={m}>{m}</option>)}</select></label>
          </div>
          <label className="text-[11px] text-white/50 space-y-1"><span>Required skills * (comma-separated)</span>
            <input className={field} value={f.required_skills} onChange={set('required_skills')} required placeholder="Python, SQL, Docker" /></label>
          <label className="text-[11px] text-white/50 space-y-1"><span>Preferred skills (comma-separated)</span>
            <input className={field} value={f.preferred_skills} onChange={set('preferred_skills')} placeholder="AWS, Airflow" /></label>
          <div className="grid grid-cols-2 gap-2">
            <label className="text-[11px] text-white/50 space-y-1"><span>Experience min (yrs)</span>
              <input type="number" min="0" max="40" step="0.5" className={field} value={f.experience_min_years} onChange={set('experience_min_years')} /></label>
            <label className="text-[11px] text-white/50 space-y-1"><span>Experience max (yrs)</span>
              <input type="number" min="0" max="40" step="0.5" className={field} value={f.experience_max_years} onChange={set('experience_max_years')} /></label>
          </div>
          <label className="text-[11px] text-white/50 space-y-1"><span>Education requirement</span>
            <input className={field} value={f.education} onChange={set('education')} maxLength={300} placeholder="B.Tech/BE in CS, IT or related" /></label>
          <div className="grid grid-cols-2 gap-2">
            <label className="text-[11px] text-white/50 space-y-1"><span>Salary min</span>
              <input type="number" min="0" className={field} value={f.salary_min} onChange={set('salary_min')} /></label>
            <label className="text-[11px] text-white/50 space-y-1"><span>Salary max</span>
              <input type="number" min="0" className={field} value={f.salary_max} onChange={set('salary_max')} /></label>
          </div>
          <div className="grid grid-cols-3 gap-2">
            <label className="text-[11px] text-white/50 space-y-1"><span>Currency</span>
              <select className={field} value={f.salary_currency} onChange={set('salary_currency')}>
                {['INR', 'USD', 'EUR', 'GBP'].map((m) => <option key={m}>{m}</option>)}</select></label>
            <label className="text-[11px] text-white/50 space-y-1"><span>Per</span>
              <select className={field} value={f.salary_period} onChange={set('salary_period')}>
                {['year', 'month', 'hour'].map((m) => <option key={m}>{m}</option>)}</select></label>
            <label className="text-[11px] text-white/50 space-y-1"><span>Apply by</span>
              <input type="date" className={field} value={f.deadline} onChange={set('deadline')} /></label>
          </div>
        </div>
        <div className="flex justify-end gap-2 pt-2 border-t border-base-700">
          <button type="button" onClick={onClose} className="btn-ghost text-xs">Cancel</button>
          <button className="btn-primary w-auto text-xs py-2 px-5" disabled={saving}>{saving ? 'Saving…' : job ? 'Save changes' : 'Save as draft'}</button>
        </div>
      </form>
    </div>
  );
}

function Content() {
  const { me } = useRecruiter();
  const [jobs, setJobs] = useState(null);
  const [editing, setEditing] = useState(null); // null | 'new' | job
  const [alert, setAlert] = useState(null);

  const load = useCallback(() => recruiterService.listJobs().then((r) => setJobs(r.jobs))
    .catch((e) => setAlert({ type: 'error', message: errorText(e) })), []);
  useEffect(() => { load(); }, [load]);

  const act = async (fn) => {
    try {
      const r = await fn();
      setAlert({ type: 'success', message: r.message });
      load();
    } catch (e) {
      setAlert({ type: 'error', message: errorText(e) });
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="font-heading text-2xl font-bold text-white">Job postings</h1>
          <p className="text-xs text-white/50 mt-1">Published jobs appear on students' Jobs page labelled as employer-posted, with skill-match scores and in-app applications.</p>
        </div>
        <button onClick={() => setEditing('new')} className="btn-primary w-auto text-xs py-2 px-4 flex items-center gap-1.5 whitespace-nowrap">
          <TbPlus className="w-4 h-4" /> New job
        </button>
      </div>
      {!me.can_publish_jobs && (
        <AlertBanner type="warning" message="You can prepare drafts now. Publishing is enabled once an administrator verifies your organisation." />
      )}
      {alert && <AlertBanner type={alert.type} message={alert.message} onClose={() => setAlert(null)} />}

      {jobs === null ? <p className="text-sm text-white/40">Loading…</p> : jobs.length === 0 ? (
        <div className="glass p-8 text-center text-sm text-white/50">No job postings yet.</div>
      ) : (
        <div className="space-y-3">
          {jobs.map((j) => (
            <div key={j.id} className="glass p-4 flex flex-col lg:flex-row lg:items-center gap-3 justify-between">
              <div className="min-w-0 space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <Link to={`/recruiter/jobs/${j.id}`} className="font-semibold text-white hover:text-indigo-300">{j.title}</Link>
                  <JobStatus status={j.status} />
                </div>
                <div className="text-[11px] text-white/50">
                  {j.location} · {j.work_arrangement} · {j.job_type}
                  {j.posting_date && ` · published ${fmtDate(j.posting_date)}`}
                  {j.deadline && ` · apply by ${fmtDate(j.deadline)}`}
                  {j.expiry_reason && ` · ${j.expiry_reason}`}
                </div>
                <div className="flex flex-wrap gap-1">
                  {j.required_skills.map((s) => <span key={s} className="text-[10px] px-2 py-0.5 rounded-md bg-base-950 text-white/70 border border-base-800">{displaySkill(s)}</span>)}
                  {j.preferred_skills.map((s) => <span key={s} className="text-[10px] px-2 py-0.5 rounded-md text-white/40 border border-dashed border-base-700">{displaySkill(s)}</span>)}
                </div>
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                <Link to={`/recruiter/jobs/${j.id}`} className="btn-ghost text-xs flex items-center gap-1"><TbUsers className="w-4 h-4" /> {j.applicant_count} applicant{j.applicant_count === 1 ? '' : 's'}</Link>
                {j.status !== 'expired' && <button onClick={() => setEditing(j)} className="btn-ghost text-xs flex items-center gap-1"><TbPencil className="w-4 h-4" /> Edit</button>}
                {(j.status === 'draft' || j.status === 'closed') && (
                  <button onClick={() => act(() => recruiterService.publishJob(j.id))} disabled={!me.can_publish_jobs}
                    title={me.can_publish_jobs ? '' : 'Needs a verified organisation'}
                    className="px-3 py-2 rounded-xl text-xs bg-indigo-500/20 border border-indigo-400/40 text-indigo-200 flex items-center gap-1 disabled:opacity-40">
                    <TbSend className="w-4 h-4" /> {j.status === 'closed' ? 'Reopen' : 'Publish'}
                  </button>
                )}
                {j.status === 'active' && (
                  <button onClick={() => window.confirm('Close this job? Students can no longer apply; existing applications are kept.') && act(() => recruiterService.closeJob(j.id))}
                    className="btn-ghost text-xs flex items-center gap-1"><TbLock className="w-4 h-4" /> Close</button>
                )}
                {j.status === 'draft' && !j.posting_date && (
                  <button onClick={() => window.confirm('Delete this draft?') && act(() => recruiterService.deleteJob(j.id))}
                    className="p-2 rounded-xl text-white/40 hover:text-rose-300" title="Delete draft"><TbTrash className="w-4 h-4" /></button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
      {editing && (
        <JobEditor job={editing === 'new' ? null : editing} onClose={() => setEditing(null)}
          onSaved={(msg) => { setEditing(null); setAlert({ type: 'success', message: msg }); load(); }} />
      )}
    </div>
  );
}

export default function RecruiterJobs() {
  return <RecruiterLayout><Content /></RecruiterLayout>;
}
