import React, { useCallback, useEffect, useState } from 'react';
import { TbCheck, TbX, TbRefresh, TbBan } from 'react-icons/tb';
import recruiterService, { errorText } from '../services/recruiterService';
import AlertBanner from './AlertBanner';
import { SafeLink, fmtDateTime } from './PassportBits';

const FILTERS = ['pending', 'verified', 'rejected', 'unverified'];

/** Admin queue for recruiter organisations requesting verification. */
export default function AdminOrganisationReview() {
  const [status, setStatus] = useState('pending');
  const [items, setItems] = useState([]);
  const [notes, setNotes] = useState({});
  const [alert, setAlert] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setItems((await recruiterService.adminOrganisations(status)).organisations);
    } catch (e) {
      setAlert({ type: 'error', message: errorText(e, 'Could not load organisations.') });
    } finally {
      setLoading(false);
    }
  }, [status]);
  useEffect(() => { load(); }, [load]);

  const decide = async (id, decision) => {
    try {
      const r = await recruiterService.adminReviewOrganisation(id, decision, notes[id] || '');
      setAlert({ type: 'success', message: r.message + (r.jobs_closed ? ` (${r.jobs_closed} job(s) closed)` : '') });
      load();
    } catch (e) {
      setAlert({ type: 'error', message: errorText(e, 'Review failed.') });
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="font-heading text-xl font-bold text-white">Employer verification</h2>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            Verify an organisation only after checking that it exists and that the recruiter belongs to it (company
            website, registration number on the MCA/GST portal, LinkedIn page). Verified organisations can publish jobs
            and search students who opted in. The domain hint below is automatic and is not proof.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {FILTERS.map((f) => (
            <button key={f} onClick={() => setStatus(f)}
              className={`text-xs px-3 py-1.5 rounded-lg border capitalize ${status === f ? 'border-teal-400 text-teal-300' : 'border-slate-700 text-slate-400'}`}>{f}</button>
          ))}
          <button onClick={load} className="p-2 rounded-lg border border-slate-700 text-slate-400 hover:text-white" title="Refresh"><TbRefresh className="w-4 h-4" /></button>
        </div>
      </div>
      {alert && <AlertBanner type={alert.type} message={alert.message} onClose={() => setAlert(null)} />}
      {loading ? <p className="text-sm text-slate-500">Loading…</p> : items.length === 0 ? <p className="text-sm text-slate-500">No {status} organisations.</p> : (
        <div className="space-y-3">
          {items.map((o) => {
            const det = o.verification_details || {};
            const sig = det.signals || {};
            return (
              <div key={o.id} className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-2 text-xs">
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-2">
                  <div>
                    <div className="text-sm font-semibold text-white">{o.name} <span className="text-slate-400 font-normal">{o.industry && `· ${o.industry}`} {o.location && `· ${o.location}`}</span></div>
                    <div className="text-slate-400">{o.website && <SafeLink href={o.website} className="text-teal-300">{o.website}</SafeLink>} {o.verification_requested_at && `· requested ${fmtDateTime(o.verification_requested_at)}`} · {o.job_count} job(s)</div>
                  </div>
                  <span className="text-[10px] capitalize px-2 py-0.5 rounded-full border border-slate-700 text-slate-300">{o.verification_status}</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-slate-300">
                  <div>Recruiters: {o.recruiters.map((r) => `${r.name} <${r.email}>${r.job_title ? ` (${r.job_title})` : ''}`).join('; ') || '—'}</div>
                  <div>Registration no.: {det.registration_id || '—'}</div>
                  <div>LinkedIn: {det.linkedin_url ? <SafeLink href={det.linkedin_url} className="text-teal-300">{det.linkedin_url}</SafeLink> : '—'}</div>
                  <div>Proof link: {det.proof_url ? <SafeLink href={det.proof_url} className="text-teal-300">{det.proof_url}</SafeLink> : '—'}</div>
                  {det.notes && <div className="md:col-span-2">Notes: {det.notes}</div>}
                  {sig.recruiter_email_domain && (
                    <div className={`md:col-span-2 ${sig.domains_match ? 'text-emerald-300' : 'text-amber-300'}`}>
                      Hint: recruiter email domain <b>{sig.recruiter_email_domain}</b> {sig.domains_match ? 'matches' : 'does not match'} website domain <b>{sig.website_domain || '—'}</b>
                      {sig.free_email_provider && ' · free email provider'}
                    </div>
                  )}
                </div>
                {o.verification_note && <p className="text-slate-400">Note: {o.verification_note}</p>}
                {(o.verification_status === 'pending' || o.verification_status === 'verified') && (
                  <div className="flex flex-col sm:flex-row gap-2 pt-1">
                    <input className="input-field text-xs py-2" maxLength={500}
                      placeholder={o.verification_status === 'pending' ? 'Note to the recruiter (required when rejecting)' : 'Reason for revoking (required)'}
                      value={notes[o.id] || ''} onChange={(e) => setNotes({ ...notes, [o.id]: e.target.value })} />
                    {o.verification_status === 'pending' ? (
                      <>
                        <button onClick={() => decide(o.id, 'verified')} className="px-3 py-2 rounded-lg bg-emerald-500/15 border border-emerald-500/40 text-emerald-300 flex items-center gap-1 whitespace-nowrap"><TbCheck className="w-4 h-4" /> Verify</button>
                        <button onClick={() => decide(o.id, 'rejected')} className="px-3 py-2 rounded-lg bg-rose-500/15 border border-rose-500/40 text-rose-300 flex items-center gap-1 whitespace-nowrap"><TbX className="w-4 h-4" /> Reject</button>
                      </>
                    ) : (
                      <button onClick={() => window.confirm('Revoke verification? Their published jobs will be closed.') && decide(o.id, 'revoked')}
                        className="px-3 py-2 rounded-lg bg-rose-500/15 border border-rose-500/40 text-rose-300 flex items-center gap-1 whitespace-nowrap"><TbBan className="w-4 h-4" /> Revoke</button>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
