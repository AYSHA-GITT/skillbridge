import React, { useEffect, useState } from 'react';
import { TbSearch, TbInfoCircle } from 'react-icons/tb';
import RecruiterLayout, { useRecruiter, VerificationGate } from '../../components/RecruiterLayout';
import recruiterService, { errorText } from '../../services/recruiterService';
import AlertBanner from '../../components/AlertBanner';
import { CandidateCard } from './RecruiterJobDetail';

const EMPTY = {
  skills: '', verified_only: false, match_all: false, min_proficiency: '', min_assessment: '',
  education: '', location: '', role: '', has_projects: false, has_experience: false, min_readiness: '', job_id: ''
};

function Content() {
  const { me } = useRecruiter();
  const [f, setF] = useState(EMPTY);
  const [jobs, setJobs] = useState([]);
  const [res, setRes] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    recruiterService.listJobs().then((r) => setJobs(r.jobs.filter((j) => j.status === 'active'))).catch(() => {});
  }, []);

  const search = async (e) => {
    e?.preventDefault();
    setLoading(true);
    setError('');
    const params = {};
    Object.entries(f).forEach(([k, v]) => {
      if (v === true) params[k] = 1;
      else if (v !== false && v !== '') params[k] = v;
    });
    try {
      setRes(await recruiterService.searchCandidates(params));
    } catch (err) {
      setError(errorText(err, 'Search failed.'));
    } finally {
      setLoading(false);
    }
  };

  const set = (k) => (e) => setF({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value });
  const field = 'input-field text-xs py-2.5';

  return (
    <VerificationGate me={me} feature="Candidate search">
      <div className="space-y-5">
        <div>
          <h1 className="font-heading text-2xl font-bold text-white">Find candidates</h1>
          <p className="text-xs text-white/50 mt-1 flex items-start gap-1.5">
            <TbInfoCircle className="w-4 h-4 flex-shrink-0" />
            Only students who chose to be visible to verified employers appear, with the sections they chose to share.
            Ranking uses demonstrated skills only — never name, college, location, gender or age.
          </p>
        </div>
        <form onSubmit={search} className="glass p-5 space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <input className={`${field} md:col-span-2`} placeholder="Skills, comma-separated (e.g. Python, SQL, Power BI)" value={f.skills} onChange={set('skills')} />
            <select className={field} value={f.job_id} onChange={set('job_id')}>
              <option value="">…or rank against one of your jobs</option>
              {jobs.map((j) => <option key={j.id} value={j.id}>{j.title}</option>)}
            </select>
            <input className={field} placeholder="Preferred role (e.g. data analyst)" value={f.role} onChange={set('role')} />
            <input className={field} placeholder="Preferred location (e.g. Bengaluru)" value={f.location} onChange={set('location')} />
            <input className={field} placeholder="Education (e.g. B.Tech, MCA)" value={f.education} onChange={set('education')} />
            <select className={field} value={f.min_proficiency} onChange={set('min_proficiency')}>
              <option value="">Any proficiency</option>
              <option>Intermediate</option><option>Advanced</option>
            </select>
            <input type="number" min="0" max="100" className={field} placeholder="Min assessment score %" value={f.min_assessment} onChange={set('min_assessment')} />
            <input type="number" min="0" max="100" className={field} placeholder="Min readiness % (if shared)" value={f.min_readiness} onChange={set('min_readiness')} />
          </div>
          <div className="flex flex-wrap gap-4 text-xs text-white/70">
            {[['verified_only', 'Verified skills only'], ['match_all', 'Must have all listed skills'],
              ['has_projects', 'Has projects'], ['has_experience', 'Has experience']].map(([k, label]) => (
              <label key={k} className="flex items-center gap-1.5"><input type="checkbox" checked={f[k]} onChange={set(k)} /> {label}</label>
            ))}
          </div>
          <div className="flex gap-2">
            <button className="btn-primary w-auto text-xs py-2 px-5 flex items-center gap-1.5" disabled={loading}>
              <TbSearch className="w-4 h-4" /> {loading ? 'Searching…' : 'Search'}
            </button>
            <button type="button" className="btn-ghost text-xs" onClick={() => { setF(EMPTY); setRes(null); }}>Reset</button>
          </div>
        </form>
        {error && <AlertBanner type="error" message={error} />}
        {res && (
          <div className="space-y-3">
            <p className="text-[11px] text-white/40">{res.total} candidate{res.total === 1 ? '' : 's'} · ranked by {res.ranked_by.toLowerCase()}</p>
            {res.candidates.length === 0 && <div className="glass p-8 text-center text-sm text-white/50">No candidates match these filters.</div>}
            {res.candidates.map((c) => <CandidateCard key={c.candidate_ref} c={c} jobId={f.job_id || null} />)}
          </div>
        )}
      </div>
    </VerificationGate>
  );
}

export default function RecruiterCandidates() {
  return <RecruiterLayout><Content /></RecruiterLayout>;
}
