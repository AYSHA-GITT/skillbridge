import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import RecruiterLayout, { useRecruiter } from '../../components/RecruiterLayout';
import recruiterService, { errorText } from '../../services/recruiterService';
import AlertBanner from '../../components/AlertBanner';
import { fmtDate } from '../../components/PassportBits';

const STAGE_TONE = {
  new: 'border-white/15', under_review: 'border-sky-500/40', shortlisted: 'border-indigo-400/50',
  assessment: 'border-violet-500/40', interview: 'border-amber-500/40', selected: 'border-emerald-500/50',
  rejected: 'border-rose-500/40', on_hold: 'border-slate-500/40'
};

function Content() {
  const { me } = useRecruiter();
  const [jobs, setJobs] = useState([]);
  const [jobId, setJobId] = useState('');
  const [data, setData] = useState(null);
  const [alert, setAlert] = useState(null);

  const load = useCallback(() => recruiterService.pipeline(jobId || null).then(setData)
    .catch((e) => setAlert({ type: 'error', message: errorText(e) })), [jobId]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { recruiterService.listJobs().then((r) => setJobs(r.jobs)).catch(() => {}); }, []);

  const move = async (appId, stage) => {
    try {
      const r = await recruiterService.changeStage(appId, stage);
      setAlert({ type: 'success', message: r.message });
      load();
    } catch (e) {
      setAlert({ type: 'error', message: errorText(e) });
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
        <div>
          <h1 className="font-heading text-2xl font-bold text-white">Hiring pipeline</h1>
          <p className="text-xs text-white/50 mt-1">Applicants move through your stages; each change is shown to the candidate with your optional message.</p>
        </div>
        <select className="input-field text-xs py-2 sm:w-64" value={jobId} onChange={(e) => setJobId(e.target.value)}>
          <option value="">All jobs</option>
          {jobs.map((j) => <option key={j.id} value={j.id}>{j.title}</option>)}
        </select>
      </div>
      {alert && <AlertBanner type={alert.type} message={alert.message} onClose={() => setAlert(null)} />}
      {!data ? <p className="text-sm text-white/40">Loading…</p> : (
        <div className="flex gap-3 overflow-x-auto pb-3">
          {data.stages.map((col) => (
            <div key={col.key} className={`min-w-[220px] w-[220px] flex-shrink-0 rounded-2xl bg-base-900/70 border-t-2 ${STAGE_TONE[col.key]} border-x border-b border-base-700 p-3 space-y-2`}>
              <div className="flex justify-between text-xs font-semibold text-white">
                <span>{col.label}</span><span className="text-white/40">{col.applications.length}</span>
              </div>
              {col.applications.length === 0 && <p className="text-[11px] text-white/30 italic">Empty</p>}
              {col.applications.map((a) => (
                <div key={a.application_id} className="surface p-2.5 space-y-1.5">
                  <Link to={`/recruiter/candidates/${a.candidate_ref}?job_id=${a.job_id}`} className="text-xs font-semibold text-white hover:text-indigo-300">{a.name}</Link>
                  <div className="text-[10px] text-white/45">{a.job_title}</div>
                  <div className="text-[10px] text-white/35">Applied {fmtDate(a.applied_at)}{a.match_score != null && ` · fit at apply ${a.match_score}%`}</div>
                  <select className="input-field text-[10px] py-1 px-2" value=""
                    onChange={(e) => e.target.value && move(a.application_id, e.target.value)}>
                    <option value="">Move to…</option>
                    {me.pipeline_stages.filter((s) => s.key !== col.key).map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
                  </select>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function RecruiterPipeline() {
  return <RecruiterLayout><Content /></RecruiterLayout>;
}
