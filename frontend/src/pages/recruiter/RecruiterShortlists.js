import React, { useCallback, useEffect, useState } from 'react';
import { TbPlus, TbTrash, TbX } from 'react-icons/tb';
import RecruiterLayout from '../../components/RecruiterLayout';
import recruiterService, { errorText } from '../../services/recruiterService';
import AlertBanner from '../../components/AlertBanner';
import { CandidateCard } from './RecruiterJobDetail';
import { fmtDate } from '../../components/PassportBits';

function Content() {
  const [lists, setLists] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [open, setOpen] = useState(null);
  const [form, setForm] = useState({ name: '', description: '', job_id: '' });
  const [alert, setAlert] = useState(null);

  const load = useCallback(() => recruiterService.listShortlists().then((r) => setLists(r.shortlists))
    .catch((e) => setAlert({ type: 'error', message: errorText(e) })), []);
  const openList = useCallback((id) => recruiterService.getShortlist(id).then((r) => setOpen(r.shortlist))
    .catch((e) => setAlert({ type: 'error', message: errorText(e) })), []);
  useEffect(() => { load(); recruiterService.listJobs().then((r) => setJobs(r.jobs)).catch(() => {}); }, [load]);

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

  return (
    <div className="space-y-5">
      <h1 className="font-heading text-2xl font-bold text-white">Shortlists</h1>
      {alert && <AlertBanner type={alert.type} message={alert.message} onClose={() => setAlert(null)} />}
      <form className="glass p-4 grid grid-cols-1 md:grid-cols-4 gap-2"
        onSubmit={(e) => { e.preventDefault(); act(() => recruiterService.createShortlist(form), () => setForm({ name: '', description: '', job_id: '' })); }}>
        <input className="input-field text-xs py-2" placeholder="Shortlist name" required maxLength={120} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <input className="input-field text-xs py-2" placeholder="Description (optional)" maxLength={300} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        <select className="input-field text-xs py-2" value={form.job_id} onChange={(e) => setForm({ ...form, job_id: e.target.value })}>
          <option value="">Not tied to a job</option>
          {jobs.map((j) => <option key={j.id} value={j.id}>For: {j.title}</option>)}
        </select>
        <button className="btn-primary text-xs py-2 flex items-center justify-center gap-1"><TbPlus className="w-4 h-4" /> Create</button>
      </form>

      {lists === null ? <p className="text-sm text-white/40">Loading…</p> : lists.length === 0 ? (
        <div className="glass p-8 text-center text-sm text-white/50">No shortlists yet. Add candidates from their profile page.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {lists.map((s) => (
            <div key={s.id} className="glass p-4 flex justify-between items-start gap-2">
              <button className="text-left" onClick={() => openList(s.id)}>
                <div className="font-semibold text-white hover:text-indigo-300">{s.name}</div>
                <div className="text-[11px] text-white/45">{s.count} candidate{s.count === 1 ? '' : 's'} · created {fmtDate(s.created_at)}</div>
                {s.description && <div className="text-xs text-white/55 mt-1">{s.description}</div>}
              </button>
              <button onClick={() => window.confirm(`Delete "${s.name}"?`) && act(() => recruiterService.deleteShortlist(s.id), () => setOpen(null))}
                className="p-1.5 text-white/40 hover:text-rose-300"><TbTrash className="w-4 h-4" /></button>
            </div>
          ))}
        </div>
      )}

      {open && (
        <div className="glass p-5 space-y-3">
          <div className="flex justify-between items-center">
            <h2 className="font-heading text-lg font-bold text-white">{open.name}</h2>
            <button onClick={() => setOpen(null)} className="text-white/40 hover:text-white"><TbX className="w-5 h-5" /></button>
          </div>
          {open.entries.length === 0 && <p className="text-xs text-white/40">Empty.</p>}
          {open.entries.map((e) => e.available ? (
            <CandidateCard key={e.entry_id} c={e} jobId={open.job_id} extra={
              <button className="text-[11px] text-white/40 hover:text-rose-300"
                onClick={() => act(() => recruiterService.removeFromShortlist(open.id, e.entry_id), () => openList(open.id))}>Remove</button>
            } />
          ) : (
            <div key={e.entry_id} className="surface p-3 flex justify-between text-xs text-white/50">
              <span>{e.message}</span>
              <button className="hover:text-rose-300" onClick={() => act(() => recruiterService.removeFromShortlist(open.id, e.entry_id), () => openList(open.id))}>Remove</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function RecruiterShortlists() {
  return <RecruiterLayout><Content /></RecruiterLayout>;
}
